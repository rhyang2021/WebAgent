# Multi-Agent System Architecture

## Overview

This is a new Multi-Agent System (MAS) implementation that replaces the previous single-agent approach. The system consists of a Controller agent that can make decisions and create SubAgents to execute specific tasks.

## Architecture

### Controller
- **Role**: Makes high-level decisions about how to approach tasks
- **Capabilities**: 
  - Can directly use only 3 tools: `search`, `visit`, `code`
  - Has access to all available tools for schema information
  - Can create SubAgents with specific tool sets
  - Maintains internal message history (`self.messages`)
- **Output Format**: Uses XML-like tags for structured responses

### SubAgent
- **Role**: Executes specific tasks assigned by the Controller
- **Capabilities**:
  - Can use any tools specified by the Controller
  - Maintains internal message history (`self.messages`)
  - Executes tasks in multiple rounds if needed
- **Output Format**: Uses XML-like tags for tool calls and answers

## Tag Format

### Controller Output
```xml
<think>
Reasoning about what needs to be done
</think>
<action>
One of: direct_answer | use_tools | create_subagents | completed
</action>
<content>
Content based on action type
</content>
```

### Tool Calls
```xml
<tool>
name: tool_name
args: {"parameter": "value"}
</tool>
```

### SubAgent Creation
```xml
<subagent>
role: Agent Role
task: Specific task description
tools: tool1,tool2,tool3
</subagent>
```

### SubAgent Output
```xml
<tool>
name: tool_name
args: {"parameter": "value"}
</tool>

<answer>
Final answer when task is complete
</answer>
```

## Key Features

1. **Internal Message Storage**: Both Controller and SubAgents maintain their own message history
2. **Tool Access Control**: Controller can only directly use 3 specific tools
3. **Dynamic SubAgent Creation**: Controller can create SubAgents with custom tool sets
4. **Structured Communication**: All communication uses XML-like tags for parsing

## Usage

### Basic Usage
```python
from agent import Controller
from tool_search import Search
from tool_visit import Visit
from tool_code import Code

# Create tools
tools = [Search(), Visit(), Code()]

# Create LLM wrapper
llm = SimpleLLM(model_path)

# Create controller
controller = Controller(tools, llm)

# Run task
result = run_mas("Your task here", llm, tools)
```

### Running the System
```bash
python run.py --task "What is the capital of France?" --rounds 5
```

### Testing
```bash
python test_agent.py
```

## File Structure

- `agent.py`: Contains Controller and SubAgent classes
- `prompt.py`: Contains system prompts for both agent types
- `run.py`: Main execution script
- `test_agent.py`: Test script for the system
- `tool_*.py`: Individual tool implementations

## Differences from Previous Version

1. **Replaced single agent with Controller + SubAgent system**
2. **Added internal message storage** for both agent types
3. **Changed tool call format** from JSON to XML-like tags
4. **Added tool access control** - Controller limited to 3 tools
5. **Moved tool usage and subagent creation** into Controller class
6. **Simplified run.py** - no more external message management

## Future Enhancements

1. Add more sophisticated SubAgent coordination
2. Implement SubAgent result caching
3. Add parallel SubAgent execution
4. Implement more sophisticated tool selection strategies
5. Add SubAgent performance monitoring