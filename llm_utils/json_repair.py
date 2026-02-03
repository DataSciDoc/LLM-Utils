# -*- coding: utf-8 -*-
"""
JSON Repair Utilities for LLM Outputs

Battle-tested functions for fixing malformed JSON returned by language models.
Originally developed for production LLM applications starting in 2022.

Common issues handled:
- Markdown code fences (```json ... ```)
- Single quotes instead of double quotes
- Missing/extra braces
- Escape sequence problems
- Truncated output
- Preamble/postamble text around JSON

Author: Richard Kerr
Created: 2022 (Original production code)
Refactored: 2024
"""

import json
import re
from typing import Any, Dict, List, Optional, Union


def remove_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.replace("```json", "")
    text = text.replace("```JSON", "")
    text = text.replace("```", "")
    return text.strip()


def fix_quotes(text: str) -> str:
    """Convert single quotes to double quotes for JSON compliance."""
    # Simple replacement - works for most cases
    # More sophisticated handling below for edge cases
    return text.replace("'", '"')


def remove_escape_sequences(text: str) -> str:
    """Clean up escape sequence issues from LLM output."""
    try:
        return text.encode('utf-8').decode('unicode_escape')
    except (UnicodeDecodeError, UnicodeEncodeError):
        # If decode fails, return original
        return text


def extract_json_object(text: str) -> str:
    """
    Extract JSON object from text that may contain preamble/postamble.
    Finds the first complete {...} or [...] structure.
    """
    text = text.strip()
    
    # Find first opening brace/bracket
    obj_start = text.find('{')
    arr_start = text.find('[')
    
    if obj_start == -1 and arr_start == -1:
        return text  # No JSON structure found
    
    # Determine if we're looking for object or array
    if arr_start == -1 or (obj_start != -1 and obj_start < arr_start):
        start_char, end_char = '{', '}'
        start_idx = obj_start
    else:
        start_char, end_char = '[', ']'
        start_idx = arr_start
    
    # Find matching closing brace/bracket
    depth = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text[start_idx:], start=start_idx):
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == start_char:
            depth += 1
        elif char == end_char:
            depth -= 1
            if depth == 0:
                return text[start_idx:i+1]
    
    # If we get here, JSON is truncated - return from start to end
    return text[start_idx:]


def fix_truncated_json(text: str) -> str:
    """
    Attempt to fix truncated JSON by closing open structures.
    Handles cases where LLM output was cut off mid-response.
    """
    text = text.strip()
    
    # Count unmatched braces/brackets
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    
    # Check if we're inside an unclosed string
    in_string = False
    for i, char in enumerate(text):
        if char == '\\' and i + 1 < len(text):
            continue
        if char == '"':
            in_string = not in_string
    
    # Close unclosed string
    if in_string:
        text = text + '"'
    
    # Close open brackets first, then braces
    text = text + (']' * max(0, open_brackets))
    text = text + ('}' * max(0, open_braces))
    
    return text


def fix_common_json_errors(text: str) -> str:
    """
    Fix common JSON formatting errors from LLM output.
    
    Handles:
    - Trailing commas before closing braces/brackets
    - Missing commas between elements
    - Unquoted keys (in simple cases)
    """
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    # Fix unquoted keys (simple alphanumeric keys only)
    # Pattern: { key: or , key: where key is not quoted
    text = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', text)
    
    return text


def repair_json(
    text: str,
    target_key: Optional[str] = None,
    strict: bool = False
) -> Union[Dict, List, Any]:
    """
    Main JSON repair function. Attempts multiple strategies to parse JSON from LLM output.
    
    Args:
        text: Raw text from LLM that should contain JSON
        target_key: If specified, extract JSON starting from this key
        strict: If False (default), use json.loads with strict=False
    
    Returns:
        Parsed JSON as dict/list, or raises ValueError if all repair attempts fail
    
    Example:
        >>> text = "Here's the data: ```json {'name': 'test', 'value': 42} ```"
        >>> result = repair_json(text)
        >>> print(result)
        {'name': 'test', 'value': 42}
    """
    
    # If already a dict/list, return as-is
    if isinstance(text, (dict, list)):
        return text
    
    original_text = text
    errors = []
    
    # Strategy 1: Try direct parse first (maybe it's valid!)
    try:
        return json.loads(text, strict=not strict)
    except json.JSONDecodeError as e:
        errors.append(f"Direct parse: {e}")
    
    # Strategy 2: Remove markdown fences and try again
    text = remove_markdown_fences(text)
    try:
        return json.loads(text, strict=not strict)
    except json.JSONDecodeError as e:
        errors.append(f"After fence removal: {e}")
    
    # Strategy 3: Extract JSON object/array from surrounding text
    text = extract_json_object(text)
    try:
        return json.loads(text, strict=not strict)
    except json.JSONDecodeError as e:
        errors.append(f"After extraction: {e}")
    
    # Strategy 4: Fix quotes
    text = fix_quotes(text)
    try:
        return json.loads(text, strict=not strict)
    except json.JSONDecodeError as e:
        errors.append(f"After quote fix: {e}")
    
    # Strategy 5: Fix common errors (trailing commas, unquoted keys)
    text = fix_common_json_errors(text)
    try:
        return json.loads(text, strict=not strict)
    except json.JSONDecodeError as e:
        errors.append(f"After common fixes: {e}")
    
    # Strategy 6: Fix escape sequences
    text = remove_escape_sequences(text)
    try:
        return json.loads(text, strict=not strict)
    except json.JSONDecodeError as e:
        errors.append(f"After escape fix: {e}")
    
    # Strategy 7: Fix truncated JSON
    text = fix_truncated_json(text)
    try:
        return json.loads(text, strict=not strict)
    except json.JSONDecodeError as e:
        errors.append(f"After truncation fix: {e}")
    
    # Strategy 8: If target_key specified, try to extract from that point
    if target_key:
        try:
            key_pattern = f'"{target_key}":'
            if key_pattern in original_text:
                text = original_text.split(key_pattern)[1]
                # Find the value and wrap it
                text = key_pattern + text
                text = '{' + text.split('}')[0] + '}'
                text = fix_quotes(text)
                text = remove_escape_sequences(text)
                return json.loads(text, strict=not strict)
        except (json.JSONDecodeError, IndexError) as e:
            errors.append(f"Target key extraction: {e}")
    
    # All strategies failed
    raise ValueError(
        f"Could not repair JSON after all strategies.\n"
        f"Errors: {errors}\n"
        f"Original text: {original_text[:500]}..."
    )


def repair_json_list(
    texts: List[str],
    target_key: Optional[str] = None,
    on_error: str = 'skip'
) -> List[Union[Dict, List, None]]:
    """
    Repair a list of JSON strings from LLM outputs.
    
    Args:
        texts: List of raw text strings containing JSON
        target_key: If specified, extract JSON starting from this key
        on_error: How to handle errors - 'skip' (return None), 'raise', or 'empty' (return {})
    
    Returns:
        List of parsed JSON objects (with None or {} for failures depending on on_error)
    """
    results = []
    
    for text in texts:
        try:
            result = repair_json(text, target_key=target_key)
            results.append(result)
        except ValueError as e:
            if on_error == 'raise':
                raise
            elif on_error == 'empty':
                results.append({})
            else:  # 'skip'
                results.append(None)
    
    return results


# Convenience function for the most common use case
def safe_json_parse(text: str, default: Any = None) -> Any:
    """
    Safely parse JSON from LLM output, returning default on failure.
    
    Args:
        text: Raw text from LLM
        default: Value to return if parsing fails (default: None)
    
    Returns:
        Parsed JSON or default value
    """
    try:
        return repair_json(text)
    except ValueError:
        return default


# =============================================================================
# Testing / Examples
# =============================================================================

if __name__ == "__main__":
    # Test cases based on real LLM output failures
    
    test_cases = [
        # Markdown fences
        '```json\n{"name": "test", "value": 42}\n```',
        
        # Single quotes
        "{'name': 'test', 'value': 42}",
        
        # Preamble text
        'Here is the JSON you requested:\n{"name": "test"}',
        
        # Truncated
        '{"name": "test", "items": [1, 2, 3',
        
        # Trailing comma
        '{"name": "test", "value": 42,}',
        
        # Unquoted keys
        '{name: "test", value: 42}',
        
        # Mixed issues
        "Sure! Here's the data:\n```json\n{'name': 'test',}\n```\nLet me know if you need anything else!",
    ]
    
    print("JSON Repair Test Results")
    print("=" * 50)
    
    for i, test in enumerate(test_cases):
        print(f"\nTest {i+1}:")
        print(f"Input: {test[:60]}...")
        try:
            result = repair_json(test)
            print(f"Output: {result}")
            print("Status: ✓ SUCCESS")
        except ValueError as e:
            print(f"Status: ✗ FAILED - {e}")
