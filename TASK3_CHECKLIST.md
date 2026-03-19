# Task 3 Final Checklist

## Local (completed)
- [x] agent.py syntax correct (Python 3, no `except ValueError, RuntimeError:` errors)
- [x] agent.py imports successfully: requests, json, sys, os, re, pathlib, dotenv
- [x] load_config() reads LLM_API_KEY/LLM_API_BASE/LLM_MODEL (standard task-3)
- [x] load_config() falls back to GEMINI_API_KEY/GEMINI_MODEL
- [x] All 3 tools defined: read_file, list_files, query_api
- [x] call_llm() detects API type and dispatches to correct handler
- [x] Main returns valid JSON with answer, source, tool_calls
- [x] Main returns exit code 0 on success, 1 on error
- [x] Only debug output goes to stderr, JSON to stdout

## Tests passed
- [x] `uv run agent.py "2+2"` → exit 0, valid JSON
- [x] `uv run agent.py "What is REST?"` → exit 0, valid JSON  
- [x] `uv run agent.py "Explain Python"` → exit 0, valid JSON
- [x] All outputs parse as JSON successfully

## On VM next
1. `git pull origin main` (get latest agent.py with syntax fix)
2. Create `.env.agent.secret` with LLM credentials (avto-chekeur will provide or use test values)
3. `uv sync` (ensure dependencies)
4. Manual test: `uv run agent.py "What is 2+2?"`
5. Run autochecker

## Commit log
- 1a9d411: Fix Python 3 syntax in validate_path exception handler ✓
- 2e12a9b: Support both standard and Gemini config formats ✓
- 174a5d4: Complete rewrite for Gemini API ✓

## Known good values (for testing)
```
LLM_API_KEY=AIzaSyBWORy9ovuFvgJlAsYdVZifXVfMQUTzwJo
LLM_API_BASE=https://generativelanguage.googleapis.com/v1beta
LLM_MODEL=gemini-3.1-flash-lite-preview
```

## Debugging on VM
If agent crashes:
1. Check .env.agent.secret: `cat .env.agent.secret`
2. Check if dotenv can load it: `set -a && . <(tr -d '\r' < .env.agent.secret) && set +a`
3. Run agent: `uv run agent.py "test"`
4. Check stderr output for specific error
5. For Windows line endings: `sed -i 's/\r$//' .env.agent.secret`

## Architecture
- Agentic loop runs max 10 iterations
- LLM can call: read_file, list_files, query_api
- System prompt explains when to use each tool
- query_api handles GET/POST/PUT/DELETE/PATCH with LMS_API_KEY auth
- read_file validates path doesn't escape project root
