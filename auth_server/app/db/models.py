from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Group(Base):
    """用戶群組 - 用於分組管理白名單"""
    __tablename__ = "groups"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="group")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # 🆕 管理員標記
    
    # Status flow: pending_api -> pending_approval -> active / rejected
    status = Column(String, default="pending_api")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Exchange Info
    exchange = Column(String, default="bitget")
    exchange_uid = Column(String, nullable=True, unique=True, index=True)
    
    # API verification tracking
    api_verified_at = Column(DateTime, nullable=True)
    
    # Admin approval tracking
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String, nullable=True)
    
    # Group membership
    group_id = Column(String, ForeignKey("groups.id"), nullable=True)
    group = relationship("Group", back_populates="users")
    
    # Legacy fields
    verified_invite_code = Column(String, nullable=True)
    zeabur_url = Column(String, nullable=True)

    # Relationships
    credentials = relationship("APICredential", back_populates="user", uselist=False)
    executions = relationship("GridExecution", back_populates="user")
    agreements = relationship("UserAgreement", back_populates="user")

class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    exchange = Column(String, default="bitget")
    exchange_uid = Column(String)  # The UID this code is valid for (optional or specific)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)
    used_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)

class APICredential(Base):
    __tablename__ = "api_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    
    # Encrypted fields
    api_key_encrypted = Column(String)
    api_secret_encrypted = Column(String)
    passphrase_encrypted = Column(String, nullable=True)
    
    exchange = Column(String, default="bitget")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="credentials")

class GridExecution(Base):
    __tablename__ = "grid_executions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    trading_pair = Column(String)
    status = Column(String)  # running, stopped, error
    config = Column(Text, nullable=True) # JSON string of parameters
    
    # Performance
    pnl = Column(Float, default=0.0)
    buy_orders = Column(Integer, default=0)
    sell_orders = Column(Integer, default=0)
    
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    logs = Column(Text, nullable=True)

    user = relationship("User", back_populates="executions")

class UserAgreement(Base):
    __tablename__ = "user_agreements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    agreement_version = Column(String)
    agreed_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)

    user = relationship("User", back_populates="agreements")


class NodeStatus(Base):
    """用戶 Grid Node 狀態追蹤"""
    __tablename__ = "node_status"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    
    # 連接狀態
    is_online = Column(Boolean, default=False)
    is_trading = Column(Boolean, default=False)
    last_heartbeat = Column(DateTime, nullable=True)
    
    # 交易數據
    total_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)
    available_balance = Column(Float, default=0.0)
    
    # 分離的 USDT/USDC 餘額
    usdt_equity = Column(Float, default=0.0)
    usdt_available = Column(Float, default=0.0)
    usdc_equity = Column(Float, default=0.0)
    usdc_available = Column(Float, default=0.0)
    
    # 持倉資訊 (JSON)
    positions = Column(Text, nullable=True)
    symbols = Column(Text, nullable=True)
    
    # Node 資訊
    node_version = Column(String, nullable=True)
    node_url = Column(String, nullable=True)
    
    # 時間戳
    registered_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="node_status")

