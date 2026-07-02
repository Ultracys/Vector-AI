from fastapi import APIRouter
from app.api.endpoints import guardrails, payments, compliance

api_router = APIRouter()

# Include endpoint modules
api_router.include_router(guardrails.router, tags=["Guardrails"])
api_router.include_router(payments.router, tags=["Payments"])
api_router.include_router(compliance.router, tags=["Compliance"])
