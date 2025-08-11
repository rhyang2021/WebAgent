#!/usr/bin/env python3
"""
Test script for the new Multi-Agent System
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import Controller, SubAgent
from tool_search import Search
from tool_visit import Visit
from tool_code import Code


class MockLLM:
    """Mock LLM for testing"""
    
    def __init__(self):
        self.responses = [
            """<think>
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
</content>""",
            
            """<think>
I should create subagents to gather more detailed information.
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
</content>""",
            
            """<think>
I have enough information to provide an answer.
</think>
<action>
completed
</action>
<content>
The capital of France is Paris.
</content>"""
        ]
        self.response_index = 0
    
    def __call__(self, messages):
        if self.response_index < len(self.responses):
            response = self.responses[self.response_index]
            self.response_index += 1
            return response
        return "No more responses"


def test_controller():
    """Test Controller functionality"""
    print("Testing Controller...")
    
    # Create tools
    tools = [Search(), Visit(), Code()]
    
    # Create mock LLM
    llm = MockLLM()
    
    # Create controller
    controller = Controller(tools, llm)
    
    print(f"Controller tools: {[t.name for t in controller.controller_tools]}")
    print(f"All available tools: {[t.name for t in controller.all_tools]}")
    
    # Test step
    step = controller.step("What is the capital of France?")
    print(f"Step result: {step}")
    
    # Test tool usage
    result = controller.use_tool("search", {"query": ["test"]})
    print(f"Tool result: {result}")
    
    # Test subagent creation
    subagent = controller.create_subagent("Test Agent", "Test task", ["search"])
    print(f"Created subagent: {subagent.role}")
    
    print("Controller test completed!\n")


def test_subagent():
    """Test SubAgent functionality"""
    print("Testing SubAgent...")
    
    # Create tools
    tools = [Search(), Visit()]
    
    # Create mock LLM
    llm = MockLLM()
    
    # Create subagent
    subagent = SubAgent("Test Agent", "Test task", tools, llm)
    
    print(f"SubAgent tools: {[t.name for t in subagent.tools]}")
    
    # Test execution
    result = subagent.execute()
    print(f"Execution result: {result}")
    
    print("SubAgent test completed!\n")


def main():
    """Run all tests"""
    print("Starting Multi-Agent System tests...\n")
    
    try:
        test_controller()
        test_subagent()
        print("All tests completed successfully!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()