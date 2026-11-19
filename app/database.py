from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, deferred
from datetime import datetime
from .config import DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
else:
    _connect_args = {"prepare_threshold": None}  # needed for Supabase's connection pooler
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
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
    is_active = Column(Boolean, default=True)
    full_name = Column(String, nullable=True)
    username = Column(String, unique=True, index=True, nullable=True)
    is_muted = Column(Boolean, default=False)
    # deferred: the picture is only read from the database when asked for (avatar route), not on every member lookup
    avatar = deferred(Column(Text, nullable=True))   # base64 JPEG, resized in the browser
    avatar_v = Column(Integer, default=0)          # bumps on every change so browsers refresh the picture

class DirectMessage(Base):
    __tablename__ = "direct_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, index=True)
    recipient_id = Column(Integer, index=True)
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    read_at = Column(DateTime, nullable=True)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)    # empty for admin messages
    username = Column(String)
    is_admin = Column(Boolean, default=False)
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

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
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        User.__table__.create(bind=engine)
        return
    # Older databases were created before these columns existed
    have = [c["name"] for c in inspector.get_columns("users")]
    wanted = {
        "is_active": "BOOLEAN DEFAULT TRUE",
        "full_name": "VARCHAR",
        "username": "VARCHAR",
        "is_muted": "BOOLEAN DEFAULT FALSE",
        "avatar": "TEXT",
        "avatar_v": "INTEGER DEFAULT 0",
    }
    with engine.begin() as conn:
        for column, ddl in wanted.items():
            if column not in have:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {column} {ddl}"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
