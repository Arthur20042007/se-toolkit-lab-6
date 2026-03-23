# Task 3 Plan: The System Agent

## 1. Goal
Add a `query_api` tool to the agent so it can interact with the deployed backend API. It needs to read new environment variables (`LMS_API_KEY`, `AGENT_API_BASE_URL`), and understand when to use `query_api` versus accessing local files.

## 2. Environment Variables & Secret Handling
- Modify `get_env_var` logic to support multiple fallback dotenv files `.env.agent.secret` and `.env.docker.secret`.
- Extract `LMS_API_KEY` for backend API authorization.
- Extract `AGENT_API_BASE_URL` with a default of `http://localhost:42002` if missing.

## 3. `query_api` Tool Schema
We will provide the LLM a schema for `query_api`:
- **Parameters:**
  - `method`: HTTP method like `GET`, `POST`, `PUT`, `DELETE`.
  - `path`: API path (e.g. `/items/`).
  - `body`: Optional JSON string to inject as the request body.
- **Returns:** JSON containing `status_code` and `body` from `httpx`.

## 4. Updates to the System Prompt
We will instruct the LLM:
- Keep `list_files` and `read_file` for exploring source code and wikis.
- Use `query_api` to check running backend state and metrics.
- Output JSON. `source` is now optional (so it can be safely omitted or left empty when answering dynamic queries or system facts where no single wiki file applies).

## 5. Iterative Debugging Plan
After implementing the changes, we'll test locally using `uv run run_eval.py`.
- **First Iteration:** Run the benchmark, record failures.
- **Subsequent Iterations:** Improve the LLM prompts or output handling. E.g., make sure we use `.get("content") or ""` to avoid `AttributeError: 'NoneType'` on tool calls, and increase file reading limits in prompts if necessary.

## 6. End-to-End Tests
Add tests into `backend/tests/unit/test_agent.py` checking if the agent calls `query_api` and `read_file` correctly for the respective backend vs framework questions.

**Initial score:** (To be updated after first run)
**Strategy:** Parse error feedback from `run_eval.py` to tailor the system prompt, specifically how the LLM maps the user's intent to either a code file, a wiki, or an API call.