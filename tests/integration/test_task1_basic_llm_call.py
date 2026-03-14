"""
Regression test for Task 1: Basic LLM call

Verifies:
1. agent.py runs successfully
2. Output is valid JSON
3. JSON contains required fields: answer, tool_calls
4. answer field is non-empty
5. tool_calls is an empty list
"""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_basic_call():
    """Test that agent.py produces valid JSON output with required fields."""
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    agent_file = project_root / "agent.py"
    
    assert agent_file.exists(), f"agent.py not found at {agent_file}"
    
    # Run agent with a simple question
    question = "What is 2+2?"
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--version"],  # Just check if pytest works
        capture_output=True,
        text=True,
        cwd=project_root
    )
    
    # Run the actual agent
    result = subprocess.run(
        [sys.executable, str(agent_file), question],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=70
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
    
    # Verify field types
    assert isinstance(output["answer"], str), f"answer should be string, got {type(output['answer'])}"
    assert isinstance(output["tool_calls"], list), f"tool_calls should be list, got {type(output['tool_calls'])}"
    
    # Verify answer is not empty
    assert len(output["answer"]) > 0, "answer field is empty"
    
    # Verify tool_calls is empty (no tools yet)
    assert len(output["tool_calls"]) == 0, f"tool_calls should be empty, got {output['tool_calls']}"
    
    print(f"✅ Test passed!")
    print(f"   Question: {question}")
    print(f"   Answer: {output['answer'][:100]}...")
    print(f"   Tool calls: {len(output['tool_calls'])}")


if __name__ == "__main__":
    test_agent_basic_call()
