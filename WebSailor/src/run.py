#!/usr/bin/env python3
"""
Multi-Agent System Runner
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import Controller, SubAgent
from tool_search import Search
from tool_visit import Visit
from tool_code import Code
from openai import OpenAI


class SimpleLLM:
    """Minimal LLM wrapper"""
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.client = OpenAI(
            api_key="EMPTY",
            base_url="http://11.216.48.78:8032/v1"
        )
    
    def __call__(self, messages):
        response = self.client.chat.completions.create(
            model=self.model_path,
            messages=messages,
            temperature=0.6,
            stop=["\n<tool_response>", "<tool_response>"]
        )
        return response.choices[0].message.content


def run_mas(task: str, llm, tools, max_rounds: int = 5):
    """Main MAS loop"""
    
    # Create controller
    controller = Controller(tools, llm)
    
    print(f"\n{'='*50}")
    print(f"Task: {task}")
    print(f"{'='*50}")
    
    for round_num in range(max_rounds):
        print(f"\n--- Round {round_num + 1} ---")
        
        # Controller step
        step = controller.step(task)
        
        print(f"Think: {step['think'][:100]}...")
        print(f"Action: {step['action']}")
        
        # Handle action
        if step['action'] == 'direct_answer':
            print(f"Answer: {step['content']}")
            return step['content']
            
        elif step['action'] == 'completed':
            print(f"Final: {step['content']}")
            return step['content']
            
        elif step['action'] == 'create_subagents':
            # Parse and create subagents
            subagent_specs = controller._extract_subagents(step['content'])
            subagent_results = []
            
            for spec in subagent_specs:
                role = spec['role']
                task_desc = spec['task']
                tool_names = spec['tools']
                
                print(f"\n  Creating {role}...")
                subagent = controller.create_subagent(role, task_desc, tool_names)
                
                print(f"  Running {role}...")
                result = subagent.execute()
                print(f"  Result: {result[:100]}...")
                subagent_results.append(f"{role}: {result}")
            
            # Add results to controller's internal history
            controller.messages.append({
                "role": "user",
                "content": f"Subagents completed:\n" + "\n".join(subagent_results)
            })
            
        elif step['action'] == 'use_tools':
            # Controller uses tools directly
            tool_calls = controller._extract_tools(step['content'])
            
            for tool_call in tool_calls:
                tool_name = tool_call.get('name', '')
                args = tool_call.get('args', {})
                
                if tool_name:
                    print(f"  Using tool: {tool_name}")
                    result = controller.use_tool(tool_name, args)
                    print(f"  Result: {result[:100]}...")
        
        else:
            print(f"Unknown action: {step['action']}")
    
    # Max rounds reached
    return "Task incomplete - max rounds reached"


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="/apdcephfs_cq11/share_1567347/share_info/rhyang/huggingface_models/models--Alibaba-NLP--WebSailor-3B/snapshots/b317a15261674d83d851f0a14761840583bb9dce")
    parser.add_argument("--task", default="What is the capital of France?")
    parser.add_argument("--rounds", type=int, default=5)
    
    args = parser.parse_args()
    
    # Setup
    llm = SimpleLLM(args.model)
    tools = [Search(), Visit(), Code()]
    
    # Run
    result = run_mas(args.task, llm, tools, args.rounds)
    
    print(f"\n{'='*50}")
    print("FINAL RESULT:")
    print(result)
    print(f"{'='*50}")


if __name__ == "__main__":
    main()