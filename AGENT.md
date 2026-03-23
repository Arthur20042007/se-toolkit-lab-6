# Agent Documentation

## Architecture

This agent is a simple Python CLI (`agent.py`) that answers user questions by connecting to an LLM via the OpenAI chat completions API format. It retrieves an access token and base URL from the local `.env.agent.secret` configuration.

## Agentic Loop & Tools

The agent now incorporates an "agentic loop". Before returning a final answer, the LLM can decide to call functions (tools) to interact with the environment (the project's files).

When the LLM is queried, it is provided with two tools in its schema:
- `read_file`: Reads the contents of a file from the repository to extract specific information.
- `list_files`: Lists files and directories at a given path to discover project topology (like finding wiki files).

The code runs a control loop (up to 10 iterations max/tool usages). Over these iterations:
1. LLM provides a list of `tool_calls`.
2. Python executes the requested operations locally (via `agent.py`).
3. Python sends the results back to the LLM.
4. When the LLM finally outputs standard JSON text instead of tool calls, that's designated as the final answer. The answer and source reference are compiled and output as JSON.

We structure our request to force JSON mode on the final answer so it robustly extracts the `answer` string and `source` string. Path traversal is explicitly blocked in Python.

## LLM Provider Configuration

The agent fetches its environment variables from `.env.agent.secret`. You can use any OpenAI-compatible provider.

### Option 1: OpenRouter (Easy Alternative)

OpenRouter provides free models that are easy to access.

1. Create `.env.agent.secret` on your machine:

   ```bash
   cp .env.agent.example .env.agent.secret
   ```

2. Edit `.env.agent.secret` with OpenRouter keys:

   ```
   LLM_API_KEY=your_openrouter_api_key
   LLM_API_BASE_URL=https://openrouter.ai/api/v1
   LLM_API_MODEL=meta-llama/llama-3.3-70b-instruct:free
   ```

 *(You can get a free API key at [OpenRouter](https://openrouter.ai)).*

### Option 2: Qwen Code API (Recommended)

You can deploy a Qwen Code API proxy on your VM to funnel requests to the free Qwen models using a Qwen-specific API.

1. SSH into your VM and configure the `qwen-code` CLI and `qwen-code-api` according to the wiki instructions.
2. In your `.env.agent.secret`:

   ```
   LLM_API_KEY=<qwen-code-api-key>
   LLM_API_BASE_URL=http://<VM-IP>:<PORT>/v1
   LLM_API_MODEL=qwen3.5-plus
   ```

## How to run

```bash
uv run agent.py "What does REST stand for?"
```

## Logging

The standard output (`stdout`) contains only a single JSON response on success:

```json
{"answer": "...", "tool_calls": []}
```

All diagnostic output, logs, and errors are printed to `stderr`.
