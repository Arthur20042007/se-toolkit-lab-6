# Task 3: System Agent - Final Deployment

## Status
- ✅ agent.py: Complete, tested, all syntax errors fixed
- ✅ Python 3 compatible (no Python 2 syntax)
- ✅ Supports both Gemini and OpenAI-compatible APIs
- ✅ All 3 tools implemented: read_file, list_files, query_api
- ✅ Agentic loop: max 10 iterations, proper tool calling
- ✅ Exit codes: 0=success, 1=failure
- ✅ Output: valid JSON to stdout, debug to stderr

## For Autochecker on VM

### Step 1: Get latest code
```bash
cd ~/se-toolkit-lab-6
git fetch
git checkout main
git pull origin main
```

### Step 2: Setup environment
```bash
# Ensure uv is installed and synced
which uv || (curl -L https://astral.sh/uv/install.sh | sh)
uv sync
```

### Step 3: Configure credentials
The autochecker will inject these environment variables. 
If testing manually, use test values:

```bash
cat > .env.agent.secret << 'EOF'
LLM_API_KEY=AIzaSyBWORy9ovuFvgJlAsYdVZifXVfMQUTzwJo
LLM_API_BASE=https://generativelanguage.googleapis.com/v1beta
LLM_MODEL=gemini-3.1-flash-lite-preview
EOF
```

For backend API (in separate .env.docker.secret):
```bash
cat > .env.docker.secret << 'EOF'
LMS_API_KEY=my-secret-api-key
AGENT_API_BASE_URL=http://localhost:42002
EOF
```

### Step 4: Manual test
```bash
uv run agent.py "What is 2+2?"
# Expected: {"answer": "4", "source": "unknown", "tool_calls": []}
```

### Step 5: Run autochecker
```bash
uv run run_eval.py
# Should test 10 local questions
# Then autochecker will test 5 hidden questions
```

## Troubleshooting

### Agent crashes with exit code 1
**Step 1:** Check if .env.agent.secret exists
```bash
cat .env.agent.secret
# Should show: LLM_API_KEY, LLM_API_BASE, LLM_MODEL
```

**Step 2:** Check for Windows line endings
```bash
file .env.agent.secret
# Should say: ASCII text (not CRLF)

# Fix if needed:
sed -i 's/\r$//' .env.agent.secret
```

**Step 3:** Load env and test manually
```bash
set -a && . <(tr -d '\r' < .env.agent.secret) && set +a
uv run agent.py "test" 2>&1
```

**Step 4:** Read the stderr output - it will tell you exactly what's wrong
- `ERROR: .env.agent.secret not found` → missing file
- `ERROR: Missing LLM configuration` → incomplete env vars
- `ERROR: HTTP error calling Gemini` → API key or model name wrong
- `ERROR: Failed to connect to API` → backend not running

### Agent runs but returns invalid JSON
This should not happen - all code paths return valid JSON.
If it does:
1. Check stderr for error messages
2. Verify agent.py has no truncated/corrupted lines
3. Run: `python3 -m py_compile agent.py` (check syntax)

### Agent returns empty answer
This is OK - LLM can return empty text if unsure.
The structure is still valid JSON.

## Architecture Summary

```
User question
  ↓
agent.py main() loads .env.agent.secret
  ↓
load_config() → reads LLM_API_KEY, LLM_API_BASE, LLM_MODEL
  ↓
Agentic loop (max 10 iterations):
  1. call_llm() sends messages + tools to LLM
  2. LLM can call: read_file, list_files, query_api
  3. Agent executes tool and returns result to LLM
  4. Loop until LLM returns no tool_calls
  ↓
Return JSON: {answer, source, tool_calls}
  ↓
main() prints JSON to stdout, exits with code 0
```

## Key Code Sections

### API Detection (line ~254)
```python
is_gemini = "generativelanguage.googleapis.com" in api_base
if is_gemini:
    return call_gemini_llm(...)
else:
    return call_openai_compatible_llm(...)
```

### Query API (line ~116)
```python
api_key = os.getenv("LMS_API_KEY")
api_base = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
# ... makes HTTP request with Bearer token
# Returns JSON: {"status_code": 200, "body": "..."}
```

### Tool Definitions (line ~174)
- read_file(path) → reads file, validates path doesn't escape project
- list_files(path) → lists directory contents
- query_api(method, path, body) → HTTP request to backend API

## Testing Locally (Before VM)

All these passed:
```bash
uv run agent.py "2+2"                    # Basic math ✓
uv run agent.py "What is REST?"          # Knowledge ✓
uv run agent.py "Explain Python"         # Explanation ✓
```

All returned: exit code 0, valid JSON with answer field.

## Commits
- `1a9d411`: Fix Python 3 syntax in validate_path (CRITICAL)
- `2e12a9b`: Support both Gemini and OpenAI-compatible APIs
- `174a5d4`: Complete rewrite for Gemini compatibility

## Final Checklist for Autochecker
- [x] agent.py syntax valid (Python 3)
- [x] All imports work (requests, json, sys, os, re, pathlib, dotenv)
- [x] .env.agent.secret can be loaded by load_config()
- [x] LLM API key is read from environment (not hardcoded)
- [x] All 3 tools are defined and callable
- [x] Agentic loop runs max 10 iterations
- [x] JSON output is valid
- [x] Exit code 0 on success
- [x] Debug output goes to stderr only
