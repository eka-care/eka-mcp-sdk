import json
import os
from typing import Optional, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FileTokenStorage:
    """File-based token storage implementation."""
    
    def __init__(self):
        from ..config.settings import settings
        
        if settings.token_storage_dir:
            self.storage_dir = Path(settings.token_storage_dir)
        else:
            # Default to user's home directory/.eka_mcp
            self.storage_dir = Path.home() / ".eka_mcp"
        
        self.token_file = self.storage_dir / "tokens.json"
        
        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Set secure file permissions (user read/write only)
        if self.storage_dir.exists():
            os.chmod(self.storage_dir, 0o700)
    
    async def store_tokens(self, access_token: str, refresh_token: str, 
                          expires_in: int = 1800) -> None:
        """Store tokens to file."""
        try:
            token_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            # Set secure file permissions
            os.chmod(self.token_file, 0o600)
            
            logger.debug(f"Tokens stored to {self.token_file}")
            
        except Exception as e:
            logger.error(f"Failed to store tokens: {str(e)}")
            raise
    
    async def get_tokens(self) -> Optional[Dict[str, str]]:
        """Get tokens from file."""
        try:
            if not self.token_file.exists():
                logger.debug("No token file found")
                return None
            
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            # Validate required fields
            if not all(key in token_data for key in ['access_token', 'refresh_token']):
                logger.warning("Invalid token file format")
                return None
            
            logger.debug("Tokens loaded from file")
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to load tokens: {str(e)}")
            return None
    
    async def clear_tokens(self) -> None:
        """Clear stored tokens."""
        try:
            if self.token_file.exists():
                self.token_file.unlink()
                logger.debug("Tokens cleared")
        except Exception as e:
            logger.error(f"Failed to clear tokens: {str(e)}")