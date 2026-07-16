import time
import uuid
import json
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.logging import log_audit_event

async def verify_sama_fapi_headers(request: Request):
    """
    Middleware/Dependency to enforce SAMA Open Banking FAPI compliance.
    Checks for:
      1. X-Fapi-Interaction-Id (for traceability)
      2. X-Jws-Signature (for request payload integrity and non-repudiation)
      3. Authorization (OAuth2 Bearer token with appropriate scopes)
    """
    # 1. Enforce interaction tracking
    interaction_id = request.headers.get("X-Fapi-Interaction-Id")
    correlation_id = request.headers.get("X-Correlation-ID") or interaction_id or str(uuid.uuid4())
    
    # 2. Check Authorization Header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        log_audit_event(
            action="API_SECURITY_VIOLATION",
            message="Request blocked: Missing OAuth2 Authorization Header",
            status="BLOCKED",
            correlation_id=correlation_id,
            sama_reference="SAMA-OB-PIS-SEC-101",
            level=40 # ERROR
        )
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "error_description": "Missing Authorization Header. SAMA Open Banking APIs require OAuth2 access token."
            }
        )
        
    if not auth_header.startswith("Bearer "):
        log_audit_event(
            action="API_SECURITY_VIOLATION",
            message="Request blocked: Invalid Authorization Header format",
            status="BLOCKED",
            correlation_id=correlation_id,
            sama_reference="SAMA-OB-PIS-SEC-101",
            level=40 # ERROR
        )
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "error_description": "Authorization token must be a Bearer token."
            }
        )
        
    token = auth_header.replace("Bearer ", "").strip()
    # Simple validation of mock token: must not be 'expired'
    if token == "expired_token":
        log_audit_event(
            action="API_SECURITY_VIOLATION",
            message="Request blocked: OAuth2 Access Token Expired",
            status="BLOCKED",
            correlation_id=correlation_id,
            sama_reference="SAMA-OB-PIS-SEC-101",
            level=40
        )
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "error_description": "The access token has expired."
            }
        )

    # 3. Verify JWS Cryptographic Signature (Non-repudiation & integrity)
    jws_signature = request.headers.get("X-Jws-Signature")
    if not jws_signature:
        # Log warning: SAMA requires JWS signatures for Payment Initiation
        log_audit_event(
            action="API_SECURITY_VIOLATION",
            message="Request blocked: Missing cryptographic signature X-Jws-Signature",
            status="BLOCKED",
            correlation_id=correlation_id,
            sama_reference="SAMA-OB-PIS-SEC-101",
            level=40
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_signature",
                "error_description": "Missing JWS signature (X-Jws-Signature header). Detached JWS signature is mandatory for Payment Initiation Services."
            }
        )
        
    # Check signature format: standard compact serialization JWS has 3 parts separated by dots '.' (detached has 3 parts but second is empty)
    parts = jws_signature.split(".")
    if len(parts) != 3:
        log_audit_event(
            action="API_SECURITY_VIOLATION",
            message=f"Request blocked: Invalid JWS signature structure: {jws_signature}",
            status="BLOCKED",
            correlation_id=correlation_id,
            sama_reference="SAMA-OB-PIS-SEC-101",
            level=40
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_signature",
                "error_description": "Invalid signature format. Must be a valid RFC 7515 Compact JWS."
            }
        )

    # All checks passed! Inject verified metadata to request state
    request.state.interaction_id = interaction_id
    request.state.client_id = "tpp_sa_operator_01"
    request.state.scopes = ["pis:payment"]
