#!/usr/bin/env python3
"""
Example usage of the new Multi-Agent System
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import Controller, SubAgent
from tool_search import Search
from tool_visit import Visit
from tool_code import Code


class ExampleLLM:
    """Example LLM implementation"""
    
    def __init__(self):
        self.conversation_history = []
    
    def __call__(self, messages):
        """Simple LLM that responds based on the last message"""
        if not messages:
            return "No messages provided"
        
        last_message = messages[-1]["content"]
        
        # Simple response logic for demonstration
        if "capital of France" in last_message.lower():
            return """<think>
I need to search for information about France's capital.
</think>
<action>
use_tools
</action>
<content>
<tool>
name: search
args: {"query": ["capital of France", "France capital city"]}
</tool>
</content>"""
        
        elif "create subagent" in last_message.lower():
            return """<think>
I should create a subagent to gather more detailed information.
</think>
<action>
create_subagents
</action>
<content>
<subagent>
role: Research Agent
task: search for information about Paris
tools: search,visit
</subagent>
</content>"""
        
        elif "subagent" in last_message.lower():
            return """<think>
I am a subagent and need to execute my task.
</think>
<tool>
name: search
args: {"query": ["Paris information", "Paris facts"]}
</tool>
<answer>
Paris is the capital and largest city of France, known for its art, fashion, gastronomy and culture.
</answer>"""
        
        else:
            return """<think>
I need to provide a direct answer.
</think>
<action>
direct_answer
</action>
<content>
I can help you with that. Let me search for more information.
</content>"""


def example_controller_usage():
    """Example of using the Controller"""
    print("=== Controller Example ===")
    
    # Create tools
    tools = [Search(), Visit(), Code()]
    
    # Create LLM
    llm = ExampleLLM()
    
    # Create controller
    controller = Controller(tools, llm)
    
    print(f"Available tools: {[t.name for t in controller.all_tools]}")
    print(f"Controller can use: {[t.name for t in controller.controller_tools]}")
    
    # Controller makes a decision
    step = controller.step("What is the capital of France?")
    print(f"\nController step:")
    print(f"Think: {step['think']}")
    print(f"Action: {step['action']}")
    print(f"Content: {step['content']}")
    
    # Controller uses a tool
    if step['action'] == 'use_tools':
        print("\nController using tool...")
        # Parse tool calls
        tool_calls = controller._extract_tools(step['content'])
        for tool_call in tool_calls:
            print(f"Tool: {tool_call['name']}, Args: {tool_call['args']}")
    
    # Controller creates subagents
    elif step['action'] == 'create_subagents':
        print("\nController creating subagents...")
        subagent_specs = controller._extract_subagents(step['content'])
        for spec in subagent_specs:
            print(f"Role: {spec['role']}, Task: {spec['task']}, Tools: {spec['tools']}")
            
            # Create and run subagent
            subagent = controller.create_subagent(spec['role'], spec['task'], spec['tools'])
            result = subagent.execute()
            print(f"Subagent result: {result}")
    
    print("\nController example completed!")


def example_subagent_usage():
    """Example of using a SubAgent directly"""
    print("\n=== SubAgent Example ===")
    
    # Create tools
    tools = [Search(), Visit()]
    
    # Create LLM
    llm = ExampleLLM()
    
    # Create subagent
    subagent = SubAgent("Research Agent", "Find information about Paris", tools, llm)
    
    print(f"SubAgent role: {subagent.role}")
    print(f"SubAgent task: {subagent.task}")
    print(f"SubAgent tools: {[t.name for t in subagent.tools]}")
    
    # Execute task
    result = subagent.execute()
    print(f"\nSubAgent execution result: {result}")
    
    print("\nSubAgent example completed!")


def main():
    """Run examples"""
    print("Multi-Agent System Examples")
    print("=" * 50)
    
    try:
        example_controller_usage()
        example_subagent_usage()
        print("\nAll examples completed successfully!")
    except Exception as e:
        print(f"Example failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()