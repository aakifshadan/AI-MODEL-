"""Storage service with file locking for safe JSON operations"""
import json
import os
import fcntl
from contextlib import contextmanager


class StorageService:
    """Thread-safe JSON storage with file locking"""
    
    @staticmethod
    @contextmanager
    def locked_file(filepath, mode='r'):
        """Context manager for locked file operations"""
        # Get directory path
        dirpath = os.path.dirname(filepath)
        
        # Only create directory if there is one
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        
        # Create file if it doesn't exist
        if not os.path.exists(filepath) and 'r' in mode:
            with open(filepath, 'w') as f:
                json.dump({}, f)
        
        with open(filepath, mode) as f:
            # Acquire exclusive lock
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield f
            finally:
                # Release lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    @staticmethod
    def load_json(filepath, default=None):
        """Safely load JSON with file locking"""
        if default is None:
            default = {}
        
        if not os.path.exists(filepath):
            return default
        
        try:
            with StorageService.locked_file(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return default
    
    @staticmethod
    def save_json(filepath, data):
        """Safely save JSON with file locking"""
        with StorageService.locked_file(filepath, 'w') as f:
            json.dump(data, f, indent=2)
