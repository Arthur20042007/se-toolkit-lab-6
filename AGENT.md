# Agent Documentation

## Architecture

This agent is a simple Python CLI (`agent.py`) that answers user questions by connecting to an LLM via the OpenAI chat completions API format. It retrieves an access token and base URL from the local `.env.agent.secret` configuration.

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
