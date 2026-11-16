from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    trade_number = Column(Integer, index=True)
    asset = Column(String)
    action = Column(String)
    expiry_mins = Column(Integer)
    price = Column(Float)
    confidence = Column(String)
    status = Column(String, default="pending")
    result = Column(String, nullable=True)
    is_martingale = Column(Boolean, default=False)
    martingale_level = Column(Integer, default=0)  # 0 = normal, 1 or 2
    market_type = Column(String, default="patience")  # "patience" or "3min"
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    details = Column(JSON, nullable=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)

class Stats(Base):
    __tablename__ = "stats"
    id = Column(Integer, primary_key=True)
    week = Column(String, unique=True)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    martingale_wins = Column(Integer, default=0)
    martingale_losses = Column(Integer, default=0)
    total = Column(Integer, default=0)
    trade_number = Column(Integer, default=1)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Force create users table if missing
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        User.__table__.create(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
