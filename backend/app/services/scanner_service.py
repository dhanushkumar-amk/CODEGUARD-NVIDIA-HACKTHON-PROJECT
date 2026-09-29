"""
Scanner Service: Code extraction and batch preparation module.
Reads candidate frontend files safely, isolates rendered markup (JSX/HTML/Vue templates),
and chunks large files to respect Nemotron token limits.
"""
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def read_file_safe(file_path: str) -> Optional[str]:
    """
    Safely reads file contents from disk with resilient encoding fallback.
    Skips unreadable or binary files gracefully without crashing the pipeline.

    Args:
        file_path: Path to target file on disk.

    Returns:
        String content if successfully read, or None.
    """
    path = Path(file_path)
    if not path.is_file():
        logger.warning(f"File not found on disk: {file_path}")
        return None

    # Check for binary content (null bytes in first 1024 bytes)
    try:
        with open(path, "rb") as bf:
            header = bf.read(1024)
            if b"\x00" in header:
                logger.warning(f"Skipping binary file: {file_path}")
                return None
    except Exception as exc:
        logger.warning(f"Could not inspect file header for {file_path}: {exc}")
        return None

    # Attempt decodings with common text encodings
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            logger.warning(f"Error reading {file_path} with encoding {encoding}: {exc}")
            break

    logger.warning(f"Unable to decode text file with supported encodings: {file_path}")
    return None


def extract_relevant_markup(
    file_content: str,
    file_type: str,
    include_metadata: bool = False,
) -> Any:
    """
    Extracts rendered markup from source code to minimize token overhead for LLM analysis.

    - .vue: Extracts the <template>...</template> block.
    - .html: Strips <script> and <style> tags.
    - .jsx/.tsx/.js/.ts: Extracts JSX return statements and component templates.

    Args:
        file_content: Raw text content of the file.
        file_type: File extension (e.g. '.tsx', '.vue', '.html').
        include_metadata: If True, returns a list of dicts with {"content": str, "start_line": int}.
                          If False, returns isolated markup string.

    Returns:
        Isolated markup block or list of block dicts with start_line metadata.
    """
    if not file_content or not file_content.strip():
        return [] if include_metadata else ""

    ext = file_type.lower()
    if not ext.startswith("."):
        ext = "." + ext

    # 1. Vue Single File Components: extract <template>
    if ext == ".vue":
        match = re.search(r"<template[^>]*>([\s\S]*?)</template>", file_content, re.IGNORECASE)
        if match:
            start_pos = match.start()
            start_line = file_content[:start_pos].count("\n") + 1
            content_str = match.group(0).strip()
            if include_metadata:
                return [{"content": content_str, "start_line": start_line}]
            return content_str
        stripped = file_content.strip()
        if include_metadata:
            return [{"content": stripped, "start_line": 1}]
        return stripped

    # 2. Plain HTML: strip script and style tags to save tokens
    elif ext == ".html":
        cleaned = re.sub(
            r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
            "",
            file_content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        cleaned = re.sub(
            r"<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
        content_str = cleaned.strip()
        if include_metadata:
            return [{"content": content_str, "start_line": 1}]
        return content_str

    # 3. React / JSX / TSX: extract JSX return blocks
    elif ext in (".jsx", ".tsx", ".js", ".ts"):
        extracted_returns: List[Dict[str, Any]] = []

        # Pattern A: return ( <JSX> );
        for match in re.finditer(r"return\s*\(\s*(<[\s\S]*?>[\s\S]*?)\s*\);?", file_content):
            start_pos = match.start(1)
            start_line = file_content[:start_pos].count("\n") + 1
            extracted_returns.append({
                "content": match.group(1).strip(),
                "start_line": start_line,
            })

        # Pattern B: return <Tag ... >; (single-line or direct return)
        if not extracted_returns:
            for match in re.finditer(r"return\s+(<[A-Za-z][\s\S]*?>[\s\S]*?);", file_content):
                start_pos = match.start(1)
                start_line = file_content[:start_pos].count("\n") + 1
                extracted_returns.append({
                    "content": match.group(1).strip(),
                    "start_line": start_line,
                })

        # Pattern C: arrow function implicit return () => ( <JSX> )
        if not extracted_returns:
            for match in re.finditer(r"=>\s*\(\s*(<[\s\S]*?>[\s\S]*?)\s*\)", file_content):
                start_pos = match.start(1)
                start_line = file_content[:start_pos].count("\n") + 1
                extracted_returns.append({
                    "content": match.group(1).strip(),
                    "start_line": start_line,
                })

        if extracted_returns:
            if include_metadata:
                return extracted_returns
            return "\n\n".join(item["content"] for item in extracted_returns)

        # Fallback: Strip imports, requires, and export boilerplate to keep tokens focused
        lines = []
        first_line_num = 1
        found_first = False
        for idx, line in enumerate(file_content.splitlines(), 1):
            stripped = line.strip()
            if (
                stripped.startswith("import ")
                or stripped.startswith("import{")
                or stripped.startswith("require(")
                or stripped.startswith("//")
            ):
                continue
            if not found_first and stripped:
                first_line_num = idx
                found_first = True
            lines.append(line)

        content_fallback = "\n".join(lines).strip()
        if include_metadata:
            return [{"content": content_fallback, "start_line": first_line_num}]
        return content_fallback

    stripped_other = file_content.strip()
    if include_metadata:
        return [{"content": stripped_other, "start_line": 1}]
    return stripped_other


def chunk_large_file(content: str, max_tokens: int = 2000) -> List[str]:
    """
    Splits large source code blocks into manageable chunks based on character/token estimates.
    Attempts to split along component, function, or paragraph boundaries instead of mid-line.

    Args:
        content: The text/markup to partition.
        max_tokens: Maximum target tokens per chunk (estimated at ~4 characters per token).

    Returns:
        List of content chunk strings.
    """
    if not content:
        return []

    max_chars = max(100, max_tokens * 4)

    # If within limit, return as single chunk
    if len(content) <= max_chars:
        return [content]

    # Split candidates: component/function definitions or double newlines
    split_pattern = r"(?=\n(?:export\s+(?:default\s+)?(?:function|const|class)|function\s+|const\s+[A-Z]))|\n\n"
    sections = re.split(split_pattern, content)

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_length = 0

    for section in sections:
        if not section:
            continue
        sec_len = len(section)

        # If an individual section is itself larger than max_chars, split it by line
        if sec_len > max_chars:
            if current_chunk:
                chunks.append("".join(current_chunk).strip())
                current_chunk = []
                current_length = 0

            lines = section.splitlines(keepends=True)
            temp_lines: List[str] = []
            temp_len = 0
            for line in lines:
                if temp_len + len(line) > max_chars and temp_lines:
                    chunks.append("".join(temp_lines).strip())
                    temp_lines = []
                    temp_len = 0
                temp_lines.append(line)
                temp_len += len(line)
            if temp_lines:
                chunks.append("".join(temp_lines).strip())
            continue

        if current_length + sec_len > max_chars and current_chunk:
            chunks.append("".join(current_chunk).strip())
            current_chunk = [section]
            current_length = sec_len
        else:
            current_chunk.append(section)
            current_length += sec_len

    if current_chunk:
        chunks.append("".join(current_chunk).strip())

    return [c for c in chunks if c.strip()]


def prepare_scan_batch(repo_path: str, file_list: List[str]) -> List[Dict[str, Any]]:
    """
    Reads, extracts markup, and batches all discovered repository frontend files.
    Each chunk carries 'start_line' representing the line number in the original source file.

    Args:
        repo_path: Root filesystem path of cloned repository.
        file_list: Relative file paths within repository.

    Returns:
        List of chunk payloads formatted for LLM violation analysis:
        [
            {
                "file": "src/components/Header.tsx",
                "chunk_index": 0,
                "content": "<header>...</header>",
                "start_line": 34,
                "estimated_tokens": 142
            },
            ...
        ]
    """
    batch: List[Dict[str, Any]] = []
    root = Path(repo_path)

    for file_rel in file_list:
        full_path = root / file_rel
        content = read_file_safe(str(full_path))
        if content is None:
            continue

        file_type = Path(file_rel).suffix
        blocks: List[Dict[str, Any]] = extract_relevant_markup(
            content, file_type, include_metadata=True
        )
        if not blocks:
            continue

        chunk_idx = 0
        for block in blocks:
            block_content = block["content"]
            block_start_line = block.get("start_line", 1)
            if not block_content.strip():
                continue

            chunks = chunk_large_file(block_content, max_tokens=2000)
            running_line = block_start_line
            for chunk in chunks:
                if not chunk.strip():
                    continue

                first_line = chunk.strip().splitlines()[0].strip()
                chunk_start_line = running_line
                if first_line:
                    pos = content.find(first_line)
                    if pos != -1:
                        chunk_start_line = content[:pos].count("\n") + 1
                    else:
                        sub_pos = block_content.find(first_line)
                        if sub_pos != -1:
                            chunk_start_line = block_start_line + block_content[:sub_pos].count("\n")

                estimated_tokens = max(1, len(chunk) // 4)
                batch.append({
                    "file": file_rel,
                    "chunk_index": chunk_idx,
                    "content": chunk,
                    "start_line": chunk_start_line,
                    "estimated_tokens": estimated_tokens,
                })
                chunk_idx += 1
                running_line = chunk_start_line + chunk.count("\n") + 1

    logger.info(f"Prepared scan batch of {len(batch)} chunks from {len(file_list)} files.")
    return batch
