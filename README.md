# llm-utils

Battle-tested utilities for working with Large Language Model APIs in production.

**Born from necessity:** We pushed our first LLM app to production in 2022. The models were impressive. The JSON they returned was not. These utilities are what we built to make LLMs actually work in production.

## Installation

```bash
pip install llm-utils
```

Or install from source:

```bash
git clone https://github.com/datasciencedoc/llm-utils.git
cd llm-utils
pip install -e .
```

## Quick Start

### JSON Repair

LLMs are notoriously bad at producing valid JSON. They add markdown fences, use single quotes, truncate output, and wrap JSON in conversational text. `repair_json` handles all of it:

```python
from llm_utils import repair_json

# Markdown fences
text = '```json\n{"name": "test"}\n```'
result = repair_json(text)  # {'name': 'test'}

# Single quotes (common in older models)
text = "{'name': 'test', 'value': 42}"
result = repair_json(text)  # {'name': 'test', 'value': 42}

# Preamble/postamble text
text = "Here's the JSON you requested:\n{\"name\": \"test\"}\nLet me know if you need anything else!"
result = repair_json(text)  # {'name': 'test'}

# Truncated output
text = '{"name": "test", "items": [1, 2, 3'
result = repair_json(text)  # {'name': 'test', 'items': [1, 2, 3]}

# All of the above combined
text = "Sure! ```json\n{'name': 'test',}\n```"
result = repair_json(text)  # {'name': 'test'}
```

For batch processing:

```python
from llm_utils import repair_json_list, safe_json_parse

# Process a list, skip failures
results = repair_json_list(texts, on_error='skip')

# Or get a default value on failure
result = safe_json_parse(text, default={})
```

### Rate Limiting

Token bucket implementation for staying under API rate limits:

```python
from llm_utils import TokenBucket, DualRateLimiter

# Simple token bucket
bucket = TokenBucket(tokens_per_minute=100000)

if bucket.consume(estimated_tokens):
    response = make_api_call()
else:
    bucket.wait_for_tokens(estimated_tokens)
    response = make_api_call()

# Dual limiter for APIs with both request and token limits
limiter = DualRateLimiter(
    requests_per_minute=60,
    tokens_per_minute=100000
)

if limiter.wait_and_acquire(estimated_tokens=2000):
    response = make_api_call()
```

Pre-configured limiters for common APIs:

```python
from llm_utils import ANTHROPIC_RATE_LIMITER, OPENAI_RATE_LIMITER
```

### Batch Processing

Process large batches of prompts with automatic retry logic:

```python
from llm_utils import PromptManager, process_prompts_with_callback

# Using the callback helper
def call_api(prompt):
    return client.messages.create(
        model="claude-3-opus-20240229",
        messages=[{"role": "user", "content": prompt}]
    )

results = process_prompts_with_callback(
    prompts=my_prompts,
    api_callback=call_api,
    max_retries=3,
    save_path="results.json"
)

# Or use PromptManager directly for more control
manager = PromptManager(max_retries=3)
manager.add_prompts(prompts)

for prompt, metadata in manager.pending_prompts():
    try:
        result = call_api(prompt)
        manager.record_success(prompt, result)
    except Exception as e:
        manager.record_failure(prompt, str(e))

# Retry failures
manager.retry_failed()

# Get results
print(manager.summary())
manager.save_results("results.json")
```

## Why These Exist

### JSON Repair

When we started using GPT-3 in 2022 for production applications, we quickly discovered that "return JSON" in a prompt was more of a suggestion than a command. Models would:

- Wrap JSON in markdown code fences (` ```json ... ``` `)
- Use single quotes instead of double quotes
- Add conversational preamble ("Here's the JSON you requested:")
- Truncate output mid-object when hitting token limits
- Include trailing commas
- Leave keys unquoted

We tried prompt engineering. We tried examples. We tried threatening the model. Nothing worked 100% of the time. So we built `repair_json` to handle whatever the model threw at us.

### Rate Limiting

API rate limits are real, and exceeding them kills your batch jobs. The token bucket implementation here handles both request-per-minute and tokens-per-minute limits, with proper refill logic and wait calculations.

### Prompt Management

When you're processing thousands of prompts, you need:
- Progress tracking
- Automatic retries for transient failures  
- Result persistence (so you don't lose everything if your script crashes)
- Clean separation of successes and failures

`PromptManager` handles all of this.

## API Reference

### json_repair

| Function | Description |
|----------|-------------|
| `repair_json(text, target_key=None, strict=False)` | Main repair function, tries multiple strategies |
| `repair_json_list(texts, target_key=None, on_error='skip')` | Batch repair |
| `safe_json_parse(text, default=None)` | Parse with fallback value |
| `remove_markdown_fences(text)` | Strip ` ```json ``` ` wrappers |
| `fix_quotes(text)` | Convert single to double quotes |
| `extract_json_object(text)` | Find JSON in surrounding text |
| `fix_truncated_json(text)` | Close unclosed braces/brackets |
| `fix_common_json_errors(text)` | Fix trailing commas, unquoted keys |

### rate_limiting

| Class | Description |
|-------|-------------|
| `TokenBucket(tokens_per_minute)` | Simple token bucket rate limiter |
| `DualRateLimiter(requests_per_minute, tokens_per_minute)` | Combined request + token limiter |

### prompt_manager

| Class/Function | Description |
|----------------|-------------|
| `PromptManager(max_retries=3)` | Batch processing manager |
| `PromptResult` | Container for prompt results |
| `process_prompts_with_callback(prompts, api_callback, ...)` | Convenience function |

## License

MIT

## Author

Richard Kerr ([@datasciencedoc](https://linkedin.com/in/datasciencedoc))

---

*Built from production code, battle-tested since 2022.*
