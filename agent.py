#!/usr/bin/env python3
"""
Agent CLI - Call an LLM and get structured JSON responses.

Usage:
    uv run agent.py "Your question here"

Output:
    {"answer": "...", "tool_calls": []}
"""

import json
import sys
import os
from pathlib import Path

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


def call_llm(question: str, config: dict) -> str:
    """Call the LLM with a question and return the answer."""
    
    url = f"{config['api_base']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful coding assistant. Answer questions concisely and accurately."
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "temperature": 0.7,
    }
    
    try:
        print(f"[DEBUG] Calling LLM: {config['api_base']}", file=sys.stderr)
        print(f"[DEBUG] Model: {config['model']}", file=sys.stderr)
        print(f"[DEBUG] Question: {question}", file=sys.stderr)
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        response.raise_for_status()
        data = response.json()
        
        print(f"[DEBUG] API response status: {response.status_code}", file=sys.stderr)
        
        if "choices" not in data or len(data["choices"]) == 0:
            print("ERROR: Invalid API response structure", file=sys.stderr)
            sys.exit(1)
        
        answer = data["choices"][0]["message"]["content"]
        
        print(f"[DEBUG] Received answer ({len(answer)} chars)", file=sys.stderr)
        
        return answer
        
    except requests.exceptions.Timeout:
        print("ERROR: LLM request timed out (60s)", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: Connection failed: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP error: {e}", file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
        sys.exit(1)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"ERROR: Failed to parse LLM response: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    
    if len(sys.argv) < 2:
        print("ERROR: Please provide a question as argument", file=sys.stderr)
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    print(f"[DEBUG] Starting agent...", file=sys.stderr)
    
    # Load configuration
    config = load_config()
    
    # Call LLM
    answer = call_llm(question, config)
    
    # Build output
    output = {
        "answer": answer,
        "tool_calls": []
    }
    
    # Output to stdout (only valid JSON)
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
