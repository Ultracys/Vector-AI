import logging
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Inject standard SAMA compliance keys from extra dict if present
        for key in ["correlation_id", "transaction_id", "action", "client_ip", "status", "latency_ms", "sama_reference"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
                
        # Also copy generic extra properties if any
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_data.update(record.extra_data)
            
        return json.dumps(log_data)

def setup_compliance_logger(name: str = "vector_compliance") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger

# Primary audit logger instance
audit_logger = setup_compliance_logger()

# Helper function to generate audit logs cleanly
def log_audit_event(
    action: str,
    message: str,
    status: str,
    transaction_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    latency_ms: Optional[float] = None,
    sama_reference: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    level: int = logging.INFO
):
    extra = {
        "action": action,
        "status": status,
    }
    if transaction_id:
        extra["transaction_id"] = transaction_id
    if correlation_id:
        extra["correlation_id"] = correlation_id
    if client_ip:
        extra["client_ip"] = client_ip
    if latency_ms is not None:
        extra["latency_ms"] = round(latency_ms, 2)
    if sama_reference:
        extra["sama_reference"] = sama_reference
    if extra_data:
        extra["extra_data"] = extra_data
        
    audit_logger.log(level, message, extra=extra)
