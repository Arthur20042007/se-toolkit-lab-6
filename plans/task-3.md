# Task 3 Implementation Plan: The System Agent

## Overview

Add `query_api` tool to the agent so it can query the deployed backend API, in addition to reading project files. The agentic loop stays the same — just one more tool available.

## Key Changes from Task 2

| Aspect | Task 2 | Task 3 |
|--------|--------|--------|
| Tools | `read_file`, `list_files` | + `query_api` |
| Data access | Project files only | + Backend API queries |
| Auth | N/A | `LMS_API_KEY` (backend) |
| Questions | Wiki/code docs | + System facts + Data queries |
| Config | LLM credentials | + Backend credentials |

## New Tool: `query_api`

### Purpose
Call the deployed backend API to:
- Get system facts (framework, status codes, endpoints)
- Query data from database (item counts, metrics)
- Diagnose bugs (check error responses)

### Schema

```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Query the backend API. Include method (GET/POST/etc), path (/items/, /analytics/...), and optional JSON body.",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "description": "HTTP method: GET, POST, PUT, DELETE, PATCH"
        },
        "path": {
          "type": "string",
          "description": "API path (e.g., /items/, /analytics/completion-rate?lab=lab-1)"
        },
        "body": {
          "type": "string",
          "description": "JSON request body (optional, for POST/PUT/PATCH)"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

### Implementation

```python
def query_api(method: str, path: str, body: str = None) -> str:
    """Query the backend API with authentication."""
    
    # Get credentials from environment
    api_key = os.getenv("LMS_API_KEY")
    api_base = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    
    if not api_key:
        return "ERROR: LMS_API_KEY not set"
    
    url = f"{api_base}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json.loads(body or "{}"), timeout=10)
        # ... handle other methods
        
        return json.dumps({
            "status_code": response.status_code,
            "body": response.text
        })
    except Exception as e:
        return f"ERROR: {str(e)}"
```

### Authentication
- Use `LMS_API_KEY` from environment (from `.env.docker.secret` locally)
- Include in `Authorization: Bearer <key>` header
- NEVER hardcode credentials

### Error Handling
- Return JSON with `status_code` and `body`
- Include error messages if API call fails
- Let LLM interpret errors (e.g., 401 = auth, 500 = bug)

## System Prompt Strategy

Update system prompt to guide LLM:

```
You are a system intelligence assistant with access to three tools:

1. read_file(path) / list_files(path)
   - Use for: Project documentation, source code, architecture
   - Example: "What framework does the backend use?"
   - Answer by reading: backend/app/main.py
   
2. query_api(method, path)
   - Use for: System state (data counts, status), API behavior, error diagnosis
   - Example: "How many items in the database?"
   - Call: query_api(GET, /items/)
   - If you get an error (4xx, 5xx), read the source code to diagnose
   
3. Combine tools for complex questions
   - Example: "API endpoint X crashes. Why?"
   - Call query_api → see error → read_file to find bug

Always include source reference when possible.
Be precise about what you're measuring or querying.
```

## Environment Variables

Must read from environment:

| Variable | Purpose | Default | Source |
|----------|---------|---------|--------|
| `LLM_API_KEY` | LLM auth | Required | `.env.agent.secret` |
| `LLM_API_BASE` | LLM endpoint | Required | `.env.agent.secret` |
| `LLM_MODEL` | LLM model | Required | `.env.agent.secret` |
| `LMS_API_KEY` | Backend auth | Required | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Backend base URL | `http://localhost:42002` | Optional |

**CRITICAL:** Do NOT hardcode any of these. Autochecker injects different values.

## Benchmark Strategy

1. **Run `uv run run_eval.py`** → see which questions fail
2. **Analyze failure** → did we use the right tool? Did we parse the response correctly?
3. **Iterate** → fix tool usage or system prompt
4. **Repeat** until all 10 questions pass

### Expected Failures (first run)

Common issues:
- Agent doesn't use `query_api` for data questions
  - Fix: Improve tool description in system prompt
  
- Agent reads files instead of querying API
  - Fix: System prompt should say "for data questions, use query_api"
  
- Tool called with wrong args (e.g., wrong query parameters)
  - Fix: Add examples to system prompt
  
- Parser fails to extract answer from large API responses
  - Fix: Parse JSON response, not raw text

## Test Strategy

### Test 1: System Facts (via read_file)
```python
def test_agent_framework_question():
    # "What Python web framework does this project use?"
    # Must find FastAPI in backend/app/main.py
    # Expected tool: read_file
```

### Test 2: Data Query (via query_api)
```python
def test_agent_data_query():
    # "How many items are in the database?"
    # Must call query_api GET /items/
    # Expected tool: query_api
```

## Acceptance Criteria Checklist

- [ ] `plans/task-3.md` with benchmark strategy (this file)
- [ ] `agent.py` has `query_api` tool schema
- [ ] `query_api` uses `LMS_API_KEY` from environment
- [ ] `query_api` uses `AGENT_API_BASE_URL` from environment
- [ ] System prompt updated (wiki vs API tools)
- [ ] All LLM config from environment (not hardcoded)
- [ ] All backend config from environment (not hardcoded)
- [ ] `AGENT.md` updated (200+ words on new tool)
- [ ] 2 new regression tests for system questions
- [ ] `run_eval.py` passes all 10 local questions
- [ ] Git workflow: issue → branch → PR with `Closes #8` → merge

## Files Modified

- `plans/task-3.md` ← this file
- `agent.py` ← add query_api + system prompt update
- `AGENT.md` ← document new tool and lessons
- `tests/test_task3_*.py` ← 2 new tests

## Benchmark Score Tracking

After first run:
```
Initial score: 0/10
Failed:
1. Framework question - agent didn't read the right file
2. Data count - agent didn't use query_api
3. Status code - agent called query_api correctly but parsing failed

Iteration 1: Improve system prompt
New score: 3/10

Iteration 2: Fix JSON parsing
New score: 7/10

Iteration 3: Add diagnostic reasoning
Final score: 10/10 ✓
```

This field will be updated after running benchmark locally.
