# Task 2 Implementation Plan: The Documentation Agent

## Overview

Transform the basic LLM CLI from Task 1 into an **agent with tools**. The agent will have:
- `read_file` tool to read project files
- `list_files` tool to discover files in directories
- An agentic loop that executes tools and feeds results back to the LLM
- System prompt that guides the LLM to use these tools to answer questions about the project

## Key Changes from Task 1

| Aspect | Task 1 | Task 2 |
|--------|--------|--------|
| Tools | None | `read_file`, `list_files` |
| LLM Messages | Question only | Question + tool definitions + loop |
| Output | `{answer, tool_calls}` | `{answer, source, tool_calls}` |
| Max Calls | 1 | 10 per question |
| Loop | No | Yes (agentic loop) |

## Architecture

```
Question
  ↓
LLM (with tool definitions)
  ↓
Does LLM respond with tool_calls?
  ├─ YES → Execute tool(s)
  │   ├─ Collect results
  │   ├─ Add to messages as "tool" role
  │   ├─ Add 1 to call counter
  │   └─ Loop back to LLM
  │
  └─ NO → Extract final answer
      ├─ Identify source reference
      └─ Return JSON {answer, source, tool_calls}
```

## Tool Definitions

### Tool 1: `read_file`

```python
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
                    "description": "Relative path from project root (e.g., wiki/git.md)"
                }
            },
            "required": ["path"]
        }
    }
}
```

**Implementation:**
- Accept path as parameter
- Validate path doesn't escape project directory (no `../` traversal)
- Read file contents
- Return file contents or error message

### Tool 2: `list_files`

```python
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
                    "description": "Directory path relative to project root (e.g., wiki)"
                }
            },
            "required": ["path"]
        }
    }
}
```

**Implementation:**
- Accept path as parameter
- Validate path doesn't escape project directory
- List directory contents
- Return newline-separated file/dir names

## System Prompt Strategy

The system prompt should:

1. **Tell the LLM it has tools** → "You have access to read_file and list_files tools"
2. **Guide tool usage** → "Use list_files to discover relevant files, then read_file to find the answer"
3. **Require source references** → "Always include the wiki file path in your answer (e.g., wiki/git.md#section-name)"
4. **Keep it focused** → Focus on answering questions about the project/code

Example:
```
You are a documentation assistant for a software engineering project.
You have access to:
- list_files(path): List files in a directory
- read_file(path): Read file contents

Use these tools to find and answer questions about the project.
Always cite your source: include the file path and section anchor (e.g., wiki/git.md#merging).
Be concise and accurate.
```

## Agentic Loop Implementation

### Pseudocode

```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": question}
]
tool_calls_made = []
max_iterations = 10

for iteration in range(max_iterations):
    response = call_llm(messages)
    
    if has_tool_calls(response):
        # Execute tools
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call.name, tool_call.args)
            tool_calls_made.append({
                "tool": tool_call.name,
                "args": tool_call.args,
                "result": result
            })
            # Add assistant message with tool use
            messages.append({"role": "assistant", "content": response.content})
            # Add tool result
            messages.append({
                "role": "user",  # or "tool" if supported
                "content": result
            })
    else:
        # No more tool calls - we have the final answer
        final_answer = response.content
        source = extract_source(final_answer)
        return {
            "answer": final_answer,
            "source": source,
            "tool_calls": tool_calls_made
        }

# Hit max iterations
return error or partial answer
```

## Security Considerations

### Path Traversal Prevention

Both tools must validate that the requested path:
1. Is relative (doesn't start with `/`)
2. Doesn't contain `..` (directory escape)
3. Resolves within the project root

**Implementation:**
```python
def validate_path(path):
    # Normalize path
    p = Path(path).resolve()
    # Check if within project root
    project_root = Path(__file__).parent.resolve()
    try:
        p.relative_to(project_root)
        return True
    except ValueError:
        return False  # Path is outside project root
```

## Output Format

Same as input to run_eval, with addition of `source` field:

```json
{
  "answer": "The answer text with source reference...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git.md\ngit-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git Workflow\n\n..."
    }
  ]
}
```

## Testing Strategy

### Test 1: Documentation Search with `read_file`
```python
def test_agent_documentation_search():
    # Question that requires reading a file
    question = "How do you resolve a merge conflict?"
    # Expected:
    # - Tool calls include at least one list_files + read_file
    # - Source includes "wiki/git-workflow.md" or similar
    # - Answer is relevant to merge conflicts
```

### Test 2: File Discovery with `list_files`
```python
def test_agent_list_files():
    # Question about what's available
    question = "What documentation files are available in the wiki?"
    # Expected:
    # - Tool calls include list_files
    # - Answer mentions wiki directory contents
```

## Dependencies

No new dependencies needed - all tools use stdlib `pathlib`.

## Files to Modify/Create

- ✅ `plans/task-2.md` - this file
- ✅ `agent.py` - add tools, agentic loop, system prompt
- ✅ `AGENT.md` - document tools and loop
- ✅ `tests/test_task2_*.py` - 2 new regression tests

## Acceptance Criteria Checklist

- [ ] `plans/task-2.md` exists with plan (committed before code)
- [ ] `agent.py` defines tool schemas for OpenAI API
- [ ] `agent.py` implements `read_file` tool
- [ ] `agent.py` implements `list_files` tool
- [ ] Agentic loop executes max 10 tool calls
- [ ] System prompt guides tool usage
- [ ] `source` field is populated in output
- [ ] Tool calls validated for path traversal
- [ ] `AGENT.md` updated with tools and loop docs
- [ ] 2 regression tests exist and pass
- [ ] Git workflow: issue → branch → PR with `Closes #6` → merge

## Timeline

- 15 min: Create plan ✓
- 20 min: Implement tools and agentic loop
- 10 min: Update documentation
- 15 min: Write and run tests
- 5 min: Git workflow

**Total: ~65 minutes**
