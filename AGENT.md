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

## LLM Provider

**OpenRouter** (https://openrouter.ai)

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
- Use `list_files` to discover relevant files
- Use `read_file` to find answers
- Include source references (wiki file paths)
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
```

## Files

- `agent.py` — Agent CLI and agentic loop implementation
- `.env.agent.secret` — LLM credentials (gitignored)
- `plans/task-1.md` — Implementation plan for Task 1
- `plans/task-2.md` — Implementation plan for Task 2
- `AGENT.md` — This file
