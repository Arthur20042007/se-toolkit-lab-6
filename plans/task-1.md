# Task 1 Implementation Plan: Call an LLM from Code

## Overview

Build a Python CLI agent (`agent.py`) that connects to an LLM and returns structured JSON responses.

## LLM Provider Selection

**Chosen: OpenRouter** (<https://openrouter.ai>)

### Why OpenRouter?

- ✅ Free tier: 50 requests per day (sufficient for testing)
- ✅ No credit card required
- ✅ Supports free models with strong tool-calling ability
- ✅ OpenAI-compatible API (easy integration)
- ✅ Works globally (including Russia)
- ✅ No VM setup needed

### Alternative Considered

- Qwen Code API: Requires VM setup with docker-compose deployment
- Decision: OpenRouter is simpler for initial development

## Model Selection

**Model: `qwen/qwen-plus`** (OpenRouter endpoint)

- Strong code understanding and reasoning
- Available on OpenRouter free tier
- Reliable performance for structured outputs

## Architecture

```
┌─────────────────────┐
│  User Terminal      │
│  uv run agent.py    │
│  "What is REST?"    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   agent.py          │
│ ┌────────────────┐  │
│ │ 1. Parse CLI   │  │
│ │ 2. Load .env   │  │
│ │ 3. Call LLM    │  │
│ │ 4. Output JSON │  │
│ └────────────────┘  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  OpenRouter API     │
│  /v1/chat/...       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Qwen Plus LLM      │
│                     │
└─────────────────────┘
```

## Implementation Details

### 1. Environment Configuration

File: `.env.agent.secret`

- `LLM_API_KEY`: OpenRouter API key (from <https://openrouter.ai>)
- `LLM_API_BASE`: `https://openrouter.ai/api/v1`
- `LLM_MODEL`: `qwen/qwen-plus`

### 2. CLI Interface

```bash
uv run agent.py "What does REST stand for?"
```

**Output (stdout):**

```json
{"answer": "Representational State Transfer...", "tool_calls": []}
```

### 3. Code Structure

```python
# agent.py
├── Load environment variables (.env.agent.secret)
├── Parse command-line arguments
├── Create system prompt
├── Call LLM API (OpenRouter)
├── Parse response
├── Extract answer text
├── Return JSON: {answer, tool_calls}
└── Debug output to stderr
```

### 4. Error Handling

- ✅ Missing environment variables → clear error message
- ✅ API connection timeout → fail with status code 1
- ✅ Invalid JSON response → debug to stderr, return error
- ✅ Rate limiting → appropriate error handling

### 5. System Prompt

Minimal prompt (will expand in Tasks 2-3):

```
You are a helpful coding assistant.
Answer questions concisely and accurately.
```

## Dependencies

- `python-dotenv`: Load .env files
- `requests`: HTTP API calls
- `openai`: Optional (for type hints only)

## Testing Strategy

1. Regression test: `tests/integration/test_task1_basic_llm_call.py`
   - Runs `agent.py` as subprocess
   - Parses JSON output
   - Validates `answer` and `tool_calls` fields
   - Checks non-empty answer

## Acceptance Criteria Checklist

- [ ] `plans/task-1.md` created with plan (committed before code)
- [ ] `agent.py` created and functional
- [ ] Output is valid JSON with `answer` and `tool_calls`
- [ ] `.env.agent.secret` stores API key (not hardcoded)
- [ ] `AGENT.md` documents architecture
- [ ] 1 regression test passes
- [ ] Git workflow: issue → branch → PR → merge

## Timeline

- 10 min: Create files and environment setup
- 15 min: Implement `agent.py`
- 5 min: Create documentation
- 10 min: Write and run tests
- 5 min: Git workflow (commit, push, PR)

**Total: ~45 minutes**
