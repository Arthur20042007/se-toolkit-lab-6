# Task 1 Plan: Call an LLM from Code

## LLM Provider and Model

- Provider: OpenRouter
- Model: `meta-llama/llama-3.3-70b-instruct:free`
- Fallback Provider: Qwen Code API
- Fallback Model: `qwen3.5-plus`

## Agent Structure

- **Code**: `agent.py`
- **Dependencies**: `httpx` for making API requests to the LLM.
- **Input**: Take the first CLI argument as the user query.
- **Environment**: Load `LLM_API_KEY`, `LLM_API_BASE_URL`, and `LLM_API_MODEL` from `.env.agent.secret` (using standard Python or python-dotenv if available).
- **Execution**:
  1. Retrieve the environment variables.
  2. Structure the payload according to the OpenAI Chat Completion format (`messages` array).
  3. Send a POST request to the `LLM_API_BASE_URL`.
  4. Parse the `content` of the `assistant` message.
  5. Print the output in the required JSON format `{"answer": "...", "tool_calls": []}` to standard output (`sys.stdout`).
  6. Direct all debug or error logs to `sys.stderr`.
- **Timing**: Set a timeout of 60 seconds on the HTTP request.

## Testing

- Add `test_agent.py` regression test which uses `subprocess` to execute `uv run agent.py "Test"` and asserts that a valid JSON with `answer` and `tool_calls` is returned on stdout.
