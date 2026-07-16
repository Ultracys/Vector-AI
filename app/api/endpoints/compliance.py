import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.compliance import ComplianceStatusResponse, ComplianceAuditSummary
from app.core.logging import log_audit_event
from app.core.database import get_db, DBTransaction, DBSecurityLog, DBComplianceSetting

router = APIRouter()

@router.get("/compliance/status", response_model=ComplianceStatusResponse)
async def get_compliance_status(db: Session = Depends(get_db)):
    current_time = datetime.now(timezone.utc).isoformat()
    
    # Query database for actual transaction counts
    try:
        tx_count = db.query(DBTransaction).filter(DBTransaction.status != "blocked").count()
        blocked_count = db.query(DBTransaction).filter(DBTransaction.status == "blocked").count()
    except Exception:
        tx_count = 0
        blocked_count = 0
    
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

@router.get("/compliance/transactions")
async def get_compliance_transactions(db: Session = Depends(get_db), limit: int = 50):
    import json
    try:
        txs = db.query(DBTransaction).order_by(DBTransaction.created_at.desc()).limit(limit).all()
        return [
            {
                "id": t.id,
                "transaction_id": t.transaction_id,
                "correlation_id": t.correlation_id,
                "debtor_account": {"iban": t.debtor_iban, "bank_code": t.debtor_bank, "account_holder": t.debtor_holder},
                "creditor_account": {"iban": t.creditor_iban, "bank_code": t.creditor_bank, "account_holder": t.creditor_holder},
                "amount": t.amount,
                "currency": t.currency,
                "narrative": t.narrative,
                "status": t.status,
                "risk_level": t.risk_level,
                "sama_compliance_code": t.sama_compliance_code,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in txs
        ]
    except Exception as e:
        return {"error": str(e)}

@router.get("/compliance/logs")
async def get_compliance_logs(db: Session = Depends(get_db), limit: int = 50):
    import json
    try:
        logs = db.query(DBSecurityLog).order_by(DBSecurityLog.created_at.desc()).limit(limit).all()
        return [
            {
                "id": l.id,
                "correlation_id": l.correlation_id,
                "transaction_id": l.transaction_id,
                "action": l.action,
                "message": l.message,
                "status": l.status,
                "sama_reference": l.sama_reference,
                "latency_ms": l.latency_ms,
                "extra_data": json.loads(l.extra_data) if l.extra_data else {},
                "created_at": l.created_at.isoformat() if l.created_at else None
            }
            for l in logs
        ]
    except Exception as e:
        return {"error": str(e)}

@router.post("/compliance/settings")
async def update_compliance_settings(payload: dict, db: Session = Depends(get_db)):
    try:
        for k, v in payload.items():
            setting = db.query(DBComplianceSetting).filter_by(key=k).first()
            if setting:
                setting.value = str(v)
            else:
                db.add(DBComplianceSetting(key=k, value=str(v)))
        db.commit()
        return {"status": "updated"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}

@router.get("/compliance/settings")
async def get_compliance_settings(db: Session = Depends(get_db)):
    try:
        settings_list = db.query(DBComplianceSetting).all()
        return {s.key: s.value for s in settings_list}
    except Exception as e:
        return {"error": str(e)}


