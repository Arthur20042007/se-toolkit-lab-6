"""Regression test for Task 3: System data query"""

import subprocess
import json
import sys
import os


def test_data_query_question():
    """Test: 'How many items are in the database?'
    
    Expected: Uses query_api to call GET /items/ endpoint
    """
    question = "How many items are in the database?"
    
    # Set test environment variables (needed for query_api)
    env = os.environ.copy()
    env["LMS_API_KEY"] = "test_key"
    env["AGENT_API_BASE_URL"] = "http://localhost:42002"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        cwd="/Users/arthur/se-toolkit-lab-6",
        capture_output=True,
        text=True,
        timeout=70,
        env=env
    )
    
    if result.returncode != 0:
        print(f"ERROR: Agent exited with code {result.returncode}", file=sys.stderr)
        print(f"stderr: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON output: {e}", file=sys.stderr)
        print(f"stdout: {result.stdout}", file=sys.stderr)
        sys.exit(1)
    
    # Check structure
    assert "answer" in output, "Missing 'answer' field"
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "tool_calls must be list"
    
    # Check that query_api tool was used
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "query_api" in tool_names, f"Expected query_api tool, got {tool_names}"
    
    # Check answer is non-empty
    assert output["answer"].strip(), "Answer is empty"
    
    print("✓ Test passed: Data query uses query_api tool")


if __name__ == "__main__":
    test_data_query_question()
