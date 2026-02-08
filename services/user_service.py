"""User management service"""
import os
import json
import hashlib
import base64
from cryptography.fernet import Fernet
from .storage_service import StorageService


class UserService:
    def __init__(self, secret_key, users_file='users.json', user_data_dir='user_data'):
        self.users_file = users_file
        self.user_data_dir = user_data_dir
        self.cipher = self._get_cipher(secret_key)
        
        # Ensure user data directory exists
        os.makedirs(user_data_dir, exist_ok=True)
    
    def _get_cipher(self, secret_key):
        """Get encryption cipher"""
        secret = secret_key if isinstance(secret_key, bytes) else secret_key.encode()
        key = hashlib.sha256(secret).digest()
        return Fernet(base64.urlsafe_b64encode(key))
    
    def load_users(self):
        """Load all users"""
        return StorageService.load_json(self.users_file, {})
    
    def save_users(self, users):
        """Save all users"""
        StorageService.save_json(self.users_file, users)
    
    def get_user_data_path(self, user_id):
        """Get path to user data file"""
        return os.path.join(self.user_data_dir, f'{user_id}.json')
    
    def load_user_data(self, user_id):
        """Load user-specific data"""
        path = self.get_user_data_path(user_id)
        return StorageService.load_json(path, {'api_keys': {}, 'conversations': {}})
    
    def save_user_data(self, user_id, data):
        """Save user-specific data"""
        path = self.get_user_data_path(user_id)
        StorageService.save_json(path, data)
    
    def get_api_key(self, user_id, provider, fallback_keys=None):
        """Get API key for provider"""
        user_data = self.load_user_data(user_id)
        encrypted_keys = user_data.get('api_keys', {})
        
        if encrypted_keys.get(provider):
            try:
                return self.cipher.decrypt(encrypted_keys[provider].encode()).decode()
            except:
                pass
        
        # Fall back to environment variables
        if fallback_keys:
            env_map = {
                'openai': fallback_keys.get('OPENAI_API_KEY', ''),
                'anthropic': fallback_keys.get('ANTHROPIC_API_KEY', ''),
                'google': fallback_keys.get('GEMINI_API_KEY', '')
            }
            return env_map.get(provider, '')
        
        return ''
    
    def save_api_keys(self, user_id, keys):
        """Save encrypted API keys"""
        user_data = self.load_user_data(user_id)
        
        # Decrypt existing keys
        existing_keys = user_data.get('api_keys', {})
        decrypted_existing = {}
        for provider, encrypted in existing_keys.items():
            if encrypted:
                try:
                    decrypted_existing[provider] = self.cipher.decrypt(encrypted.encode()).decode()
                except:
                    decrypted_existing[provider] = ''
        
        # Merge with new keys
        for provider, key in keys.items():
            if key:
                decrypted_existing[provider] = key
        
        # Encrypt and save
        user_data['api_keys'] = {
            provider: self.cipher.encrypt(key.encode()).decode() if key else ''
            for provider, key in decrypted_existing.items()
        }
        
        self.save_user_data(user_id, user_data)
