"""
Tests for CodeGuard Scanner Service (Phase 9):
Markup extraction, file chunking, safe resilient reading, and scan batch preparation.
"""
from pathlib import Path
import tempfile
import pytest

from app.services.scanner_service import (
    read_file_safe,
    extract_relevant_markup,
    chunk_large_file,
    prepare_scan_batch,
)


def test_normal_small_tsx_extraction():
    """Verify JSX return statements are extracted from a small .tsx component."""
    tsx_content = """import React, { useState } from 'react';
import { Button } from './ui/button';

interface Props {
  title: string;
}

export const HeroHeader: React.FC<Props> = ({ title }) => {
  const [count, setCount] = useState(0);

  const handleClick = () => {
    setCount(count + 1);
  };

  return (
    <header className="hero-banner" role="banner">
      <h1 tabIndex={0}>{title}</h1>
      <button onClick={handleClick} aria-label="Increment counter">
        Count: {count}
      </button>
    </header>
  );
};

export default HeroHeader;
"""
    markup = extract_relevant_markup(tsx_content, ".tsx")
    assert "<header" in markup
    assert 'role="banner"' in markup
    assert '<h1 tabIndex={0}>{title}</h1>' in markup
    assert '<button onClick={handleClick} aria-label="Increment counter">' in markup
    # Imports and typescript interfaces should be stripped out to reduce token usage
    assert "import React" not in markup
    assert "interface Props" not in markup


def test_vue_template_block_isolation():
    """Verify only the <template> block is isolated from a Vue single file component."""
    vue_content = """<template>
  <main class="dashboard-container" role="main">
    <nav aria-label="Breadcrumb navigation">
      <ol>
        <li><a href="/">Home</a></li>
        <li aria-current="page">Dashboard</li>
      </ol>
    </nav>
    <section aria-labelledby="status-heading">
      <h2 id="status-heading">System Status</h2>
      <img src="/status.png" alt="All systems operational" />
    </section>
  </main>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue';

export default defineComponent({
  name: 'DashboardView',
  setup() {
    const active = ref(true);
    return { active };
  }
});
</script>

<style scoped>
.dashboard-container {
  padding: 2rem;
  background: #0f172a;
}
</style>
"""
    markup = extract_relevant_markup(vue_content, ".vue")
    assert markup.startswith("<template>")
    assert markup.endswith("</template>")
    assert '<main class="dashboard-container"' in markup
    assert '<nav aria-label="Breadcrumb navigation">' in markup
    # Script and style sections should not be present
    assert "<script" not in markup
    assert "defineComponent" not in markup
    assert "<style" not in markup


def test_html_script_and_style_stripping():
    """Verify HTML files have script and style tags stripped to save LLM tokens."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Accessible Landing Page</title>
  <style>
    body { font-family: sans-serif; background: #fff; }
    .hero { min-height: 80vh; }
  </style>
  <script>
    console.log("analytics tracker");
  </script>
</head>
<body>
  <header>
    <h1>Welcome to CodeGuard</h1>
  </header>
  <main>
    <img src="/logo.svg" alt="CodeGuard logo" />
  </main>
  <script src="/bundle.js"></script>
</body>
</html>
"""
    markup = extract_relevant_markup(html_content, ".html")
    assert "<h1>Welcome to CodeGuard</h1>" in markup
    assert '<img src="/logo.svg" alt="CodeGuard logo" />' in markup
    assert "<style>" not in markup
    assert "font-family: sans-serif" not in markup
    assert "<script>" not in markup
    assert "console.log" not in markup


def test_large_file_chunking_on_component_boundaries():
    """Verify that a large file exceeding max_tokens is split into multiple pieces."""
    # Build a synthetic component collection exceeding 2000 tokens (>8000 chars)
    components = []
    for i in range(15):
        comp = f"""
export function SectionWidget{i}() {{
  return (
    <section id="section-{i}" aria-labelledby="heading-{i}">
      <h2 id="heading-{i}">Component Section {i}</h2>
      <p>This is a detailed accessibility content block number {i} with descriptive text.</p>
      <button aria-label="Action button for section {i}">Trigger Action {i}</button>
    </section>
  );
}}
"""
        components.append(comp)

    large_content = "\n\n".join(components)
    assert len(large_content) > 4000

    # With max_tokens=250 (max_chars ~1000), it must split into multiple chunks
    chunks = chunk_large_file(large_content, max_tokens=250)
    assert len(chunks) > 1

    # Verify each chunk is a valid non-empty string and retains component sections
    total_reconstructed = 0
    for chunk in chunks:
        assert len(chunk) > 0
        assert "SectionWidget" in chunk or "section id=" in chunk
        total_reconstructed += len(chunk)

    assert total_reconstructed > 0


def test_binary_file_returns_none_and_does_not_crash():
    """Verify that unreadable or binary files (containing null bytes) return None."""
    with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as f:
        # Write binary content with null bytes
        f.write(b"PNG\x00\x01\x02\x03\x00BINARY_BLOB_MOCK")
        binary_path = f.name

    try:
        content = read_file_safe(binary_path)
        assert content is None
    finally:
        Path(binary_path).unlink(missing_ok=True)


def test_prepare_scan_batch_skips_unreadable_gracefully():
    """
    Verify prepare_scan_batch processes valid files, skips unreadable/binary files,
    and returns correct chunk dict structure without crashing.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # 1. Create a valid TSX file
        tsx_file = root / "src" / "App.tsx"
        tsx_file.parent.mkdir(parents=True, exist_ok=True)
        tsx_file.write_text(
            """export default function App() {
  return (
    <main>
      <h1>App Title</h1>
      <img src="avatar.jpg" alt="User avatar" />
    </main>
  );
}""",
            encoding="utf-8",
        )

        # 2. Create a valid Vue file
        vue_file = root / "src" / "Modal.vue"
        vue_file.write_text(
            """<template>
  <div role="dialog" aria-modal="true" aria-labelledby="modal-title">
    <h2 id="modal-title">Notice</h2>
    <button aria-label="Close dialog">X</button>
  </div>
</template>
<script>export default {}</script>""",
            encoding="utf-8",
        )

        # 3. Create a binary file
        bin_file = root / "src" / "corrupt.tsx"
        with open(bin_file, "wb") as bf:
            bf.write(b"\x00\x00\x00CORRUPT_NULL_BYTES\x00\x00")

        # 4. Reference a non-existent file
        file_list = [
            "src/App.tsx",
            "src/Modal.vue",
            "src/corrupt.tsx",
            "src/does_not_exist.jsx",
        ]

        batch = prepare_scan_batch(str(root), file_list)

        # Batch should contain items for App.tsx and Modal.vue, skipping corrupt and missing files
        assert len(batch) >= 2
        files_in_batch = {item["file"] for item in batch}
        assert "src/App.tsx" in files_in_batch
        assert "src/Modal.vue" in files_in_batch
        assert "src/corrupt.tsx" not in files_in_batch
        assert "src/does_not_exist.jsx" not in files_in_batch

        # Validate structure of each batch chunk item
        for item in batch:
            assert "file" in item
            assert "chunk_index" in item
            assert "content" in item
            assert "estimated_tokens" in item
            assert item["chunk_index"] >= 0
            assert item["estimated_tokens"] >= 1
            assert len(item["content"]) > 0


def test_safe_read_encoding_fallback():
    """Verify read_file_safe can handle non-utf-8 encodings like latin-1."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        # Write bytes valid in latin-1 / cp1252 but invalid in strict utf-8
        f.write(b"Caf\xe9 and Cr\xe8me Br\xfbl\xe9e")
        file_path = f.name

    try:
        content = read_file_safe(file_path)
        assert content is not None
        assert "Caf" in content
    finally:
        Path(file_path).unlink(missing_ok=True)
