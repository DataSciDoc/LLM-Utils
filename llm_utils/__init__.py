# -*- coding: utf-8 -*-
"""
LLM Utilities Library

Battle-tested utilities for working with Large Language Model APIs in production.
Originally developed for production LLM applications starting in 2022.

Modules:
    json_repair: Fix malformed JSON from LLM outputs
    rate_limiting: Token bucket rate limiters for API calls
    prompt_manager: Batch processing, retry logic, result tracking

Author: Richard Kerr
Repository: https://github.com/datasciencedoc/llm-utils
"""

from .json_repair import (
    repair_json,
    repair_json_list,
    safe_json_parse,
    remove_markdown_fences,
    fix_quotes,
    extract_json_object,
    fix_truncated_json,
    fix_common_json_errors,
)

from .rate_limiting import (
    TokenBucket,
    DualRateLimiter,
    ANTHROPIC_RATE_LIMITER,
    OPENAI_RATE_LIMITER,
)

from .prompt_manager import (
    PromptManager,
    PromptResult,
    process_prompts_with_callback,
)

__version__ = "0.1.0"
__author__ = "Richard Kerr"

__all__ = [
    # JSON repair
    "repair_json",
    "repair_json_list", 
    "safe_json_parse",
    "remove_markdown_fences",
    "fix_quotes",
    "extract_json_object",
    "fix_truncated_json",
    "fix_common_json_errors",
    # Rate limiting
    "TokenBucket",
    "DualRateLimiter",
    "ANTHROPIC_RATE_LIMITER",
    "OPENAI_RATE_LIMITER",
    # Prompt management
    "PromptManager",
    "PromptResult",
    "process_prompts_with_callback",
]
