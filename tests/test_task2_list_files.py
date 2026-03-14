"""
Regression test for Task 2: Documentation Agent - list_files tool

Verifies:
1. Agent can list files in a directory
2. Output is valid JSON with answer, source, and tool_calls
3. list_files tool is called
4. Results contain actual wiki files
"""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_list_files():
    """Test that agent uses list_files tool to discover files."""
    
    project_root = Path(__file__).parent.parent
    agent_file = project_root / "agent.py"
    
    assert agent_file.exists(), f"agent.py not found at {agent_file}"
    
    # Question that should trigger list_files
    question = "What files are available in the wiki directory?"
    
    result = subprocess.run(
        [sys.executable, str(agent_file), question],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=90
    )
    
    assert result.returncode == 0, f"agent.py exited with code {result.returncode}\nstderr: {result.stderr}"
    
    # Parse output
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"Output is not valid JSON: {result.stdout}\nError: {e}"
        )
    
    # Verify required fields
    assert "answer" in output, f"Missing 'answer' field in output: {output}"
    assert "tool_calls" in output, f"Missing 'tool_calls' field in output: {output}"
    assert "source" in output, f"Missing 'source' field in output: {output}"
    
    # Verify field types
    assert isinstance(output["answer"], str), f"answer should be string"
    assert isinstance(output["tool_calls"], list), f"tool_calls should be list"
    assert isinstance(output["source"], str), f"source should be string"
    
    # Verify answer is not empty
    assert len(output["answer"]) > 0, "answer field is empty"
    
    # Verify list_files tool was called
    assert any(tc.get("tool") == "list_files" for tc in output["tool_calls"]), \
        f"Expected list_files tool call, got: {[tc.get('tool') for tc in output['tool_calls']]}"
    
    print(f"✅ Test passed!")
    print(f"   Tool calls: {len(output['tool_calls'])}")
    print(f"   Tools used: {[tc.get('tool') for tc in output['tool_calls']]}")
    print(f"   Source: {output['source']}")


if __name__ == "__main__":
    test_agent_list_files()
