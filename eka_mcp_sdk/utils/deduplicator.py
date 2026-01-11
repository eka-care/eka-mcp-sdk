"""Request deduplicator to prevent duplicate tool calls from ChatGPT's multiple MCP clients."""

from collections import deque
from typing import Any, Dict
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class RequestDeduplicator:
    """
    Circular queue-based deduplicator to prevent duplicate write operations.
    
    ChatGPT often initializes multiple MCP clients simultaneously, causing the same
    tool to be invoked multiple times within seconds. This class maintains a rolling
    window of recently processed requests and blocks duplicates.
    
    How it works:
    1. Hash the entire request (tool name + all parameters)
    2. Check if hash exists in recent requests queue
    3. If yes -> duplicate detected, skip execution
    4. If no -> add to queue and execute normally
    
    The queue auto-evicts oldest entries when full (FIFO), making it memory-efficient.
    """
    
    def __init__(self, max_size: int = 20):
        """
        Initialize the deduplicator with a circular queue.
        
        Args:
            max_size: Maximum number of recent requests to track (default: 20)
                     Covers ~5-10 seconds of typical ChatGPT duplicate windows
        """
        self.recent_requests: deque = deque(maxlen=max_size)
        self.max_size = max_size
        logger.info(f"RequestDeduplicator initialized (queue_size={max_size})")
    
    def _hash_request(self, tool_name: str, **params) -> str:
        """
        Create a unique hash from tool name and all parameters.
        
        Uses SHA256 for collision resistance and takes first 16 characters
        for efficiency. This provides ~10^18 unique combinations, sufficient
        for duplicate detection within our time window.
        
        Args:
            tool_name: Name of the MCP tool being invoked
            **params: All parameters passed to the tool
            
        Returns:
            16-character hash string
        """
        # Clean params: remove None values and sort for consistency
        cleaned_params = {k: v for k, v in params.items() if v is not None}
        
        request_data = {
            "tool": tool_name,
            "params": cleaned_params
        }
        
        # Sort keys for deterministic hashing
        request_str = json.dumps(request_data, sort_keys=True, default=str)
        
        # Generate short hash (16 chars = 64 bits of entropy)
        full_hash = hashlib.sha256(request_str.encode()).hexdigest()
        return full_hash[:16]
    
    def is_duplicate(self, tool_name: str, **params) -> bool:
        """
        Check if this request was recently processed.
        
        If duplicate: Returns True and logs warning
        If new: Adds to queue and returns False
        
        Args:
            tool_name: Name of the MCP tool being invoked
            **params: All parameters passed to the tool
            
        Returns:
            True if duplicate detected, False if new request
            
        Example:
            ```python
            if dedup.is_duplicate("add_patient", fln="John", mobile="+91..."):
                return {"error": "Duplicate request"}
            # Execute normally...
            ```
        """
        request_hash = self._hash_request(tool_name, **params)
        
        if request_hash in self.recent_requests:
            logger.warning(
                f"⚡ DUPLICATE REQUEST DETECTED: {tool_name} "
                f"(hash={request_hash}, queue_size={len(self.recent_requests)})"
            )
            return True
        
        # New request - add to queue
        self.recent_requests.append(request_hash)
        logger.debug(
            f"✓ New request tracked: {tool_name} "
            f"(hash={request_hash}, queue_size={len(self.recent_requests)}/{self.max_size})"
        )
        return False
    
    def clear(self) -> None:
        """Clear all tracked requests (useful for testing)."""
        self.recent_requests.clear()
        logger.info("RequestDeduplicator cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics about the deduplicator."""
        return {
            "queue_size": len(self.recent_requests),
            "max_size": self.max_size,
            "utilization": f"{len(self.recent_requests) / self.max_size * 100:.1f}%"
        }


# Global singleton instance (one per server process)
_deduplicator = RequestDeduplicator(max_size=20)


def check_duplicate(tool_name: str, **params) -> bool:
    """
    Convenience function to check for duplicates using the global deduplicator.
    
    Args:
        tool_name: Name of the MCP tool
        **params: All tool parameters
        
    Returns:
        True if duplicate, False if new
    """
    return _deduplicator.is_duplicate(tool_name, **params)


def get_deduplicator() -> RequestDeduplicator:
    """Get the global deduplicator instance (useful for testing/stats)."""
    return _deduplicator
