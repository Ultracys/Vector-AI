from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class PromptValidationRequest(BaseModel):
    prompt: str = Field(..., description="The user or AI agent text prompt to validate.", min_length=1)
    user_id: Optional[str] = Field(None, description="Identifier of the executing user.")
    agent_id: Optional[str] = Field(None, description="Identifier of the initiating AI agent (e.g., Agent-Alpha).")
    correlation_id: Optional[str] = Field(None, description="Optional correlation ID for distributed tracing.")
    active_layers: Optional[List[str]] = Field(None, description="Security layers to activate: regex, decoder, arabic, vector, llm. Defaults to all.")
    susceptibility: Optional[float] = Field(0.0, description="Agent susceptibility level 0.0 (hardened) to 1.0 (fully vulnerable).", ge=0.0, le=1.0)

class PromptValidationResponse(BaseModel):
    status: str = Field(..., description="Validation outcome: 'validated' or 'blocked'.")
    risk_score: float = Field(..., description="Determined semantic risk score [0.0 - 1.0].")
    threat_type: Optional[str] = Field(None, description="Type of threat identified, if any.")
    reason: Optional[str] = Field(None, description="Text explanation of the decision.")
    risk_matrix: Optional[Dict[str, float]] = Field(None, description="Individual risk scores per threat category.")
    llm_report: Optional[Dict[str, Any]] = Field(None, description="Simulated LLM Guardian analysis report.")
    decoded_prompt: Optional[str] = Field(None, description="Decoded content if obfuscation was detected.")
    layer_results: Optional[Dict[str, Any]] = Field(None, description="Per-layer evaluation breakdown.")
