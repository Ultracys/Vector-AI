import time
from datetime import datetime, timezone
from fastapi import APIRouter
from app.schemas.compliance import ComplianceStatusResponse, ComplianceAuditSummary
from app.api.endpoints.payments import audit_counters
from app.core.logging import log_audit_event

router = APIRouter()

@router.get("/compliance/status", response_model=ComplianceStatusResponse)
async def get_compliance_status():
    current_time = datetime.now(timezone.utc).isoformat()
    
    # Simple compliance rate simulation: starts at 100%, maintains high score
    tx_count = audit_counters["total_tx"]
    blocked_count = audit_counters["total_blocked"]
    
    # Log regulatory check request
    log_audit_event(
        action="COMPLIANCE_STATUS_QUERY",
        message="Compliance monitoring state queried by SAMA Auditor Node",
        status="COMPLIANT",
        sama_reference="SAMA-OB-COMP-AUD-099",
        extra_data={"tx_count": tx_count, "blocked_count": blocked_count}
    )
    
    summary = ComplianceAuditSummary(
        total_audited_transactions=tx_count + blocked_count,
        total_blocked_attacks=blocked_count,
        compliance_percentage=100.0 if (tx_count + blocked_count) == 0 else round((tx_count / (tx_count + blocked_count)) * 100.0, 2),
        sama_guidelines_mapped=[
            "SAMA-OB-PIS-SEC-101 (Consent & Cryptographic Integrity)",
            "SAMA-OB-PIS-SEC-204 (Semantic Input Sanitization & Guardrails)",
            "SAMA-OB-PIS-AUT-102 (Dynamic Authorization Control)",
            "SAMA-OB-PIS-VER-105 (Cognitive Risk Step-up Challenge)"
        ]
    )
    
    return ComplianceStatusResponse(
        status="COMPLIANT",
        environment="sandbox",
        last_audit_sync=current_time,
        sandbox_metrics=summary
    )
