"""
Scan Router: Endpoints to initiate repository accessibility audits, clone repos, prepare batches, and manage scan state.
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ScanRequest, ScanStartResponse
from app.services.git_service import (
    clone_repo,
    find_frontend_files,
    get_repo_metadata,
    cleanup_repo,
    InvalidRepoUrlError,
    RepoNotFoundError,
    RepoTooLargeError,
    CloneFailedError,
)
from app.services.scanner_service import prepare_scan_batch
from app.services.sandbox_orchestrator import cleanup_scan_sandboxes
from app.state import create_scan, get_scan, update_scan, remove_scan

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scanning"])


@router.post(
    "/start",
    response_model=ScanStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Clone repository, extract markup, and prepare scan batches",
)
async def start_scan(request: ScanRequest) -> ScanStartResponse:
    """
    Validates, shallow-clones the remote repository, discovers frontend UI files,
    detects framework, extracts relevant markup into chunks, and initializes scan state.
    """
    branch = request.branch or "main"
    scan_id = create_scan(repo_url=request.repo_url, branch=branch)

    try:
        # 1. Perform shallow clone (depth=1)
        repo_path = clone_repo(repo_url=request.repo_url, scan_id=scan_id, branch=branch)

        # 2. Discover scannable frontend files
        scannable_files = find_frontend_files(repo_path)

        # 3. Detect framework and metadata
        metadata = get_repo_metadata(repo_path)

        # 4. Prepare scan batches (read, extract markup, chunk large files)
        scan_batch = prepare_scan_batch(repo_path, scannable_files)

        # 5. Save metadata and scan batches to in-memory state store
        import time
        start_time_val = time.time()
        update_scan(
            scan_id=scan_id,
            repo_path=repo_path,
            files=scannable_files,
            file_count=len(scannable_files),
            framework=metadata.get("framework", "Vanilla HTML/JS"),
            metadata=metadata,
            scan_batch=scan_batch,
            batch_count=len(scan_batch),
            status="prepared",
            is_active_real_scan=True,
            start_timestamp=start_time_val,
        )

        # 6. Kick off detection and diagnosis pipeline as background task
        async def run_detection_pipeline():
            try:
                from app.services.detector_service import detect_violations
                await detect_violations(scan_id)

                # Phase 14: Run root-cause diagnosis across prioritized violations
                from app.services.diagnosis_service import diagnose_all
                await diagnose_all(scan_id)

                # Phase 15: Generate stakeholder-friendly plain English explanations
                from app.services.explainer_service import generate_all_explanations
                await generate_all_explanations(scan_id)

                # Phase 16: Synthesize code-fix patches with Nemotron Ultra
                from app.services.fixer_service import generate_all_fixes
                await generate_all_fixes(scan_id)

                # Phase 20: Verify fixes with axe-core in isolated sandboxes
                from app.services.verification_service import (
                    verify_all_fixes,
                    calculate_overall_improvement,
                )
                await verify_all_fixes(scan_id)
                await calculate_overall_improvement(scan_id)

                # Phase 22 & 23: Build final unified ScanReport, generate executive summary, and save files
                from app.services.aggregator_service import build_scan_report
                from app.services.report_formatter_service import (
                    generate_executive_summary,
                    save_report_files,
                )
                from app.routers.websocket import broadcast_progress

                final_report = build_scan_report(scan_id)

                # Generate executive summary via Nemotron Fast (with fallback)
                exec_summary = await generate_executive_summary(final_report)
                final_report.executive_summary = exec_summary
                update_scan(scan_id=scan_id, report=final_report, executive_summary=exec_summary)

                # Persist formatted reports to disk
                try:
                    save_report_files(final_report, scan_id, executive_summary=exec_summary)
                except Exception as save_err:
                    logger.warning(f"Could not persist report files: {save_err}")

                stats = final_report.summary or {}
                verified_count = stats.get("fixed_and_verified", 0)
                unverified_count = stats.get("fixed_not_verified", 0)
                total_violations = stats.get("total_violations", len(final_report.violations))

                if verified_count > 0:
                    completion_msg = f"Scan complete — {verified_count} of {total_violations} violations fixed and verified"
                elif unverified_count > 0:
                    completion_msg = f"Scan complete — {unverified_count} of {total_violations} fixes proposed (unverified, sandbox unavailable)"
                else:
                    completion_msg = f"Scan complete — {total_violations} violations analyzed"
                await broadcast_progress(
                    scan_id=scan_id,
                    stage="complete",
                    progress=100,
                    message=completion_msg,
                    data={
                        "fixed_and_verified": verified_count,
                        "total_violations": total_violations,
                        "score_before": final_report.overall_score_before,
                        "score_after": final_report.overall_score_after,
                        "executive_summary": exec_summary,
                    },
                )
            except Exception as bg_err:
                logger.error(f"Error during background violation pipeline for {scan_id}: {bg_err}", exc_info=True)
                await cleanup_scan_sandboxes(scan_id)
                try:
                    from app.routers.websocket import broadcast_progress
                    await broadcast_progress(
                        scan_id=scan_id,
                        stage="error",
                        progress=0,
                        message=f"Pipeline error: {str(bg_err)}",
                    )
                except Exception:
                    pass

        asyncio.create_task(run_detection_pipeline())

        return ScanStartResponse(
            scan_id=scan_id,
            status="queued",
            message=f"Repository cloned. Prepared {len(scan_batch)} scan chunks across {len(scannable_files)} UI files.",
            repo_url=request.repo_url,
            branch=branch,
            file_count=len(scannable_files),
            framework=metadata.get("framework", "Vanilla HTML/JS"),
            scannable_files=scannable_files,
            batch_count=len(scan_batch),
        )

    except InvalidRepoUrlError as exc:
        await cleanup_scan_sandboxes(scan_id)
        cleanup_repo(scan_id)
        remove_scan(scan_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except RepoNotFoundError as exc:
        await cleanup_scan_sandboxes(scan_id)
        cleanup_repo(scan_id)
        remove_scan(scan_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except RepoTooLargeError as exc:
        await cleanup_scan_sandboxes(scan_id)
        cleanup_repo(scan_id)
        remove_scan(scan_id)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        )
    except CloneFailedError as exc:
        await cleanup_scan_sandboxes(scan_id)
        cleanup_repo(scan_id)
        remove_scan(scan_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception as exc:
        await cleanup_scan_sandboxes(scan_id)
        cleanup_repo(scan_id)
        remove_scan(scan_id)
        logger.error(f"Unexpected error in start_scan: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error preparing repository for scan: {str(exc)}",
        )


@router.get(
    "/{scan_id}",
    summary="Get scan metadata and status",
)
async def get_scan_status(scan_id: str):
    """Retrieve metadata and high-level progress for a given scan_id."""
    scan = get_scan(scan_id)
    return {
        "scan_id": scan_id,
        "repo_url": scan.get("repo_url"),
        "branch": scan.get("branch"),
        "status": scan.get("status"),
        "progress": scan.get("progress", 100),
        "file_count": scan.get("file_count", len(scan.get("files", []))),
        "batch_count": scan.get("batch_count", len(scan.get("scan_batch", []))),
        "framework": scan.get("framework"),
        "files": scan.get("files", []),
    }


@router.get(
    "/{scan_id}/batch",
    summary="Get extracted scan chunks ready for LLM processing",
)
async def get_scan_batch(scan_id: str):
    """Returns the prepared code chunks for a given scan_id."""
    scan = get_scan(scan_id)
    return {
        "scan_id": scan_id,
        "batch_count": len(scan.get("scan_batch", [])),
        "batch": scan.get("scan_batch", []),
    }


@router.delete(
    "/{scan_id}",
    summary="Clean up temporary cloned repository and release disk space",
)
async def delete_scan(scan_id: str):
    """Deletes temporary repository clone and removes scan from memory."""
    await cleanup_scan_sandboxes(scan_id)
    cleanup_repo(scan_id)
    remove_scan(scan_id)
    return {
        "status": "success",
        "message": f"Cleaned up temporary workspace for scan {scan_id}",
    }
