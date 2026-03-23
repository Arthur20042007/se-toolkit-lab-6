# Task 2 Plan: The Documentation Agent

## 1. Tool Schemas
We will implement two tools for the LLM to use: `read_file` and `list_files`.
- `list_files`:
  - Definition: Takes a `path` parameter.
  - Functionality: Lists files and directories in the specified path from the project root.
- `read_file`:
  - Definition: Takes a `path` parameter.
  - Functionality: Returns the content of the file.

We will define these using the standard OpenAI JSON schema format in the API request under the `tools` property.

## 2. Path Security
To prevent the LLM from accessing files outside the project directory, we will:
1. Resolve the absolute path of the workspace root (`os.path.abspath(os.getcwd())`).
2. Resolve the absolute path of the requested `path` (`os.path.abspath(os.path.join(root, path))`).
3. Ensure the newly resolved path strictly starts with the root path (`resolved.startswith(root)`). If it does not (e.g. they sent `../../etc/passwd`), we return an error message to the LLM.

## 3. Agentic Loop
We will implement a `while` loop (up to 10 iterations) inside `agent.py`:
1. The question and `tools` definitions are sent to the LLM. 
2. The system prompt will instruct the LLM:
   - "You are a specialized documentation agent."
   - "Use `list_files` to discover wiki files."
   - "Use `read_file` to find the exact answer."
   - "Provide a helpful, precise answer along with the source reference (e.g. `wiki/git-vscode.md#resolve-a-merge-conflict`)."
3. If the response contains `tool_calls`:
   - Append the assistant message with tool calls to the history.
   - For each tool call, execute the function safely and append the result as a new `role="tool"` message.
   - Continue the loop.
4. If there are no `tool_calls`, we assume it's the final answer.
5. Parse the final answer to extract the `answer` and the `source`. (We can instruct the LLM to output its final response in JSON format or we can use regex to parse if it is text. Alternatively, we could enforce JSON using tool calling or JSON mode. The simplest way is to ask the LLM to output exactly an object with `answer` and `source` when providing the final answer, or instruct it to provide the `source` separately so we can split it. However, the best way to reliably extract both `answer` and `source` is to force the LLM to act as a structured generator at the final step, or parse via format like `ANSWER: ... \n SOURCE: ...`. Let's use `ANSWER:` and `SOURCE:` parsing for simplicity.)

## 4. Final Output Construction
Once the final answer is obtained, construct the JSON dictionary containing:
- `answer` (parsed from LLM)
- `source` (parsed from LLM)
- `tool_calls` (a list recording every tool name, arguments, and string result that was executed)
and `json.dumps()` it to stdout.