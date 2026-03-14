#!/usr/bin/env python3
"""
Documentation Agent CLI - Call an LLM with tools to answer questions about the project.

The agent uses:
- read_file: Read project files
- list_files: Discover files in directories

Usage:
    uv run agent.py "How do you resolve a merge conflict?"

Output:
    {"answer": "...", "source": "wiki/git-workflow.md#...", "tool_calls": [...]}
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
    """Load LLM configuration from .env.agent.secret"""
    env_file = Path(__file__).parent / ".env.agent.secret"

    if not env_file.exists():
        print("ERROR: .env.agent.secret not found", file=sys.stderr)
        sys.exit(1)

    load_dotenv(env_file)

    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    if not all([api_key, api_base, model]):
        print("ERROR: Missing LLM configuration in .env.agent.secret", file=sys.stderr)
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
    except (ValueError, RuntimeError):
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
        
        with open(file_path, 'r', encoding='utf-8') as f:
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
                            "description": "Relative path from project root (e.g., wiki/git.md, README.md)"
                        }
                    },
                    "required": ["path"]
                }
            }
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
                            "description": "Directory path relative to project root (e.g., wiki, backend)"
                        }
                    },
                    "required": ["path"]
                }
            }
        }
    ]


def execute_tool(tool_name: str, args: dict) -> str:
    """Execute a tool and return the result."""
    if tool_name == "read_file":
        return read_file(args.get("path", ""))
    elif tool_name == "list_files":
        return list_files(args.get("path", ""))
    else:
        return f"ERROR: Unknown tool: {tool_name}"


def call_llm(messages: list, config: dict, tools: list) -> dict:
    """Call the LLM with messages and tools, return parsed response."""
    
    url = f"{config['api_base']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config["model"],
        "messages": messages,
        "tools": tools,
        "temperature": 0.7,
        "tool_choice": "auto",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if "choices" not in data or len(data["choices"]) == 0:
            print("ERROR: Invalid API response structure", file=sys.stderr)
            sys.exit(1)

        choice = data["choices"][0]
        message = choice["message"]
        
        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls", []),
            "stop_reason": choice.get("finish_reason", "")
        }

    except requests.exceptions.Timeout:
        print("ERROR: LLM request timed out (60s)", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to call LLM: {e}", file=sys.stderr)
        sys.exit(1)


def extract_source(text: str, tool_calls: list) -> Optional[str]:
    """Extract source reference from answer text or tool calls."""
    # Look for patterns like: wiki/git.md, wiki/git.md#section
    matches = re.findall(r'(wiki/[\w\-]+\.md(?:#[\w\-]+)?)', text)
    if matches:
        return matches[0]
    
    # Pattern: any relative path like path/to/file.md
    matches = re.findall(r'([a-z_]+/[\w\-\.]+)', text)
    if matches:
        return matches[0]
    
    # Fall back to last read_file tool call
    for tool_call in reversed(tool_calls):
        if tool_call.get("tool") == "read_file":
            return tool_call.get("args", {}).get("path")
    
    return None


def run_agent(question: str, config: dict) -> dict:
    """Run the agentic loop to answer a question."""
    
    system_prompt = """You are a documentation assistant for a software engineering project.

You have access to two tools:
- read_file(path): Read a file from the project (e.g., wiki/git.md, README.md)
- list_files(path): List files in a directory (e.g., wiki, backend)

Your task is to answer questions about the project by:
1. Using list_files to discover relevant documentation files
2. Using read_file to find the actual information
3. Including the source file path in your answer

Be concise, accurate, and always include the source file reference."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tools = get_tool_definitions()
    tool_calls_made = []
    max_iterations = 10

    print(f"[DEBUG] Starting agentic loop...", file=sys.stderr)

    for iteration in range(max_iterations):
        print(f"[DEBUG] Iteration {iteration + 1}/{max_iterations}", file=sys.stderr)

        # Call LLM
        response = call_llm(messages, config, tools)
        print(f"[DEBUG] LLM response stop_reason: {response['stop_reason']}", file=sys.stderr)

        # Check if LLM wants to call tools
        if response.get("tool_calls"):
            print(f"[DEBUG] Tool calls: {len(response['tool_calls'])}", file=sys.stderr)
            
            # Add assistant message
            assistant_message = {"role": "assistant", "content": response.get("content", "")}
            if response.get("tool_calls"):
                assistant_message["tool_calls"] = response["tool_calls"]
            messages.append(assistant_message)

            # Execute each tool
            for tool_call in response["tool_calls"]:
                tool_name = tool_call.get("function", {}).get("name")
                tool_args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                
                print(f"[DEBUG] Executing tool: {tool_name}({tool_args})", file=sys.stderr)
                
                # Execute tool
                result = execute_tool(tool_name, tool_args)
                
                # Record tool call
                tool_calls_made.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result[:500]  # Limit result size to avoid huge outputs
                })
                
                # Add tool result to messages
                messages.append({
                    "role": "user",
                    "content": f"Tool {tool_name} result:\n{result}"
                })

        else:
            # No more tool calls - final answer
            print(f"[DEBUG] Final answer received", file=sys.stderr)
            answer = response.get("content", "").strip()
            source = extract_source(answer, tool_calls_made)
            
            return {
                "answer": answer,
                "source": source or "unknown",
                "tool_calls": tool_calls_made
            }

    # Hit max iterations
    print(f"[DEBUG] WARNING: Hit max iterations ({max_iterations})", file=sys.stderr)
    return {
        "answer": "ERROR: Max tool calls exceeded",
        "source": "unknown",
        "tool_calls": tool_calls_made
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
