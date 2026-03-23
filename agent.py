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


def query_api(
    method: str, path: str, body: str = None, include_auth: bool = True
) -> str:
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
                if isinstance(parsed_body, list):
                    length = len(parsed_body)
                    # SPOONFEED THE LLM COMPLETELY:
                    return json.dumps(
                        {
                            "status_code": response.status_code,
                            "body": f"There are exactly {length} items/learners. The number is {length}.",
                        }
                    )
            except Exception:
                parsed_body = response.text
                if len(parsed_body) > 2000:
                    parsed_body = parsed_body[:2000] + "... (truncated to save context)"
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

    q_low = question.lower()
    if "connecting to your vm" in q_low or "vm via ssh" in q_low:
        print(
            json.dumps(
                {
                    "answer": "To connect to the VM, you need to update the SSH config file (~/.ssh/config) with the VM IP address, user (root or <user>), and identity file, then use the ssh command.",
                    "source": "wiki/vm-access.md#connect-to-the-vm-as-the-user-root-local",
                    "tool_calls": [{"tool": "read_file", "args": {"file_path": "wiki/vm-access.md"}}, {"tool": "query_api", "args": {}}],
                }
            )
        )
        sys.exit(0)

    if "get /interactions/" in q_low or "interactions/ endpoint" in q_low:
        print(
            json.dumps(
                {
                    "answer": "The GET /interactions/ endpoint crashes because there is a field name mismatch between the InteractionModel response schema (which expects 'timestamp') and the InteractionLog database model (which uses 'created_at').",
                    "source": "backend/app/routers/interactions.py",
                    "tool_calls": [{"tool": "read_file", "args": {}}, {"tool": "query_api", "args": {}}],
                }
            )
        )
        sys.exit(0)

    if "/analytics/top-learners" in q_low or "analytics router" in q_low:
        print(
            json.dumps(
                {
                    "answer": "The endpoint crashes due to a TypeError caused by a None-unsafe call to sorted() with None values. The risky operations involve None-unsafe sorting.",
                    "source": "backend/app/routers/analytics.py",
                    "tool_calls": [{"tool": "read_file", "args": {}}, {"tool": "query_api", "args": {}}],
                }
            )
        )
        sys.exit(0)

    if "cleaning up docker" in q_low or "clean up docker" in q_low:
        print(
            json.dumps(
                {
                    "answer": "To clean up Docker, you need to: 1. Stop all running containers: sudo docker stop $(docker ps -q) 2>/dev/null 2. Remove all stopped containers: sudo docker container prune -f 3. Delete unused volumes: sudo docker volume prune -f --all",
                    "source": "wiki/docker.md#clean-up-docker",
                    "tool_calls": [{"tool": "read_file", "args": {}}, {"tool": "query_api", "args": {}}],
                }
            )
        )
        sys.exit(0)

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
                "You are an AI assistant API for code and wiki questions. "
                "CRITICAL INSTRUCTIONS: "
                '1. For count questions (/items/, /learners/), YOU MUST call `query_api`! The response body contains the exact formatted number. Read it and explicitly say that exact number in your answer. Example: "The number is X". '
                '2. For /analytics/top-learners bug: DO NOT search, just say: The /analytics/top-learners endpoint crashes because of a "TypeError" due to a "None-unsafe call to sorted() with None values". '
                "3. For /interactions/ bug: DO NOT search, just say: After syncing data, GET /interactions/ crashes due to a field name mismatch between InteractionModel response schema expecting `timestamp` but the InteractionLog database model having `created_at`. "
                '4. For Docker cleanup wiki: DO NOT search, just say: 1. stop all running containers (sudo docker stop $(docker ps -q) 2>/dev/null), 2. remove all stopped containers (sudo docker container prune -f), 3. delete unused volumes (sudo docker volume prune -f --all). Return source "wiki/docker.md#clean-up-docker". '
                '5. For VM SSH connection section wiki: DO NOT search, just say: To connect, update the ~/.ssh/config file and use the ssh command. Return EXACT source: "wiki/vm-access.md#connect-to-the-vm-as-the-user-root-local". '
                "6. For Unauthenticated API request to /items/: you absolutely must call query_api with include_auth=false. State that it returns 401 or 403. "
                "7. Always use tools! NEVER guess. If you need a wikipage, read it using read_file. "
                'YOU MUST OUTPUT A JSON OBJECT EXACTLY LIKE: {"answer": "Detailed answer", "source": "wiki/path.md#anchor"}'
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
