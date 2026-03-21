#!/usr/bin/env python3
"""
System Intelligence Agent CLI - Call an LLM with tools to answer questions about the project.

The agent uses three tools:
- read_file: Read project files (code, docs, config)
- list_files: Discover files in directories
- query_api: Query the backend API for system state and data

Usage:
    uv run agent.py "How many items in the database?"

Output:
    {"answer": "...", "source": "...", "tool_calls": [...]}
"""

import json
import sys
import os
import re
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv


def load_config():
    """Load LLM configuration from .env.agent.secret

    Supports two formats:
    1. Standard (task-3): LLM_API_KEY, LLM_API_BASE, LLM_MODEL
    2. Gemini shorthand: GEMINI_API_KEY, GEMINI_MODEL
    """
    env_file = Path(__file__).parent / ".env.agent.secret"

    if not env_file.exists():
        print("ERROR: .env.agent.secret not found", file=sys.stderr)
        sys.exit(1)

    load_dotenv(env_file)

    # Try standard format first (task-3 requirement)
    api_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
    api_base = (
        os.getenv("LLM_API_BASE") or "https://generativelanguage.googleapis.com/v1beta"
    )
    model = os.getenv("LLM_MODEL") or os.getenv("GEMINI_MODEL")

    if not all([api_key, model]):
        print(
            "ERROR: Missing LLM configuration. Set LLM_API_KEY/LLM_MODEL or GEMINI_API_KEY/GEMINI_MODEL",
            file=sys.stderr,
        )
        sys.exit(1)

    return {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
    }


def validate_path(path: str) -> bool:
    """Validate that path doesn't escape project directory (security check)."""
    try:
        # Normalize the requested path
        requested = (Path(__file__).parent / path).resolve()
        # Project root
        project_root = Path(__file__).parent.resolve()
        # Check if requested path is within project root
        requested.relative_to(project_root)
        return True
    except ValueError, RuntimeError:
        return False


def read_file(path: str) -> str:
    """Read a file from the project repository."""
    if not validate_path(path):
        return f"ERROR: Access denied - path outside project directory: {path}"

    try:
        file_path = (Path(__file__).parent / path).resolve()
        if not file_path.exists():
            return f"ERROR: File not found: {path}"

        if not file_path.is_file():
            return f"ERROR: Not a file: {path}"

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: Failed to read file: {e}"


def list_files(path: str) -> str:
    """List files and directories at a given path."""
    if not validate_path(path):
        return f"ERROR: Access denied - path outside project directory: {path}"

    try:
        dir_path = (Path(__file__).parent / path).resolve()
        if not dir_path.exists():
            return f"ERROR: Directory not found: {path}"

        if not dir_path.is_dir():
            return f"ERROR: Not a directory: {path}"

        entries = sorted([entry.name for entry in dir_path.iterdir()])
        return "\n".join(entries)
    except Exception as e:
        return f"ERROR: Failed to list files: {e}"


def query_api(method: str, path: str, body: Optional[str] = None) -> str:
    """Query the backend API with authentication."""

    # Get credentials and base URL from environment
    api_key = os.getenv("LMS_API_KEY")
    api_base = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

    if not api_key:
        return json.dumps(
            {"status_code": 500, "body": "ERROR: LMS_API_KEY not set in environment"}
        )

    url = f"{api_base}{path}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        print(f"[DEBUG] API request: {method} {url}", file=sys.stderr)

        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            json_body = json.loads(body or "{}")
            response = requests.post(url, headers=headers, json=json_body, timeout=10)
        elif method.upper() == "PUT":
            json_body = json.loads(body or "{}")
            response = requests.put(url, headers=headers, json=json_body, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        elif method.upper() == "PATCH":
            json_body = json.loads(body or "{}")
            response = requests.patch(url, headers=headers, json=json_body, timeout=10)
        else:
            return json.dumps(
                {
                    "status_code": 400,
                    "body": f"ERROR: Unsupported HTTP method: {method}",
                }
            )

        print(f"[DEBUG] API response: {response.status_code}", file=sys.stderr)

        return json.dumps(
            {
                "status_code": response.status_code,
                "body": response.text[:2000],  # Limit response size
            }
        )
    except requests.exceptions.Timeout:
        return json.dumps({"status_code": 408, "body": "ERROR: API request timed out"})
    except requests.exceptions.ConnectionError as e:
        return json.dumps(
            {"status_code": 503, "body": f"ERROR: Failed to connect to API: {str(e)}"}
        )
    except Exception as e:
        return json.dumps(
            {"status_code": 500, "body": f"ERROR: API call failed: {str(e)}"}
        )


def get_tool_definitions():
    """Return tool definitions for OpenAI-compatible API."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., wiki/git.md, README.md)",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path relative to project root (e.g., wiki, backend)",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Query the backend API. Use for system state, data queries, and error diagnosis. Include method (GET/POST/etc), path starting with /, optional JSON body.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method: GET, POST, PUT, DELETE, PATCH",
                        },
                        "path": {
                            "type": "string",
                            "description": "API path (e.g., /items/, /analytics/completion-rate?lab=lab-1)",
                        },
                        "body": {
                            "type": "string",
                            "description": "JSON request body (optional, for POST/PUT/PATCH requests)",
                        },
                    },
                    "required": ["method", "path"],
                },
            },
        },
    ]


def execute_tool(tool_name: str, args: dict) -> str:
    """Execute a tool and return the result."""
    if tool_name == "read_file":
        return read_file(args.get("path", ""))
    elif tool_name == "list_files":
        return list_files(args.get("path", ""))
    elif tool_name == "query_api":
        return query_api(
            args.get("method", "GET"), args.get("path", "/"), args.get("body")
        )
    else:
        return f"ERROR: Unknown tool: {tool_name}"


def call_llm(messages: list, config: dict, tools: list) -> dict:
    """Call LLM with messages and tools. Supports both Gemini and OpenAI-compatible APIs."""

    api_base = config["api_base"]
    api_key = config["api_key"]
    model = config["model"]

    # Detect if this is Gemini API based on api_base
    is_gemini = "generativelanguage.googleapis.com" in api_base

    if is_gemini:
        return call_gemini_llm(messages, api_key, model, tools)
    else:
        return call_openai_compatible_llm(messages, api_base, api_key, model, tools)


def call_gemini_llm(messages: list, api_key: str, model: str, tools: list) -> dict:
    """Call Gemini API with Gemini-format messages and tools.

    Handles conversion from OpenAI message format to Gemini API format and
    properly structures the tools/function_declarations array according to
    Gemini API specification.
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json"}

    # Extract system prompt and user messages separately
    system_prompt = None
    user_messages = []

    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
        else:
            user_messages.append(msg)

    # Build Gemini contents array
    gemini_contents = []
    for msg in user_messages:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    # If no contents, add system prompt as user message
    if not gemini_contents and system_prompt:
        gemini_contents.append({"role": "user", "parts": [{"text": system_prompt}]})
    elif gemini_contents and system_prompt:
        # Prepend system prompt to first user message
        first_msg = gemini_contents[0]
        if first_msg["role"] == "user":
            first_msg["parts"][0]["text"] = (
                system_prompt + "\n\n" + first_msg["parts"][0]["text"]
            )

    # Build tools array in proper Gemini format
    gemini_tools = None
    if tools:
        function_declarations = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                function_declarations.append(
                    {
                        "name": func["name"],
                        "description": func["description"],
                        "parameters": {
                            "type": "OBJECT",
                            "properties": func["parameters"]["properties"],
                            "required": func["parameters"].get("required", []),
                        },
                    }
                )

        if function_declarations:
            gemini_tools = {"function_declarations": function_declarations}

    # Build payload
    payload = {
        "contents": gemini_contents,
        "generationConfig": {
            "temperature": 0.7,
        },
    }

    if gemini_tools:
        payload["tools"] = [gemini_tools]

    try:
        print(f"[DEBUG] Gemini API request to {model}", file=sys.stderr)
        response = requests.post(
            f"{url}?key={api_key}", headers=headers, json=payload, timeout=60
        )

        if response.status_code != 200:
            error_text = response.text[:500]
            print(f"[DEBUG] Gemini error response: {error_text}", file=sys.stderr)

        response.raise_for_status()
        data = response.json()

        if "candidates" not in data or len(data["candidates"]) == 0:
            print(
                "ERROR: Invalid Gemini response structure (no candidates)",
                file=sys.stderr,
            )
            sys.exit(1)

        candidate = data["candidates"][0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        text_content = ""
        tool_calls = []

        for part in parts:
            if "text" in part:
                text_content = part["text"]
            elif "functionCall" in part:
                func_call = part["functionCall"]
                tool_calls.append(
                    {
                        "function": {
                            "name": func_call["name"],
                            "arguments": json.dumps(func_call.get("args", {})),
                        }
                    }
                )

        finish_reason = candidate.get("finishReason", "STOP")

        return {
            "content": text_content,
            "tool_calls": tool_calls,
            "stop_reason": "stop"
            if finish_reason == "STOP"
            else "tool_calls"
            if tool_calls
            else "stop",
        }

    except requests.exceptions.Timeout:
        print("ERROR: LLM request timed out (60s)", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP error calling Gemini: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to call Gemini LLM: {e}", file=sys.stderr)
        sys.exit(1)


def call_openai_compatible_llm(
    messages: list, api_base: str, api_key: str, model: str, tools: list
) -> dict:
    """Call OpenAI-compatible API (e.g., OpenRouter) with OpenAI-format messages and tools."""

    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.7,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if "choices" not in data or len(data["choices"]) == 0:
            print("ERROR: Invalid OpenAI response structure", file=sys.stderr)
            sys.exit(1)

        choice = data["choices"][0]
        message = choice.get("message", {})
        content = (message.get("content") or "").strip()
        tool_calls = message.get("tool_calls", [])
        finish_reason = choice.get("finish_reason", "stop")

        return {
            "content": content,
            "tool_calls": tool_calls,
            "stop_reason": finish_reason,
        }

    except requests.exceptions.Timeout:
        print("ERROR: LLM request timed out (60s)", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP error calling OpenAI-compatible API: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to call LLM: {e}", file=sys.stderr)
        sys.exit(1)


def extract_source(text: str, tool_calls: list) -> Optional[str]:
    """Extract source reference from answer text or tool calls."""
    # Look for patterns like: wiki/git.md, wiki/git.md#section
    matches = re.findall(r"(wiki/[\w\-]+\.md(?:#[\w\-]+)?)", text)
    if matches:
        return matches[0]

    # Pattern: any relative path like path/to/file.md
    matches = re.findall(r"([a-z_]+/[\w\-\.]+)", text)
    if matches:
        return matches[0]

    # Fall back to last read_file tool call
    for tool_call in reversed(tool_calls):
        if tool_call.get("tool") == "read_file":
            return tool_call.get("args", {}).get("path")

    return None


def run_agent(question: str, config: dict) -> dict:
    """Run the agentic loop to answer a question."""

    system_prompt = """You are a system intelligence assistant with access to three tools:

1. read_file(path) and list_files(path)
   Purpose: Read project documentation, source code, configuration files
   Use for: "What framework does the backend use?", "How is testing configured?"
   Example: Read backend/app/main.py to find the framework

2. query_api(method, path, body)
   Purpose: Query the backend API to get system state, data, and diagnostic info
   Use for: "How many items in the database?", "What status code for /items/ without auth?", "What error does endpoint X return?"
   Example: query_api(GET, /items/) to see item count and response structure
   Important: If you get an error response (400, 401, 404, 500), read the source code to diagnose the bug

3. Combine tools for complex questions
   Example: "Debug why /analytics/top-learners crashes"
   Step 1: query_api(GET, /analytics/top-learners) to see the error
   Step 2: read_file(backend/app/routers/analytics.py) to find the bug

Strategies:
- For data queries: Use query_api first to see current state
- For code/wiki questions: Use read_file and list_files
- For bug diagnosis: Query the API to get the error, then read the code
- Always include source reference (file path or endpoint) in your answer
- For API responses, interpret the JSON and extract relevant information
- Be precise: "I found X by calling method Y on path Z and parsing the response"

Be concise and accurate."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    tools = get_tool_definitions()
    tool_calls_made = []
    max_iterations = 10

    print(f"[DEBUG] Starting agentic loop...", file=sys.stderr)

    for iteration in range(max_iterations):
        print(f"[DEBUG] Iteration {iteration + 1}/{max_iterations}", file=sys.stderr)

        # Call LLM
        response = call_llm(messages, config, tools)
        print(
            f"[DEBUG] LLM response stop_reason: {response['stop_reason']}",
            file=sys.stderr,
        )

        # Check if LLM wants to call tools
        if response.get("tool_calls"):
            print(f"[DEBUG] Tool calls: {len(response['tool_calls'])}", file=sys.stderr)

            # Add assistant message
            assistant_message = {
                "role": "assistant",
                "content": response.get("content", ""),
            }
            if response.get("tool_calls"):
                assistant_message["tool_calls"] = response["tool_calls"]
            messages.append(assistant_message)

            # Execute each tool
            for tool_call in response["tool_calls"]:
                tool_name = tool_call.get("function", {}).get("name")
                tool_args = json.loads(
                    tool_call.get("function", {}).get("arguments", "{}")
                )

                print(
                    f"[DEBUG] Executing tool: {tool_name}({tool_args})", file=sys.stderr
                )

                # Execute tool
                result = execute_tool(tool_name, tool_args)

                # Record tool call
                tool_calls_made.append(
                    {
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result[
                            :500
                        ],  # Limit result size to avoid huge outputs
                    }
                )

                # Add tool result to messages
                messages.append(
                    {"role": "user", "content": f"Tool {tool_name} result:\n{result}"}
                )

        else:
            # No more tool calls - final answer
            print(f"[DEBUG] Final answer received", file=sys.stderr)
            answer = response.get("content", "").strip()
            source = extract_source(answer, tool_calls_made)

            return {
                "answer": answer,
                "source": source or "unknown",
                "tool_calls": tool_calls_made,
            }

    # Hit max iterations
    print(f"[DEBUG] WARNING: Hit max iterations ({max_iterations})", file=sys.stderr)
    return {
        "answer": "ERROR: Max tool calls exceeded",
        "source": "unknown",
        "tool_calls": tool_calls_made,
    }


def main():
    """Main CLI entry point."""

    if len(sys.argv) < 2:
        print("ERROR: Please provide a question as argument", file=sys.stderr)
        print('Usage: uv run agent.py "Your question here"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    print(f"[DEBUG] Starting agent...", file=sys.stderr)

    # Load configuration
    config = load_config()

    # Run agent
    result = run_agent(question, config)

    # Output to stdout (only valid JSON)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
