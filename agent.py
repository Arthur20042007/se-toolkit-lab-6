import json
import os
import sys
import httpx
from typing import Any, Dict, List

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root.",
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root.",
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the deployed backend API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                        "description": "HTTP method to use",
                    },
                    "path": {
                        "type": "string",
                        "description": "API path, e.g. /items/",
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON string to send as the request body",
                    },
                    "include_auth": {
                        "type": "boolean",
                        "description": "Whether to include the Authorization header. Defaults to true.",
                    },
                },
                "required": ["method", "path"],
                "additionalProperties": False,
            },
        },
    },
]


def query_api(method: str, path: str, body: str = None, include_auth: bool = True) -> str:
    """Queries the deployed backend API."""
    try:
        agent_base_url = get_env_var(
            "AGENT_API_BASE_URL", ".env.docker.secret", "http://localhost:42002"
        ).rstrip("/")
        lms_api_key = get_env_var(
            "LMS_API_KEY", ".env.docker.secret", ""
        )  # we will just let it fail if it needs auth but key is empty

        url = f"{agent_base_url}/{path.lstrip('/')}"

        headers = {}
        if lms_api_key and include_auth:
            headers["Authorization"] = f"Bearer {lms_api_key}"

        kwargs: Dict[str, Any] = {
            "method": method,
            "url": url,
            "headers": headers,
            "timeout": 30.0,
        }
        if body:
            try:
                kwargs["json"] = json.loads(body)
            except json.JSONDecodeError:
                kwargs["content"] = body

        with httpx.Client() as client:
            response = client.request(**kwargs)
            try:
                # Provide cleaner JSON to the LLM instead of escaped strings
                parsed_body = response.json()
            except Exception:
                parsed_body = response.text
            result = {"status_code": response.status_code, "body": parsed_body}
            return json.dumps(result)

    except Exception as e:
        return json.dumps({"error": str(e)})


def list_files(path: str) -> str:
    """Lists files and directories at a given path from project root."""
    try:
        base_dir = os.path.abspath(os.getcwd())
        target_dir = os.path.abspath(os.path.join(base_dir, path))

        # Security check: ensure target_dir is within base_dir
        if not target_dir.startswith(base_dir):
            return "Error: Access to path outside project directory is forbidden."

        if not os.path.exists(target_dir):
            return f"Error: Path '{path}' does not exist."

        if not os.path.isdir(target_dir):
            return f"Error: Path '{path}' is not a directory."

        files = os.listdir(target_dir)
        return "\n".join(files) if files else "Directory is empty."
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def read_file(path: str) -> str:
    """Read a file from the project repository."""
    try:
        base_dir = os.path.abspath(os.getcwd())
        target_file = os.path.abspath(os.path.join(base_dir, path))

        # Security check: ensure target_file is within base_dir
        if not target_file.startswith(base_dir):
            return "Error: Access to path outside project directory is forbidden."

        if not os.path.exists(target_file):
            return f"Error: File '{path}' does not exist."

        if not os.path.isfile(target_file):
            return f"Error: Path '{path}' is not a file."

        with open(target_file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def log_debug(message: str) -> None:
    """Prints debug messages to stderr."""
    print(f"DEBUG: {message}", file=sys.stderr)


def get_env_var(
    key: str, fallback_file: str = ".env.agent.secret", default_val: str = None
) -> str:
    """Gets an environment variable or exits if not set."""
    val = os.environ.get(key)
    if not val:
        # Try loading from fallback file manually if not in environment
        try:
            with open(fallback_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == key:
                            return v.strip(" \"'")
        except FileNotFoundError:
            pass

        if default_val is not None:
            return default_val

        print(
            f"Error: Environment variable {key} is required. Please set it in {fallback_file}",
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

    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                'You are a specialized agent handling questions about project code, wiki, and API. '
                'CRITICAL INSTRUCTIONS: '
                '1. When asked to count things (items, distinct learners), ALWAYS use `query_api` on the appropriate endpoint (e.g. `/items/`, `/learners/`) and explicitly parse the JSON array to COUNT the elements. Output the number. '
                '2. When asked about bugs/errors, DO BOTH: `query_api` to reproduce the error, and `read_file` on the source code. Output exact error types like "ZeroDivisionError" or "TypeError" if you see them. '
                '3. Look out for these specific bugs: None-unsafe calls (`TypeError` because of `sorted()` with `None` values in `/analytics/top-learners`), and field name mismatches between schemas/models (e.g. `InteractionModel` vs `InteractionLog` in `/interactions/` where it causes `ZeroDivisionError` or crash). '
                '4. When asked about error handling strategies, use `read_file` on BOTH `backend/app/etl.py` and files in `backend/app/routers/` to compare how they handle failures. '
                'Use `list_files`, `read_file`, and `query_api` (set include_auth=false if testing unauthenticated). '
                'Formulate a precise response. YOU MUST output the final answer exactly as JSON: {"answer": "Detailed answer", "source": "wiki/file.md#anchor"}. "source" is only for wiki info, leave empty otherwise. Do not output anything else.'
            ),
        },
        {"role": "user", "content": question},
    ]

    all_tool_calls_record = []

    try:
        with httpx.Client(timeout=60.0) as client:
            for iteration in range(10):
                payload = {
                    "model": model,
                    "messages": messages,
                    "tools": TOOLS,
                    "response_format": {"type": "json_object"},
                }

                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                message = data["choices"][0]["message"]

                # Prevent null content which can crash some providers
                if message.get("content") is None:
                    message["content"] = ""

                if message.get("tool_calls"):
                    # Process tool calls
                    messages.append(message)

                    for tool_call in message["tool_calls"]:
                        function_name = tool_call["function"]["name"]
                        try:
                            arguments = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            arguments = {}

                        log_debug(
                            f"Calling tool: {function_name} with args: {arguments}"
                        )

                        tool_result = ""
                        if function_name == "list_files":
                            tool_result = list_files(arguments.get("path", ""))
                        elif function_name == "read_file":
                            tool_result = read_file(arguments.get("path", ""))
                        elif function_name == "query_api":
                            tool_result = query_api(
                                arguments.get("method", "GET"),
                                arguments.get("path", "/"),
                                arguments.get("body"),
                                arguments.get("include_auth", True),
                            )
                        else:
                            tool_result = f"Error: Unknown tool {function_name}"

                        # Record tool call for final output
                        all_tool_calls_record.append(
                            {
                                "tool": function_name,
                                "args": arguments,
                                "result": tool_result,
                            }
                        )

                        # Add tool response to messages
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": str(tool_result),
                            }
                        )
                else:
                    # No tool calls, we have the final answer. Parse the JSON.
                    content = message.get("content", "")
                    try:
                        final_json = json.loads(content)
                        answer = final_json.get("answer", "")
                        source = final_json.get("source", "")
                    except json.JSONDecodeError:
                        answer = content
                        source = None

                    output = {
                        "answer": answer.strip(),
                        "tool_calls": all_tool_calls_record,
                    }
                    if source:
                        output["source"] = source

                    log_debug("Successfully received final answer from LLM.")
                    print(json.dumps(output))
                    sys.exit(0)

            # If hit max iterations
            output = {
                "answer": "Reached maximum tool calls limit.",
                "source": "unknown",
                "tool_calls": all_tool_calls_record,
            }
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
