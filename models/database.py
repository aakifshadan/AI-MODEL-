"""Database models using SQLAlchemy"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, BigInteger, Text, 
    Boolean, TIMESTAMP, Enum, DECIMAL, ForeignKey, Index, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255))
    auth_type = Column(Enum('email', 'google', 'github'), nullable=False, default='email')
    picture_url = Column(Text)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    last_login_at = Column(TIMESTAMP)
    
    # Relationships
    api_keys = relationship('UserAPIKey', back_populates='user', cascade='all, delete-orphan')
    conversations = relationship('Conversation', back_populates='user', cascade='all, delete-orphan')
    sessions = relationship('UserSession', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}')>"


class UserAPIKey(Base):
    """User API Keys (encrypted)"""
    __tablename__ = 'user_api_keys'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    provider = Column(Enum('openai', 'anthropic', 'google'), nullable=False)
    encrypted_key = Column(Text, nullable=False)
    key_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    last_used_at = Column(TIMESTAMP)
    
    # Relationships
    user = relationship('User', back_populates='api_keys')
    
    __table_args__ = (
        Index('idx_user_provider', 'user_id', 'provider'),
    )
    
    def __repr__(self):
        return f"<UserAPIKey(user_id='{self.user_id}', provider='{self.provider}')>"


class Conversation(Base):
    """Conversation model"""
    __tablename__ = 'conversations'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(500), nullable=False)
    provider = Column(Enum('openai', 'anthropic', 'google'), nullable=False)
    model = Column(String(100), nullable=False)
    is_archived = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    total_messages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(DECIMAL(10, 6), default=0.000000)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    user = relationship('User', back_populates='conversations')
    messages = relationship('Message', back_populates='conversation', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_user_updated', 'user_id', 'updated_at'),
    )
    
    def __repr__(self):
        return f"<Conversation(id='{self.id}', title='{self.title[:30]}...')>"


class Message(Base):
    """Message model"""
    __tablename__ = 'messages'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    role = Column(Enum('user', 'assistant', 'system'), nullable=False)
    content = Column(Text, nullable=False)
    provider = Column(String(50))
    model = Column(String(100))
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(DECIMAL(10, 6), default=0.000000)
    is_error = Column(Boolean, default=False)
    error_message = Column(Text)
    message_metadata = Column('metadata', JSON)  # Renamed to avoid conflict
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    conversation = relationship('Conversation', back_populates='messages')
    attachments = relationship('MessageAttachment', back_populates='message', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_conversation_created', 'conversation_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', conversation_id='{self.conversation_id}')>"


class MessageAttachment(Base):
    """Message attachments (for future: images, files)"""
    __tablename__ = 'message_attachments'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, ForeignKey('messages.id', ondelete='CASCADE'), nullable=False)
    file_type = Column(Enum('image', 'document', 'code', 'other'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    message = relationship('Message', back_populates='attachments')
    
    def __repr__(self):
        return f"<MessageAttachment(id={self.id}, file_name='{self.file_name}')>"


class UserSession(Base):
    """User sessions"""
    __tablename__ = 'user_sessions'
    
    id = Column(String(64), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    expires_at = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    user = relationship('User', back_populates='sessions')
    
    __table_args__ = (
        Index('idx_expires_at', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<UserSession(id='{self.id}', user_id='{self.user_id}')>"


# Database connection helper
def get_engine(database_url):
    """Create database engine"""
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False  # Set to True for SQL debugging
    )


def get_session_maker(engine):
    """Create session maker"""
    return sessionmaker(bind=engine)


def init_db(engine):
    """Initialize database (create all tables)"""
    Base.metadata.create_all(engine)


def drop_all(engine):
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(engine)
