from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from pydantic import BaseModel
from app.db.session import get_db
from app.db.models import CSPViolationReport
import json

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/security", tags=["security"])

class CSPReportPayload(BaseModel):
    # Depending on browser implementation, it comes wrapped in 'csp-report'
    csp_report: dict

async def process_csp_report(report_data: dict, db: AsyncSession, ip_address: str):
    """Background task to store CSP reports in the database and trigger analytics."""
    try:
        report = CSPViolationReport(
            document_uri=report_data.get("document-uri"),
            referrer=report_data.get("referrer"),
            violated_directive=report_data.get("violated-directive"),
            effective_directive=report_data.get("effective-directive"),
            original_policy=report_data.get("original-policy"),
            disposition=report_data.get("disposition"),
            blocked_uri=report_data.get("blocked-uri"),
            status_code=report_data.get("status-code"),
            source_file=report_data.get("source-file"),
            line_number=report_data.get("line-number"),
            column_number=report_data.get("column-number"),
            user_agent=report_data.get("user-agent"),
            ip_address=ip_address
        )
        db.add(report)
        await db.commit()
        
        # Threat intelligence hook could go here (e.g., notify Slack if spike in violations)
        logger.info("csp_violation_logged", blocked_uri=report.blocked_uri, directive=report.violated_directive)
    except Exception as e:
        logger.error("csp_report_processing_failed", error=str(e))
        await db.rollback()

@router.post("/csp-report", status_code=204)
async def csp_report_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint designated in the Content-Security-Policy `report-uri` directive.
    Receives JSON violation reports from user browsers when a resource is blocked.
    """
    try:
        # CSP reports are sent as application/csp-report content type
        body = await request.body()
        if not body:
            return
            
        data = json.loads(body.decode("utf-8"))
        report_data = data.get("csp-report", {})
        
        if not report_data:
            return
            
        ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        
        # Offload DB insertion to background task to keep endpoint blazing fast
        background_tasks.add_task(process_csp_report, report_data, db, ip)
        
    except json.JSONDecodeError:
        logger.warning("invalid_csp_report_json")
    except Exception as e:
        logger.error("csp_endpoint_error", error=str(e))
        
    # Always return 204 No Content per W3C Spec
    return None
