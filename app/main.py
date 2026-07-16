import time
import uuid
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from app.config import settings
from app.api.router import api_router
from app.core.logging import log_audit_event, audit_logger
from app.core.database import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
def on_startup():
    init_db()

# CORS Configuration for front-end integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Latency tracking and request trace middleware
@app.middleware("http")
async def audit_trace_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    
    # Process request
    response = await call_next(request)
    
    # Calculate latency
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time-Ms"] = f"{latency_ms:.2f}"
    
    # Log any slow request exceeding 50ms as a performance warning (SAMA Guideline Alert)
    if latency_ms > 50.0:
        log_audit_event(
            action="LATENCY_ALERT",
            message=f"Performance Warning: Request to {request.url.path} took {latency_ms:.2f}ms (Limit: 50ms)",
            status="WARNING",
            correlation_id=correlation_id,
            client_ip=request.client.host if request.client else "unknown",
            latency_ms=latency_ms,
            sama_reference="SAMA-OB-SYS-PERF-501",
            level=30 # WARNING
        )
        
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"
    
    # Log unhandled exceptions in structured format
    log_audit_event(
        action="UNHANDLED_EXCEPTION",
        message=f"System error occurred processing {request.url.path}: {str(exc)}",
        status="SYSTEM_ERROR",
        correlation_id=correlation_id,
        client_ip=client_ip,
        sama_reference="SAMA-OB-SYS-FAIL-999",
        extra_data={"exception_type": type(exc).__name__},
        level=50 # CRITICAL
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "system_error",
            "reason": "An internal compliance engine error occurred. Audited transaction rolled back."
        }
    )

# Include central router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", response_class=HTMLResponse, tags=["Root"])
async def root():
    # Serve the static premium frontend dashboard HTML file
    static_file_path = os.path.join(os.path.dirname(__file__), "static", "frontend.html")
    if os.path.exists(static_file_path):
        with open(static_file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Vector AI Frontend Not Found</h1>", status_code=404)

@app.get("/slides", response_class=HTMLResponse, tags=["Root"])
async def slides():
    # Serve the static premium slide deck presentation_slides.html file
    slide_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presentation_slides.html")
    if os.path.exists(slide_file_path):
        with open(slide_file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Vector AI Presentation Slides Not Found</h1>", status_code=404)

@app.get("/slides/practice", response_class=HTMLResponse, tags=["Root"])
async def practice_slides():
    # Serve the static premium slide deck practice_slides.html file
    slide_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "practice_slides.html")
    if os.path.exists(slide_file_path):
        with open(slide_file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Vector AI Practice Slides Not Found</h1>", status_code=404)


