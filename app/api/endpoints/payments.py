import time
import uuid
import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.schemas.payments import PaymentInitiationRequest, PaymentInitiationResponse
from app.core.security import evaluate_semantic_threat
from app.core.risk import evaluate_transaction_risk
from app.core.logging import log_audit_event
from app.config import settings
from app.core.database import get_db, DBTransaction, DBSecurityLog, DBComplianceSetting
from app.core.fapi_middleware import verify_sama_fapi_headers
from typing import Optional, List

router = APIRouter()

# Keep a basic thread-safe/in-memory count as a fallback
audit_counters = {
    "total_tx": 0,
    "total_blocked": 0
}

@router.post("/payments/initiate", response_model=PaymentInitiationResponse)
async def initiate_payment(
    request: Request, 
    payload: PaymentInitiationRequest,
    db: Session = Depends(get_db),
    _ = Depends(verify_sama_fapi_headers)
):
    start_time = time.perf_counter()
    correlation_id = payload.correlation_id or str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"
    transaction_id = f"899-TX-{uuid.uuid4().hex[:6].upper()}"
    
    # Extract dynamic limit from compliance_settings
    try:
        limit_setting = db.query(DBComplianceSetting).filter_by(key="sama_auto_approve_limit").first()
        auto_approve_limit = float(limit_setting.value) if limit_setting else settings.SAMA_AUTO_APPROVE_LIMIT
    except Exception:
        auto_approve_limit = settings.SAMA_AUTO_APPROVE_LIMIT
    
    # Extract optional red-team parameters from headers (for Red-Team Arena)
    active_layers_header = request.headers.get("X-Security-Layers")
    susceptibility_header = request.headers.get("X-Susceptibility")
    
    active_layers = None
    if active_layers_header:
        active_layers = [l.strip() for l in active_layers_header.split(",") if l.strip()]
    
    susceptibility = 0.0
    if susceptibility_header:
        try:
            susceptibility = max(0.0, min(1.0, float(susceptibility_header)))
        except ValueError:
            pass

    # 1. Semantic Check on the payment narrative/prompt
    is_threat, score, threat_type, metadata = evaluate_semantic_threat(
        payload.narrative,
        active_layers=active_layers,
        susceptibility=susceptibility,
    )
    
    if is_threat:
        audit_counters["total_blocked"] += 1
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        # Log central bank audit record for transaction intercept
        log_audit_event(
            action="PAYMENT_INITIATION_INTERCEPT",
            message=f"Payment block: narrative contains threat {threat_type} (score: {score:.2f})",
            status="BLOCKED",
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            client_ip=client_ip,
            latency_ms=latency_ms,
            sama_reference="SAMA-OB-PIS-SEC-204",
            extra_data={
                "amount": payload.amount,
                "currency": payload.currency,
                "threat_type": threat_type,
                "narrative": payload.narrative,
                "risk_matrix": metadata.get("risk_matrix"),
            }
        )
        
        # Persist transaction as BLOCKED in SQLite
        try:
            db_tx = DBTransaction(
                transaction_id=transaction_id,
                correlation_id=correlation_id,
                debtor_iban=payload.debtor_account.iban,
                debtor_bank=payload.debtor_account.bank_code,
                debtor_holder=payload.debtor_account.account_holder,
                creditor_iban=payload.creditor_account.iban,
                creditor_bank=payload.creditor_account.bank_code,
                creditor_holder=payload.creditor_account.account_holder,
                amount=payload.amount,
                currency=payload.currency,
                narrative=payload.narrative,
                status="blocked",
                risk_level="critical",
                sama_compliance_code="SAMA-OB-PIS-SEC-204"
            )
            db.add(db_tx)
            
            db_log = DBSecurityLog(
                correlation_id=correlation_id,
                transaction_id=transaction_id,
                action="PAYMENT_INITIATION_INTERCEPT",
                message=f"Payment block: narrative contains threat {threat_type} (score: {score:.2f})",
                status="BLOCKED",
                sama_reference="SAMA-OB-PIS-SEC-204",
                latency_ms=latency_ms,
                extra_data=json.dumps(metadata)
            )
            db.add(db_log)
            db.commit()
        except Exception as db_err:
            db.rollback()
            print(f"Database error: {db_err}")
        
        return JSONResponse(
            status_code=403,
            content={
                "status": "blocked",
                "reason": "Semantic anomaly detected",
                "threat_type": threat_type,
                "risk_score": score,
                "risk_matrix": metadata.get("risk_matrix"),
                "llm_report": metadata.get("llm_report"),
                "decoded_prompt": metadata.get("decoded_prompt"),
                "layer_results": metadata.get("layer_results"),
            }
        )
        
    # 2. Dynamic Authorization Check on amount
    auth_decision, risk_level = evaluate_transaction_risk(payload.amount, is_anomalous=False, auto_approve_limit=auto_approve_limit)
    audit_counters["total_tx"] += 1
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    
    # Log SAMA PIS audit trail record
    sama_code = "SAMA-OB-PIS-AUT-102" if auth_decision["status"] == "approved" else "SAMA-OB-PIS-VER-105"
    
    log_audit_event(
        action="PAYMENT_INITIATION_EVALUATION",
        message=f"Payment initiated. Status: {auth_decision['status'].upper()}, Risk level: {risk_level}",
        status=auth_decision["status"].upper(),
        transaction_id=transaction_id,
        correlation_id=correlation_id,
        client_ip=client_ip,
        latency_ms=latency_ms,
        sama_reference=sama_code,
        extra_data={
            "amount": payload.amount,
            "currency": payload.currency,
            "debtor_iban": payload.debtor_account.iban,
            "creditor_iban": payload.creditor_account.iban,
            "agent_id": payload.agent_id
        }
    )
    
    # Persist transaction in SQLite
    try:
        db_tx = DBTransaction(
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            debtor_iban=payload.debtor_account.iban,
            debtor_bank=payload.debtor_account.bank_code,
            debtor_holder=payload.debtor_account.account_holder,
            creditor_iban=payload.creditor_account.iban,
            creditor_bank=payload.creditor_account.bank_code,
            creditor_holder=payload.creditor_account.account_holder,
            amount=payload.amount,
            currency=payload.currency,
            narrative=payload.narrative,
            status=auth_decision["status"],
            risk_level=risk_level.lower(),
            sama_compliance_code=sama_code
        )
        db.add(db_tx)
        
        db_log = DBSecurityLog(
            correlation_id=correlation_id,
            transaction_id=transaction_id,
            action="PAYMENT_INITIATION_EVALUATION",
            message=f"Payment initiated. Status: {auth_decision['status'].upper()}, Risk level: {risk_level}",
            status=auth_decision["status"].upper(),
            sama_reference=sama_code,
            latency_ms=latency_ms,
            extra_data=json.dumps({
                "amount": payload.amount,
                "currency": payload.currency,
                "agent_id": payload.agent_id,
                "reason": auth_decision["reason"]
            })
        )
        db.add(db_log)
        db.commit()
    except Exception as db_err:
        db.rollback()
        print(f"Database error: {db_err}")
    
    return PaymentInitiationResponse(
        transaction_id=transaction_id,
        status=auth_decision["status"],
        risk_level=risk_level.lower(),
        sama_compliance_code=sama_code,
        reason=auth_decision["reason"]
    )

