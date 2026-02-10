"""Database service for MySQL operations"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from models.database import User, UserAPIKey, Conversation, Message, UserSession
from cryptography.fernet import Fernet
import hashlib
import base64


class DatabaseService:
    """Service for database operations"""
    
    def __init__(self, session: Session, secret_key: str):
        self.session = session
        self.cipher = self._get_cipher(secret_key)
    
    def _get_cipher(self, secret_key):
        """Get encryption cipher"""
        secret = secret_key if isinstance(secret_key, bytes) else secret_key.encode()
        key = hashlib.sha256(secret).digest()
        return Fernet(base64.urlsafe_b64encode(key))
    
    # ============ USER OPERATIONS ============
    
    def create_user(self, email, name, password_hash=None, auth_type='email', picture_url=None):
        """Create a new user"""
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower().strip(),
            name=name,
            password_hash=password_hash,
            auth_type=auth_type,
            picture_url=picture_url
        )
        self.session.add(user)
        self.session.commit()
        return user
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        return self.session.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email):
        """Get user by email"""
        return self.session.query(User).filter(User.email == email.lower()).first()
    
    def update_user_login(self, user_id):
        """Update last login timestamp"""
        user = self.get_user_by_id(user_id)
        if user:
            user.last_login_at = datetime.now()
            self.session.commit()
    
    def update_user(self, user_id, **kwargs):
        """Update user fields"""
        user = self.get_user_by_id(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            self.session.commit()
        return user
    
    # ============ API KEY OPERATIONS ============
    
    def save_api_key(self, user_id, provider, api_key, key_name=None):
        """Save encrypted API key"""
        encrypted = self.cipher.encrypt(api_key.encode()).decode()
        
        # Check if key exists
        existing = self.session.query(UserAPIKey).filter(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider
        ).first()
        
        if existing:
            existing.encrypted_key = encrypted
            existing.key_name = key_name
            existing.updated_at = datetime.now()
        else:
            key = UserAPIKey(
                user_id=user_id,
                provider=provider,
                encrypted_key=encrypted,
                key_name=key_name
            )
            self.session.add(key)
        
        self.session.commit()
    
    def get_api_key(self, user_id, provider):
        """Get decrypted API key"""
        key = self.session.query(UserAPIKey).filter(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider,
            UserAPIKey.is_active == True
        ).first()
        
        if key:
            try:
                return self.cipher.decrypt(key.encrypted_key.encode()).decode()
            except:
                return None
        return None
    
    def get_api_keys_status(self, user_id):
        """Get status of all API keys"""
        keys = self.session.query(UserAPIKey).filter(
            UserAPIKey.user_id == user_id
        ).all()
        
        status = {}
        for key in keys:
            decrypted = self.get_api_key(user_id, key.provider)
            status[key.provider] = {
                'configured': bool(decrypted),
                'masked': f"{'*' * 20}...{decrypted[-4:]}" if decrypted and len(decrypted) > 4 else ""
            }
        
        return status
    
    def update_api_key_usage(self, user_id, provider):
        """Update last used timestamp"""
        key = self.session.query(UserAPIKey).filter(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider
        ).first()
        
        if key:
            key.last_used_at = datetime.now()
            self.session.commit()
    
    # ============ CONVERSATION OPERATIONS ============
    
    def create_conversation(self, user_id, title, provider, model):
        """Create a new conversation"""
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            provider=provider,
            model=model
        )
        self.session.add(conversation)
        self.session.commit()
        return conversation
    
    def get_conversation(self, conversation_id):
        """Get conversation by ID"""
        return self.session.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
    
    def get_user_conversations(self, user_id, limit=50, include_archived=False):
        """Get user's conversations"""
        query = self.session.query(Conversation).filter(
            Conversation.user_id == user_id
        )
        
        if not include_archived:
            query = query.filter(Conversation.is_archived == False)
        
        return query.order_by(desc(Conversation.updated_at)).limit(limit).all()
    
    def update_conversation(self, conversation_id, **kwargs):
        """Update conversation fields"""
        conversation = self.get_conversation(conversation_id)
        if conversation:
            for key, value in kwargs.items():
                if hasattr(conversation, key):
                    setattr(conversation, key, value)
            self.session.commit()
        return conversation
    
    def delete_conversation(self, conversation_id):
        """Delete a conversation"""
        conversation = self.get_conversation(conversation_id)
        if conversation:
            self.session.delete(conversation)
            self.session.commit()
            return True
        return False
    
    def archive_conversation(self, conversation_id):
        """Archive a conversation"""
        return self.update_conversation(conversation_id, is_archived=True)
    
    def pin_conversation(self, conversation_id, pinned=True):
        """Pin/unpin a conversation"""
        return self.update_conversation(conversation_id, is_pinned=pinned)
    
    # ============ MESSAGE OPERATIONS ============
    
    def create_message(self, conversation_id, role, content, provider=None, model=None,
                      input_tokens=0, output_tokens=0, total_tokens=0, cost=0.0,
                      is_error=False, error_message=None, message_metadata=None):
        """Create a new message"""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            is_error=is_error,
            error_message=error_message,
            message_metadata=message_metadata
        )
        self.session.add(message)
        self.session.commit()
        return message
    
    def get_conversation_messages(self, conversation_id, limit=None):
        """Get messages for a conversation"""
        query = self.session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_message(self, message_id):
        """Get message by ID"""
        return self.session.query(Message).filter(Message.id == message_id).first()
    
    def delete_message(self, message_id):
        """Delete a message"""
        message = self.get_message(message_id)
        if message:
            self.session.delete(message)
            self.session.commit()
            return True
        return False
    
    # ============ USAGE STATISTICS ============
    
    def get_user_usage_stats(self, user_id):
        """Get usage statistics for a user"""
        stats = self.session.query(
            func.count(func.distinct(Conversation.id)).label('total_conversations'),
            func.count(Message.id).label('total_messages'),
            func.sum(Message.input_tokens).label('total_input_tokens'),
            func.sum(Message.output_tokens).label('total_output_tokens'),
            func.sum(Message.total_tokens).label('total_tokens'),
            func.sum(Message.cost).label('total_cost')
        ).join(
            Conversation, Message.conversation_id == Conversation.id
        ).filter(
            Conversation.user_id == user_id,
            Message.role == 'assistant'
        ).first()
        
        return {
            'total_conversations': stats.total_conversations or 0,
            'total_messages': stats.total_messages or 0,
            'total_input_tokens': int(stats.total_input_tokens or 0),
            'total_output_tokens': int(stats.total_output_tokens or 0),
            'total_tokens': int(stats.total_tokens or 0),
            'total_cost': float(stats.total_cost or 0)
        }
    
    def get_provider_usage_stats(self, user_id):
        """Get usage statistics by provider"""
        stats = self.session.query(
            Conversation.provider,
            func.count(func.distinct(Conversation.id)).label('conversations'),
            func.count(Message.id).label('messages'),
            func.sum(Message.input_tokens).label('input_tokens'),
            func.sum(Message.output_tokens).label('output_tokens'),
            func.sum(Message.total_tokens).label('total_tokens'),
            func.sum(Message.cost).label('cost')
        ).join(
            Message, Conversation.id == Message.conversation_id
        ).filter(
            Conversation.user_id == user_id,
            Message.role == 'assistant'
        ).group_by(
            Conversation.provider
        ).all()
        
        result = {}
        for stat in stats:
            result[stat.provider] = {
                'conversations': stat.conversations,
                'messages': stat.messages,
                'input_tokens': int(stat.input_tokens or 0),
                'output_tokens': int(stat.output_tokens or 0),
                'total_tokens': int(stat.total_tokens or 0),
                'cost': float(stat.cost or 0)
            }
        
        return result
    
    def search_conversations(self, user_id, query, limit=20):
        """Search conversations by title or content"""
        conversations = self.session.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.title.like(f'%{query}%')
        ).order_by(desc(Conversation.updated_at)).limit(limit).all()
        
        return conversations
    
    # ============ SESSION OPERATIONS ============
    
    def create_session(self, session_id, user_id, ip_address=None, user_agent=None, expires_at=None):
        """Create a user session"""
        session = UserSession(
            id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at or datetime.now()
        )
        self.session.add(session)
        self.session.commit()
        return session
    
    def get_session(self, session_id):
        """Get session by ID"""
        return self.session.query(UserSession).filter(
            UserSession.id == session_id
        ).first()
    
    def delete_session(self, session_id):
        """Delete a session"""
        session = self.get_session(session_id)
        if session:
            self.session.delete(session)
            self.session.commit()
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Delete expired sessions"""
        self.session.query(UserSession).filter(
            UserSession.expires_at < datetime.now()
        ).delete()
        self.session.commit()
