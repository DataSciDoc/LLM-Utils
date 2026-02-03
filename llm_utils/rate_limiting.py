# -*- coding: utf-8 -*-
"""
Rate Limiting Utilities for LLM APIs

Token bucket implementation for managing API rate limits.
Handles both request-per-minute and tokens-per-minute limits.

Author: Richard Kerr
Created: 2024
"""

import time
from typing import Optional


class TokenBucket:
    """
    Token bucket rate limiter for API calls.
    
    Implements a token bucket algorithm that refills at a constant rate,
    allowing bursts up to capacity while maintaining average rate limits.
    
    Args:
        tokens_per_minute: Maximum tokens allowed per minute
        capacity: Optional bucket capacity (defaults to tokens_per_minute)
    
    Example:
        >>> bucket = TokenBucket(tokens_per_minute=100000)
        >>> if bucket.consume(1500):  # Request uses ~1500 tokens
        ...     make_api_call()
        ... else:
        ...     wait_and_retry()
    """
    
    def __init__(self, tokens_per_minute: int, capacity: Optional[int] = None):
        self.capacity = capacity or tokens_per_minute
        self.tokens = self.capacity
        self.last_refill = time.time()
        self.refill_rate = tokens_per_minute / 60  # tokens per second
    
    def consume(self, tokens: int) -> bool:
        """
        Attempt to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were available and consumed, False otherwise
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def wait_for_tokens(self, tokens: int, max_wait: float = 60.0) -> bool:
        """
        Wait until tokens are available, then consume them.
        
        Args:
            tokens: Number of tokens needed
            max_wait: Maximum seconds to wait (default: 60)
            
        Returns:
            True if tokens were obtained, False if max_wait exceeded
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self.consume(tokens):
                return True
            # Calculate wait time for needed tokens
            self._refill()
            tokens_needed = tokens - self.tokens
            wait_time = min(tokens_needed / self.refill_rate, max_wait)
            time.sleep(min(wait_time, 1.0))  # Check at least every second
        
        return False
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        time_passed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
        self.last_refill = now
    
    @property
    def available_tokens(self) -> float:
        """Get current available tokens (after refill)."""
        self._refill()
        return self.tokens
    
    def time_until_tokens(self, tokens: int) -> float:
        """
        Calculate seconds until specified tokens will be available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Seconds until tokens available (0 if already available)
        """
        self._refill()
        if self.tokens >= tokens:
            return 0.0
        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class DualRateLimiter:
    """
    Combined rate limiter for APIs with both request and token limits.
    
    Many LLM APIs have dual limits:
    - Requests per minute (e.g., 60 RPM)
    - Tokens per minute (e.g., 100,000 TPM)
    
    This class manages both simultaneously.
    
    Args:
        requests_per_minute: Maximum API calls per minute
        tokens_per_minute: Maximum tokens per minute
    
    Example:
        >>> limiter = DualRateLimiter(
        ...     requests_per_minute=60,
        ...     tokens_per_minute=100000
        ... )
        >>> if limiter.acquire(estimated_tokens=2000):
        ...     response = make_api_call()
        ...     limiter.record_actual_tokens(actual_tokens)
    """
    
    def __init__(self, requests_per_minute: int, tokens_per_minute: int):
        self.request_bucket = TokenBucket(requests_per_minute)
        self.token_bucket = TokenBucket(tokens_per_minute)
    
    def acquire(self, estimated_tokens: int) -> bool:
        """
        Attempt to acquire both a request slot and tokens.
        
        Args:
            estimated_tokens: Estimated tokens for the request
            
        Returns:
            True if both limits allow the request
        """
        # Check both limits
        if self.request_bucket.consume(1) and self.token_bucket.consume(estimated_tokens):
            return True
        return False
    
    def wait_and_acquire(self, estimated_tokens: int, max_wait: float = 60.0) -> bool:
        """
        Wait for availability, then acquire.
        
        Args:
            estimated_tokens: Estimated tokens for the request
            max_wait: Maximum seconds to wait
            
        Returns:
            True if acquired within max_wait
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self.acquire(estimated_tokens):
                return True
            time.sleep(0.5)
        
        return False
    
    def get_wait_time(self, estimated_tokens: int) -> float:
        """Get estimated wait time for next request."""
        request_wait = self.request_bucket.time_until_tokens(1)
        token_wait = self.token_bucket.time_until_tokens(estimated_tokens)
        return max(request_wait, token_wait)


# Default instances for common API configurations
ANTHROPIC_RATE_LIMITER = DualRateLimiter(
    requests_per_minute=60,
    tokens_per_minute=100000
)

OPENAI_RATE_LIMITER = DualRateLimiter(
    requests_per_minute=60,
    tokens_per_minute=90000
)
