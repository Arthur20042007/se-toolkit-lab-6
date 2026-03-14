"""
Regression test for Task 2: Documentation Agent - read_file tool

Verifies:
1. Agent can read documentation files
2. Output is valid JSON with answer, source, and tool_calls
3. read_file tool is called
4. Source field contains the file path that was read
5. Answer contains relevant information from the file
"""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_read_file():
    """Test that agent uses read_file tool to answer documentation questions."""
    
    project_root = Path(__file__).parent.parent
    agent_file = project_root / "agent.py"
    
    assert agent_file.exists(), f"agent.py not found at {agent_file}"
    
    # Question that should trigger read_file tool
    question = "What is git and how is it used in this project?"
    
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
    
    # Verify source contains a file path (wiki/...)
    assert output["source"] != "unknown", f"source should not be 'unknown', got: {output['source']}"
    assert "/" in output["source"], f"source should be a file path, got: {output['source']}"
    
    # Verify read_file tool was called at least once
    assert any(tc.get("tool") == "read_file" for tc in output["tool_calls"]), \
        f"Expected read_file tool call, got: {[tc.get('tool') for tc in output['tool_calls']]}"
    
    # Verify the source file path appears in the tool calls
    tool_files = [tc.get("args", {}).get("path") for tc in output["tool_calls"] if tc.get("tool") == "read_file"]
    assert tool_files, "No read_file calls found"
    
    print(f"✅ Test passed!")
    print(f"   Tool calls: {len(output['tool_calls'])}")
    print(f"   Tools used: {[tc.get('tool') for tc in output['tool_calls']]}")
    print(f"   Source: {output['source']}")
    print(f"   Files read: {tool_files}")


if __name__ == "__main__":
    test_agent_read_file()
