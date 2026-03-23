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
]

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
            
        with open(target_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

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

    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": "You are a specialized documentation agent. Use `list_files` to discover wiki files and `read_file` to find the exact answer to the user's question. Formulate a helpful and precise response, and YOU MUST output the final answer structured exactly as JSON using the following format: {\"answer\": \"Your final answer here\", \"source\": \"wiki/path-to-file.md#optional-anchor\"}. Always provide the source reference. Do not output anything other than the final JSON object.",
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
                    "response_format": {"type": "json_object"}
                }
                
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                message = data["choices"][0]["message"]
                
                if message.get("tool_calls"):
                    # Process tool calls
                    messages.append(message)
                    
                    for tool_call in message["tool_calls"]:
                        function_name = tool_call["function"]["name"]
                        try:
                            arguments = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            arguments = {}
                            
                        log_debug(f"Calling tool: {function_name} with args: {arguments}")
                        
                        tool_result = ""
                        if function_name == "list_files":
                            tool_result = list_files(arguments.get("path", ""))
                        elif function_name == "read_file":
                            tool_result = read_file(arguments.get("path", ""))
                        else:
                            tool_result = f"Error: Unknown tool {function_name}"
                            
                        # Record tool call for final output
                        all_tool_calls_record.append({
                            "tool": function_name,
                            "args": arguments,
                            "result": tool_result
                        })
                        
                        # Add tool response to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": str(tool_result)
                        })
                else:
                    # No tool calls, we have the final answer. Parse the JSON.
                    content = message.get("content", "")
                    try:
                        final_json = json.loads(content)
                        answer = final_json.get("answer", "")
                        source = final_json.get("source", "")
                    except json.JSONDecodeError:
                        answer = content
                        source = "unknown"
                        
                    output = {
                        "answer": answer.strip(),
                        "source": source,
                        "tool_calls": all_tool_calls_record
                    }
                    log_debug("Successfully received final answer from LLM.")
                    print(json.dumps(output))
                    sys.exit(0)
                    
            # If hit max iterations
            output = {
                "answer": "Reached maximum tool calls limit.",
                "source": "unknown",
                "tool_calls": all_tool_calls_record
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
