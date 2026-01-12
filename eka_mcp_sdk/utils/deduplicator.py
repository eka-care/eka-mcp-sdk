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
        self.response_cache: Dict[str, Any] = {}  # Cache responses by hash
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
    
    def check_and_get_cached(self, tool_name: str, **params) -> tuple[bool, Any]:
        """
        Check if this request was recently processed and return cached response.
        
        Args:
            tool_name: Name of the MCP tool being invoked
            **params: All parameters passed to the tool
            
        Returns:
            Tuple of (is_duplicate, cached_response)
            - (False, None) if new request
            - (True, response) if duplicate with cached response
            
        Example:
            ```python
            is_dup, cached = dedup.check_and_get_cached("add_patient", fln="John")
            if is_dup:
                return cached  # Return original response
            # Execute normally...
            ```
        """
        request_hash = self._hash_request(tool_name, **params)
        
        if request_hash in self.recent_requests:
            cached_response = self.response_cache.get(request_hash)
            logger.warning(
                f"⚡ DUPLICATE REQUEST DETECTED: {tool_name} "
                f"(hash={request_hash}, returning cached response)"
            )
            return True, cached_response
        
        # New request - add to queue
        self.recent_requests.append(request_hash)
        logger.debug(
            f"✓ New request tracked: {tool_name} "
            f"(hash={request_hash}, queue_size={len(self.recent_requests)}/{self.max_size})"
        )
        return False, None
    
    def cache_response(self, tool_name: str, response: Any, **params) -> None:
        """
        Cache the response for a request.
        
        Args:
            tool_name: Name of the MCP tool
            response: The response to cache
            **params: All tool parameters (same as used in check_and_get_cached)
        """
        request_hash = self._hash_request(tool_name, **params)
        self.response_cache[request_hash] = response
        logger.debug(f"✓ Cached response for {tool_name} (hash={request_hash})")
    
    def is_duplicate(self, tool_name: str, **params) -> bool:
        """
        DEPRECATED: Use check_and_get_cached() instead for better duplicate handling.
        
        This method only checks for duplicates without returning cached responses.
        """
        is_dup, _ = self.check_and_get_cached(tool_name, **params)
        return is_dup
    
    def clear(self) -> None:
        """Clear all tracked requests and cached responses (useful for testing)."""
        self.recent_requests.clear()
        self.response_cache.clear()
        logger.info("RequestDeduplicator cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics about the deduplicator."""
        return {
            "queue_size": len(self.recent_requests),
            "max_size": self.max_size,
            "cached_responses": len(self.response_cache),
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
