import json
import os
import sys
import httpx
from typing import Any, Dict


def log_debug(message: str) -> None:
    """Prints debug messages to stderr."""
    print(f"DEBUG: {message}", file=sys.stderr)


def get_env_var(key: str) -> str:
    """Gets an environment variable or exits if not set."""
    val = os.environ.get(key)
    if not val:
        # Try loading from .env.agent.secret manually if not in environment
        try:
            with open(".env.agent.secret", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        if k.strip() == key:
                            return v.strip(" \"'")
        except FileNotFoundError:
            pass

        print(
            f"Error: Environment variable {key} is required. Please set it in .env.agent.secret",
            file=sys.stderr,
        )
        sys.exit(1)
    return val


def main() -> None:
    if len(sys.argv) < 2:
        print("Error: Missing question argument.", file=sys.stderr)
        print('Usage: uv run agent.py "<question>"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    log_debug(f"Received question: {question}")

    api_key = get_env_var("LLM_API_KEY")
    base_url = get_env_var("LLM_API_BASE_URL")
    model = get_env_var("LLM_API_MODEL")

    # Construct the base URL appropriately handling trailing slashes or /chat/completions
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"

    log_debug(f"Sending request to {url} using model {model}")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Keep your answers concise.",
            },
            {"role": "user", "content": question},
        ],
    }

    try:
        # 60s timeout as per requirements
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data: Dict[str, Any] = response.json()

            answer = data["choices"][0]["message"]["content"]

            output = {"answer": answer.strip(), "tool_calls": []}
            log_debug("Successfully received response from LLM.")
            # Only valid JSON to stdout
            print(json.dumps(output))
            sys.exit(0)

    except httpx.HTTPStatusError as e:
        print(
            f"Error: API request failed with status code {e.response.status_code}.",
            file=sys.stderr,
        )
        print(e.response.text, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to communicate with LLM API: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
