#!/usr/bin/env python3
"""
Modified Agent Runner with Internal Message History
"""

import sys
import os
import json
from typing import List, Dict, Any

# Import the modified agent classes
from agent import Controller, SubAgent
from prompt_base import get_enhanced_controller_prompt

# Mock tool classes for demonstration
class SearchTool:
    def __init__(self):
        self.name = "search"
        self.description = "Search for information on the web"
        self.parameters = {"query": {"type": "string", "description": "Search query"}}
    
    def call(self, **kwargs):
        query = kwargs.get("query", "")
        return f"Search results for: {query}\n[Mock search results...]"

class VisitTool:
    def __init__(self):
        self.name = "visit"
        self.description = "Visit a specific URL and extract content"
        self.parameters = {"url": {"type": "string", "description": "URL to visit"}}
    
    def call(self, **kwargs):
        url = kwargs.get("url", "")
        return f"Content from {url}:\n[Mock page content...]"

class CodeTool:
    def __init__(self):
        self.name = "code"
        self.description = "Generate or analyze code"
        self.parameters = {"task": {"type": "string", "description": "Coding task"}}
    
    def call(self, **kwargs):
        task = kwargs.get("task", "")
        return f"Code for task '{task}':\n```python\n# Mock generated code\nprint('Hello, World!')\n```"

class AnalyzeTool:
    def __init__(self):
        self.name = "analyze"
        self.description = "Analyze data or content"
        self.parameters = {"content": {"type": "string", "description": "Content to analyze"}}
    
    def call(self, **kwargs):
        content = kwargs.get("content", "")
        return f"Analysis of content:\n[Mock analysis results...]"

class SummarizeTool:
    def __init__(self):
        self.name = "summarize"
        self.description = "Summarize long text or content"
        self.parameters = {"text": {"type": "string", "description": "Text to summarize"}}
    
    def call(self, **kwargs):
        text = kwargs.get("text", "")
        return f"Summary: [Mock summary of the provided text...]"


def create_llm_config():
    """Create LLM configuration"""
    return {
        'model': "/apdcephfs_cq11/share_1567347/share_info/rhyang/huggingface_models/models--Alibaba-NLP--WebSailor-3B/snapshots/b317a15261674d83d851f0a14761840583bb9dce",
        'api_key': 'EMPTY',
        'model_server': 'http://11.216.48.78:8032/v1',
        'temperature': 0.6,
        'generate_cfg': {
            'temperature': 0.6,
            'top_p': 0.95
        }
    }


def run_agent_system(task: str, max_rounds: int = 10):
    """Run the modified agent system"""
    
    # Initialize all available tools
    all_tools = [
        SearchTool(),
        VisitTool(), 
        CodeTool(),
        AnalyzeTool(),
        SummarizeTool()
    ]
    
    # Create LLM configuration
    llm_cfg = create_llm_config()
    
    # Create Controller with all tools (but only search, visit, code for direct use)
    controller = Controller(all_tools, llm_cfg)
    
    print(f"\n{'='*60}")
    print(f"Task: {task}")
    print(f"{'='*60}")
    
    round_num = 0
    while round_num < max_rounds:
        round_num += 1
        print(f"\n--- Round {round_num} ---")
        
        # Get next action from controller
        if round_num == 1:
            # First round - provide the task
            step_result = controller.step(task)
        else:
            # Subsequent rounds - let controller continue based on history
            step_result = controller.step("Continue based on previous results or provide final answer.")
        
        response = step_result.get('response', '')
        result = step_result.get('result', {})
        
        print(f"Controller Response: {response[:200]}...")
        print(f"Action Type: {result.get('type', 'unknown')}")
        
        # Handle different result types
        if result.get('type') == 'answer':
            print(f"\nFINAL ANSWER:")
            print(result.get('content', ''))
            break
            
        elif result.get('type') == 'tool_result':
            print(f"Tool Result: {result.get('content', '')[:100]}...")
            
        elif result.get('type') == 'subagent_result':
            print(f"SubAgent ({result.get('role', 'Unknown')}) Result: {result.get('content', '')[:100]}...")
            
        elif result.get('type') == 'error':
            print(f"Error: {result.get('content', '')}")
            
        # Check if we should continue
        if '<answer>' in response:
            break
            
        # Prevent infinite loops
        if round_num >= max_rounds:
            print(f"\nMax rounds ({max_rounds}) reached. Stopping.")
            break
    
    print(f"\n{'='*60}")
    print("Agent System Execution Complete")
    print(f"Total Rounds: {round_num}")
    print(f"Final Message History Length: {len(controller.messages)}")
    print(f"{'='*60}")
    
    return controller.messages


def demo_scenarios():
    """Run demonstration scenarios"""
    
    scenarios = [
        {
            "name": "Simple Search Task",
            "task": "Find information about Python web scraping libraries and recommend the best one.",
            "max_rounds": 5
        },
        {
            "name": "Complex Research Task", 
            "task": "Research the latest developments in AI language models, compare their capabilities, and provide a comprehensive analysis.",
            "max_rounds": 8
        },
        {
            "name": "Multi-Step Coding Task",
            "task": "Create a Python script that scrapes weather data from a website and generates a daily weather report.",
            "max_rounds": 6
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{'#'*80}")
        print(f"DEMO SCENARIO: {scenario['name']}")
        print(f"{'#'*80}")
        
        try:
            run_agent_system(scenario['task'], scenario['max_rounds'])
        except Exception as e:
            print(f"Error in scenario '{scenario['name']}': {str(e)}")
        
        print(f"\n{'#'*80}")
        print(f"END OF SCENARIO: {scenario['name']}")
        print(f"{'#'*80}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the modified agent system")
    parser.add_argument("--task", type=str, help="Task to execute")
    parser.add_argument("--rounds", type=int, default=10, help="Maximum number of rounds")
    parser.add_argument("--demo", action="store_true", help="Run demonstration scenarios")
    
    args = parser.parse_args()
    
    if args.demo:
        demo_scenarios()
    elif args.task:
        run_agent_system(args.task, args.rounds)
    else:
        # Interactive mode
        print("Interactive Agent System")
        print("Type 'quit' to exit, 'demo' to run demonstrations")
        
        while True:
            try:
                user_input = input("\nEnter task: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    break
                elif user_input.lower() == 'demo':
                    demo_scenarios()
                elif user_input:
                    run_agent_system(user_input)
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()