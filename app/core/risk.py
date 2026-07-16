from typing import Dict, Any, Tuple
from app.config import settings

def evaluate_transaction_risk(
    amount_sar: float,
    is_anomalous: bool = False,
    auto_approve_limit: float = None
) -> Tuple[Dict[str, Any], str]:
    """
    Evaluates transaction risk based on SAMA sandbox rules.
    Returns (response_payload, risk_rating)
    """
    limit = auto_approve_limit if auto_approve_limit is not None else settings.SAMA_AUTO_APPROVE_LIMIT
    
    # SAMA OB Rule: Transactions above limit or containing behavioral/semantic anomalies
    # must undergo additional cognitive confirmation (e.g. dynamic slider).
    if amount_sar >= limit or is_anomalous:
        return {
            "status": "requires_verification",
            "risk_level": "high",
            "reason": "Transaction exceeds auto-approve threshold or exhibits behavioral/semantic anomaly"
        }, "HIGH"
        
    return {
        "status": "approved",
        "reason": "Below threshold and verified by Vector AI"
    }, "LOW"
