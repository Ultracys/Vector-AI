from pydantic import BaseModel, Field
from typing import Dict, Any, List

class ComplianceAuditSummary(BaseModel):
    total_audited_transactions: int = Field(..., description="Cumulative transaction checks run.")
    total_blocked_attacks: int = Field(..., description="Cumulative semantic threats intercepted.")
    compliance_percentage: float = Field(..., description="System compliance index score.")
    sama_guidelines_mapped: List[str] = Field(..., description="List of SAMA frameworks active in validation logic.")

class ComplianceStatusResponse(BaseModel):
    status: str = Field("COMPLIANT", description="Overall system compliance status.")
    environment: str = Field("sandbox", description="Operating environment context.")
    last_audit_sync: str = Field(..., description="Timestamp of last regulatory sync (ISO-8601).")
    sandbox_metrics: ComplianceAuditSummary = Field(..., description="Sandbox telemetry details.")
