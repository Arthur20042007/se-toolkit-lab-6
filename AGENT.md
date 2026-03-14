# Agent Architecture

## Overview

`agent.py` is a Python CLI that calls an LLM with tools to answer questions about the project. It implements an **agentic loop**: the agent asks the LLM a question, the LLM decides which tools to call, the agent executes tools, and the loop continues until the LLM provides a final answer.

## Capabilities by Task

### Task 1: Basic LLM Calling

- ✅ Accept questions as CLI arguments
- ✅ Call OpenRouter API (OpenAI-compatible)
- ✅ Parse LLM responses
- ✅ Return JSON with `answer` and empty `tool_calls`

### Task 2: Documentation Agent

- ✅ Define `read_file` and `list_files` tools
- ✅ Implement agentic loop (max 10 iterations)
- ✅ Execute tools and feed results back to LLM
- ✅ Return JSON with `answer`, `source`, and populated `tool_calls`
- ✅ Path traversal protection for security

### Task 3: System Agent

- ✅ Add `query_api` tool for backend API access
- ✅ Read `LMS_API_KEY` from environment (required for authentication)
- ✅ Read `AGENT_API_BASE_URL` from environment (default: `http://localhost:42002`)
- ✅ Bearer token authentication (OAuth 2.0 standard)
- ✅ Support GET, POST, PUT, DELETE, PATCH methods
- ✅ System prompt guidance for tool selection
- ✅ Error diagnosis workflow: query API for error, read code to debug

## LLM Provider

**OpenRouter** (<https://openrouter.ai>)

- Free tier: 50+ requests/day
- OpenAI-compatible API
- Model: `qwen/qwen-plus` (strong reasoning + tool calling)

## Tools

### read_file

Read a file from the project repository.

**Parameters:**

- `path` (string) — relative path from project root (e.g., `wiki/git.md`)

**Returns:**

- File contents or error message

**Security:**

- Blocks directory traversal (`../`)
- Only allows access within project root

### list_files

List files and directories at a given path.

**Parameters:**

- `path` (string) — directory path from project root (e.g., `wiki`)

**Returns:**

- Newline-separated list of entries

**Security:**

- Blocks directory traversal
- Only lists within project root

### query_api

Query the backend API to get system state, data, and diagnostic information.

**Parameters:**

- `method` (string, required) — HTTP method: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`
- `path` (string, required) — API endpoint path (e.g., `/items/`, `/analytics/completion-rate?lab=lab-1`)
- `body` (string, optional) — JSON request body for POST/PUT/PATCH requests

**Returns:**

- JSON object: `{"status_code": int, "body": str}` where `body` is the response text (limited to 2000 chars)

**Authentication:**

- Requires `LMS_API_KEY` environment variable (different from `LLM_API_KEY`)
- Uses Bearer token: `Authorization: Bearer {LMS_API_KEY}`
- Raises error if `LMS_API_KEY` is not set

**Configuration:**

- Base URL from `AGENT_API_BASE_URL` environment variable (default: `http://localhost:42002`)
- Timeout: 10 seconds per request
- Handles connection errors, timeouts gracefully

**Usage Examples:**

```
query_api("GET", "/items/")
→ {"status_code": 200, "body": "[{\"id\": 1, ...}]"}

query_api("GET", "/analytics/completion-rate?lab=lab-1")
→ {"status_code": 200, "body": "{\"rate\": 0.85}"}

query_api("GET", "/items/", None)  (without auth)
→ {"status_code": 401, "body": "Unauthorized"}
```

**Error Diagnosis Workflow:**

1. When query_api returns error (400, 401, 404, 500):
   - Check the error message body
   - Use read_file to find relevant source code
   - Locate the root cause in backend code
   - Example: "TypeError in ETL" → read `backend/app/etl.py`

## Agentic Loop

The agent runs a loop (max 10 iterations):

1. Send question + tool definitions to LLM
2. If LLM responds with tool calls:
   - Execute each tool
   - Add results to message history
   - Loop back to step 1
3. If LLM responds without tool calls:
   - Return final answer with source reference

```
Question + Tools
    ↓
LLM Decision
    ├─ Has tool calls? → Execute + Loop
    └─ No tool calls? → Return answer
```

## System Prompt

Guides the LLM to:

- Use `read_file` and `list_files` for code, docs, configuration
- Use `query_api` for system state, data queries, and error diagnosis
- Combine tools for complex questions:
  - Get API error → Read source code → Diagnose
  - Example: "Debug /analytics crash" → Query API for error → Read routers → Find bug
- Include source references (file paths or API endpoints)
- Be concise and accurate

## Output Format

```json
{
  "answer": "Answer text with source reference",
  "source": "wiki/git-workflow.md#section-name",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git.md\ngit-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git Workflow\n...content..."
    }
  ]
}
```

## Usage

```bash
# Basic LLM call (Task 1)
uv run agent.py "What is REST?"
# Output: {"answer": "...", "source": "unknown", "tool_calls": []}

# Documentation search (Task 2)
uv run agent.py "How do you resolve a merge conflict?"
# Output: {"answer": "...", "source": "wiki/...", "tool_calls": [...]}

# System intelligence (Task 3)
LMS_API_KEY=test_key uv run agent.py "How many items in the database?"
# Output: {"answer": "...", "source": "...", "tool_calls": [{"tool": "query_api", ...}]}
```

## Configuration

File: `.env.agent.secret` (git-ignored)

```bash
LLM_API_KEY=sk-or-v1-...
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=qwen/qwen-plus
```

## Testing

```bash
# Task 1 tests
uv run pytest tests/test_task1_basic_llm_call.py -v

# Task 2 tests
uv run pytest tests/test_task2_*.py -v

# Task 3 tests
uv run pytest tests/test_task3_*.py -v

# Run benchmark
uv run run_eval.py
```

## Files

- `agent.py` — Agent CLI and agentic loop implementation (all tasks)
- `.env.agent.secret` — LLM credentials (gitignored)
- `plans/task-1.md` — Implementation plan for Task 1
- `plans/task-2.md` — Implementation plan for Task 2
- `plans/task-3.md` — Implementation plan for Task 3
- `AGENT.md` — This file (documentation)

## Lessons Learned

### Task 3: System Agent

1. **Authentication Separation**: `LMS_API_KEY` is separate from `LLM_API_KEY` — different services with different auth mechanisms

2. **Environment-Based Configuration**: All credentials read from environment (no hardcoding) — enables testing with different backends

3. **Tool Selection in System Prompt**: Clear guidance needed for LLM to choose correct tool:
   - Wiki/code questions → use read_file/list_files
   - Data/system questions → use query_api
   - Error diagnosis → combine both (API for error, code for root cause)

4. **Error Response Handling**: API returns error status codes (401, 404, 500) — system should guide LLM to read error body and investigate code

5. **Response Size Limits**: API responses capped at 2000 chars to avoid context explosion in large datasets

6. **Bearer Token Format**: Uses standard OAuth 2.0 Bearer token for API authentication
