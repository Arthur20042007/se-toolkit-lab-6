# Agent Architecture

## Overview

`agent.py` is a Python CLI that calls an LLM and returns structured JSON responses. It serves as the foundation for building an agentic system with tools and reasoning capabilities in later tasks.

## Current Capabilities (Task 1)

- ✅ Accept questions as CLI arguments
- ✅ Call OpenRouter API (OpenAI-compatible)
- ✅ Parse LLM responses
- ✅ Return JSON with `answer` and (empty) `tool_calls`
- ✅ 60-second timeout
- ✅ Proper error handling and logging to stderr

## LLM Provider

**OpenRouter** (https://openrouter.ai)

### Why OpenRouter?

- Free tier: 50+ requests per day (no credit card)
- OpenAI-compatible `/v1/chat/completions` API
- Global access (works from Russia)
- Multiple free models available

### Model

**`qwen/qwen-plus`** (OpenRouter endpoint for Qwen Plus)

- Strong code understanding and reasoning
- Available on free tier of OpenRouter
- Good performance/reliability ratio

## Architecture

```
User Input (CLI)
    │
    └─→ agent.py
            │
            ├─→ Load .env.agent.secret
            │   ├─ LLM_API_KEY
            │   ├─ LLM_API_BASE
            │   └─ LLM_MODEL
            │
            ├─→ Parse CLI arguments
            │
            ├─→ Build API request
            │   └─ system prompt
            │   └─ user question
            │
            ├─→ Call OpenRouter API
            │
            ├─→ Parse response
            │
            └─→ Output JSON
                └─ {answer, tool_calls}
```

## Configuration

File: `.env.agent.secret` (git-ignored)

```bash
LLM_API_KEY=sk-or-v1-...           # OpenRouter API key
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=qwen/qwen-plus
```

### How to Create

```bash
cp .env.agent.example .env.agent.secret
# Edit with your OpenRouter API key
```

### Get an API Key

1. Visit https://openrouter.ai
2. Sign up (free, no credit card)
3. Go to Settings → API Keys
4. Create a new key
5. Copy it to `.env.agent.secret`

## Usage

```bash
# Installation (first time)
uv sync

# Run the agent
uv run agent.py "What is REST?"

# Expected output (stdout):
# {"answer": "Representational State Transfer. It's an architectural style...", "tool_calls": []}
```

### Debug Output

All debug/progress messages go to **stderr**, not stdout:

```bash
# Run with debug output visible:
uv run agent.py "Your question" 2>&1

# In your code, use:
print("[DEBUG] Message here", file=sys.stderr)
```

## Input/Output Contract

### Input

- **CLI argument #1**: String question
- **Timeout**: 60 seconds

### Output (stdout, always valid JSON)

```json
{
  "answer": "The answer to the question",
  "tool_calls": []
}
```

### Exit Codes

- `0`: Success
- `1`: Any error (missing config, API error, timeout, etc.)

## Error Handling

| Error | Handling |
|-------|----------|
| Missing `.env.agent.secret` | Print to stderr, exit 1 |
| Missing env variables | Print to stderr, exit 1 |
| API connection timeout | Print to stderr, exit 1 |
| API HTTP error | Print response, exit 1 |
| Invalid JSON response | Print to stderr, exit 1 |
| No arguments | Print usage, exit 1 |

## Future Tasks

### Task 2: Add Tools

- Define tools (read_file, list_dir, run_code, etc.)
- Add `tool_calls` to output
- Implement tool execution loop

### Task 3: Build Agentic Loop

- Implement reasoning loop
- Handle tool results
- Multi-step reasoning chains

## Dependencies

- `python-dotenv`: Load `.env` files
- `requests`: HTTP API calls

## Development Notes

- All API calls use OpenAI-compatible format (`.../v1/chat/completions`)
- System prompt is minimal (will expand in Task 2 with tool definitions)
- Temperature set to 0.7 for balanced creativity/consistency
- No tools defined yet (tool_calls always empty)

## Testing

Run tests with:

```bash
pytest tests/integration/test_task1_basic_llm_call.py -v
```

See `tests/integration/test_task1_basic_llm_call.py` for details.
