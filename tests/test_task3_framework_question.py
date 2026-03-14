"""Regression test for Task 3: System facts query"""

import subprocess
import json
import sys


def test_framework_question():
    """Test: 'What Python framework does backend use?'
    
    Expected: Uses read_file to find FastAPI in backend/app/main.py
    """
    question = "What Python framework does the backend use?"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        cwd="/Users/arthur/se-toolkit-lab-6",
        capture_output=True,
        text=True,
        timeout=70
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
    
    # Check that at least one read_file tool was used
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "read_file" in tool_names, f"Expected read_file tool, got {tool_names}"
    
    # Check answer is non-empty
    assert output["answer"].strip(), "Answer is empty"
    
    print("✓ Test passed: Framework question uses read_file tool")


if __name__ == "__main__":
    test_framework_question()
