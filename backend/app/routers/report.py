"""
Report Router: Endpoints to retrieve full accessibility audit and verification reports.
"""
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import ScanReport
from app.services.aggregator_service import build_scan_report
from app.state import get_scan

router = APIRouter(tags=["Reports"])


@router.get(
    "/{scan_id}",
    response_model=ScanReport,
    summary="Get complete audit report and compliance score",
)
async def get_scan_report(scan_id: str) -> ScanReport:
    """
    Retrieve comprehensive report containing before/after compliance scores,
    all identified violations, synthesized patches, and sandbox test results.
    Returns the real aggregated report from build_scan_report().
    """
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan report not found for scan_id: {scan_id}",
        )

    # Return cached report if available, otherwise dynamically build it
    report = scan.get("report")
    if not report or not getattr(report, "unified_records", None):
        try:
            report = build_scan_report(scan_id)
        except Exception as exc:
            # If report is already present, fallback
            if not report:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error compiling scan report: {str(exc)}",
                )

    return report


@router.get(
    "/{scan_id}/markdown",
    summary="Get complete report as formatted raw Markdown",
)
async def get_scan_report_markdown(scan_id: str):
    """Returns the comprehensive audit report as clean, formatted Markdown."""
    from fastapi.responses import PlainTextResponse
    from app.services.report_formatter_service import (
        format_report_as_markdown,
        generate_executive_summary,
    )

    report = await get_scan_report(scan_id)
    summary = report.executive_summary or await generate_executive_summary(report)
    md_content = format_report_as_markdown(report, summary)
    return PlainTextResponse(content=md_content, media_type="text/plain; charset=utf-8")


@router.get(
    "/{scan_id}/html",
    summary="Get complete report as formatted HTML document",
)
async def get_scan_report_html(scan_id: str):
    """Returns the comprehensive audit report as a styled standalone HTML document."""
    from fastapi.responses import HTMLResponse
    from app.services.report_formatter_service import (
        format_report_as_html,
        generate_executive_summary,
    )

    report = await get_scan_report(scan_id)
    summary = report.executive_summary or await generate_executive_summary(report)
    html_content = format_report_as_html(report, summary)
    return HTMLResponse(content=html_content, media_type="text/html; charset=utf-8")


@router.get(
    "/{scan_id}/download",
    summary="Download complete audit report as standalone HTML file",
)
async def download_scan_report(scan_id: str):
    """Offers the standalone HTML audit report as a downloadable file attachment."""
    from fastapi.responses import Response
    from app.services.report_formatter_service import (
        format_report_as_html,
        generate_executive_summary,
        save_report_files,
    )

    report = await get_scan_report(scan_id)
    summary = report.executive_summary or await generate_executive_summary(report)
    html_content = format_report_as_html(report, summary)

    # Also persist to disk
    try:
        save_report_files(report, scan_id, executive_summary=summary)
    except Exception as save_err:
        logger.warning(f"Could not persist report files to disk: {save_err}")

    filename = f"codeguard-report-{scan_id}.html"
    return Response(
        content=html_content,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
