from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any

class AccountDetails(BaseModel):
    iban: str = Field(..., description="SAMA Compliant IBAN starting with SA followed by 22 alphanumeric characters.", pattern=r"^SA\d{2}[A-Z0-9]{20}$")
    bank_code: str = Field(..., description="SAMA bank identifier code (BIC).")
    account_holder: str = Field(..., description="Name of the account holder.")

class PaymentInitiationRequest(BaseModel):
    debtor_account: AccountDetails = Field(..., description="The funding account details.")
    creditor_account: AccountDetails = Field(..., description="The receiving account details.")
    amount: float = Field(..., description="Transaction amount (minimum 0.01).", gt=0)
    currency: str = Field("SAR", description="SAMA mandated currency. Must be SAR.", pattern=r"^SAR$")
    narrative: str = Field(..., description="Description or prompt instructing the transfer. Will be semantic-scanned.", min_length=3)
    agent_id: Optional[str] = Field(None, description="The AI agent ID if initiated autonomously.")
    correlation_id: Optional[str] = Field(None, description="Correlation identifier for central bank audits.")

class PaymentInitiationResponse(BaseModel):
    transaction_id: str = Field(..., description="Unique generated transaction identifier.")
    status: str = Field(..., description="State of transaction: 'approved', 'requires_verification', or 'blocked'.")
    risk_level: str = Field(..., description="Assessed threat level: 'low' or 'high'.")
    sama_compliance_code: str = Field(..., description="SAMA regulatory audit code mapped to this check.")
    reason: str = Field(..., description="System narrative of authorization decision.")
