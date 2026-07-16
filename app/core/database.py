import os
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# Database path: project root
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "vector_ai.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Needed for SQLite in FastAPI multi-threading
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBTransaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    correlation_id = Column(String, index=True, nullable=True)
    debtor_iban = Column(String, nullable=False)
    debtor_bank = Column(String, nullable=True)
    debtor_holder = Column(String, nullable=True)
    creditor_iban = Column(String, nullable=False)
    creditor_bank = Column(String, nullable=True)
    creditor_holder = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="SAR")
    narrative = Column(Text, nullable=True)
    status = Column(String, nullable=False)  # approved, requires_verification, blocked, dynamic_otp_verified, dynamic_otp_failed
    risk_level = Column(String, nullable=False)  # low, high, critical
    sama_compliance_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DBSecurityLog(Base):
    __tablename__ = "security_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String, index=True, nullable=True)
    transaction_id = Column(String, index=True, nullable=True)
    action = Column(String, nullable=False)  # PROMPT_VALIDATION, PAYMENT_INITIATION_INTERCEPT, etc.
    message = Column(Text, nullable=False)
    status = Column(String, nullable=False)  # VALIDATED, BLOCKED, COMPLIANT, etc.
    sama_reference = Column(String, index=True, nullable=True)
    latency_ms = Column(Float, nullable=True)
    extra_data = Column(Text, nullable=True)  # Store JSON representation
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DBComplianceSetting(Base):
    __tablename__ = "compliance_settings"
    
    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Initialize default settings if not exists
    db = SessionLocal()
    try:
        limit_setting = db.query(DBComplianceSetting).filter_by(key="sama_auto_approve_limit").first()
        if not limit_setting:
            db.add(DBComplianceSetting(key="sama_auto_approve_limit", value="500.0"))
            
        threshold_setting = db.query(DBComplianceSetting).filter_by(key="semantic_threshold").first()
        if not threshold_setting:
            db.add(DBComplianceSetting(key="semantic_threshold", value="0.40"))
            
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
