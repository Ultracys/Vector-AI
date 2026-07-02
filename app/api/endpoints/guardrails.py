import time
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.schemas.guardrails import PromptValidationRequest, PromptValidationResponse
from app.core.security import evaluate_semantic_threat
from app.core.logging import log_audit_event
from app.config import settings

router = APIRouter()

@router.post("/validate-prompt", response_model=PromptValidationResponse)
async def validate_prompt(request: Request, payload: PromptValidationRequest):
    start_time = time.perf_counter()
    correlation_id = payload.correlation_id or str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"
    
    # Determine active security layers
    active_layers = payload.active_layers or settings.DEFAULT_ACTIVE_LAYERS.copy()
    susceptibility = payload.susceptibility if payload.susceptibility is not None else settings.DEFAULT_SUSCEPTIBILITY

    # Run Multi-Layer Semantic Guardrail Security Evaluation
    is_threat, score, threat_type, metadata = evaluate_semantic_threat(
        payload.prompt,
        active_layers=active_layers,
        susceptibility=susceptibility,
    )
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    
    if is_threat:
        # SAMA Audit log for security block event
        log_audit_event(
            action="PROMPT_VALIDATION",
            message=f"Semantic anomaly blocked: prompt matches {threat_type} (score: {score:.2f})",
            status="BLOCKED",
            correlation_id=correlation_id,
            client_ip=client_ip,
            latency_ms=latency_ms,
            sama_reference="SAMA-OB-PIS-SEC-204", # Regulatory standard for PIS injection guard
            extra_data={
                "threat_type": threat_type, 
                "score": score, 
                "prompt_length": len(payload.prompt),
                "active_layers": active_layers,
                "susceptibility": susceptibility,
                "risk_matrix": metadata.get("risk_matrix"),
            }
        )
        # SAMA compliant 403 Forbidden payload
        return JSONResponse(
            status_code=403,
            content={
                "status": "blocked",
                "risk_score": score,
                "threat_type": threat_type,
                "reason": "Semantic anomaly detected",
                "risk_matrix": metadata.get("risk_matrix"),
                "llm_report": metadata.get("llm_report"),
                "decoded_prompt": metadata.get("decoded_prompt"),
                "layer_results": metadata.get("layer_results"),
            }
        )
        
    # Log successful validation trace
    log_audit_event(
        action="PROMPT_VALIDATION",
        message="Prompt successfully validated by Vector Guardrails Gateway",
        status="VALIDATED",
        correlation_id=correlation_id,
        client_ip=client_ip,
        latency_ms=latency_ms,
        sama_reference="SAMA-OB-PIS-SEC-101",
        extra_data={
            "score": score, 
            "prompt_length": len(payload.prompt),
            "active_layers": active_layers,
            "susceptibility": susceptibility,
        }
    )
    
    return PromptValidationResponse(
        status="validated",
        risk_score=score,
        threat_type=threat_type,
        reason="Prompt conforms to security baseline parameters.",
        risk_matrix=metadata.get("risk_matrix"),
        llm_report=metadata.get("llm_report"),
        decoded_prompt=metadata.get("decoded_prompt"),
        layer_results=metadata.get("layer_results"),
    )
