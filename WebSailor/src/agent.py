#!/usr/bin/env python3
"""
Multi-Agent System with Controller and SubAgents
"""

import re
import json
from typing import List, Dict, Any, Optional, Union
from qwen_agent.agents.fncall_agent import FnCallAgent
from qwen_agent.llm import BaseChatModel
from qwen_agent.tools import BaseTool
from prompt import CONTROLLER_PROMPT, SUBAGENT_PROMPT


class Controller(FnCallAgent):
    """Controller - makes decisions and manages subagents"""
    
    def __init__(self, tools: List[BaseTool], llm: Union[Dict, BaseChatModel], 
                 system_message: Optional[str] = None):
        # Controller can only directly use search, visit, code tools
        controller_tools = [tool for tool in tools if hasattr(tool, 'name') and 
                          tool.name in ['search', 'visit', 'code']]
        
        # Get all available tools for schema
        all_tools_desc = ', '.join([f"{tool.name}: {getattr(tool, 'description', 'No description')}" 
                                  for tool in tools])
        
        if system_message is None:
            system_message = CONTROLLER_PROMPT.format(tools=all_tools_desc)
        
        super().__init__(
            function_list=controller_tools,
            llm=llm,
            system_message=system_message,
            name="Controller"
        )
        
        self.all_tools = tools  # All available tools for schema
        self.controller_tools = controller_tools  # Tools controller can directly use
        self.messages = []  # Internal message history
        
    def step(self, task: str, history: str = "") -> Dict:
        """Make one decision"""
        prompt = f"Task: {task}\n\nHistory:\n{history}" if history else f"Task: {task}"
        
        # Add to internal messages
        self.messages.append({"role": "user", "content": prompt})
        
        # Get response from LLM
        response = self.llm(self.messages)
        
        # Add to internal messages
        self.messages.append({"role": "assistant", "content": response})
        
        # Parse response
        think = self._extract_tag(response, 'think')
        action = self._extract_tag(response, 'action').strip()
        content = self._extract_tag(response, 'content').strip()
        
        return {
            'think': think,
            'action': action, 
            'content': content,
            'raw': response
        }
    
    def use_tool(self, tool_name: str, args: Dict) -> str:
        """Controller directly uses a tool"""
        for tool in self.controller_tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                try:
                    result = tool.call(args)
                    # Add tool usage to internal messages
                    self.messages.append({
                        "role": "user", 
                        "content": f"Tool {tool_name} result: {result}"
                    })
                    return result
                except Exception as e:
                    error_msg = f"Tool {tool_name} error: {e}"
                    self.messages.append({"role": "user", "content": error_msg})
                    return error_msg
        
        return f"Tool {tool_name} not available to controller"
    
    def create_subagent(self, role: str, task: str, tool_names: List[str]) -> 'SubAgent':
        """Create a subagent with specified tools"""
        # Get tools for subagent
        subagent_tools = []
        for tool_name in tool_names:
            for tool in self.all_tools:
                if hasattr(tool, 'name') and tool.name == tool_name.strip():
                    subagent_tools.append(tool)
        
        # Create subagent
        subagent = SubAgent(role, task, subagent_tools, self.llm)
        
        # Add subagent creation to internal messages
        self.messages.append({
            "role": "user", 
            "content": f"Created subagent {role} with tools: {tool_names}"
        })
        
        return subagent
    
    def _extract_tag(self, text: str, tag: str) -> str:
        """Extract content from XML-like tags"""
        match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
        return match.group(1).strip() if match else ""
    
    def _extract_tools(self, content: str) -> List[Dict]:
        """Extract tool calls from content"""
        tools = []
        tool_pattern = r'<tool>\s*(.*?)\s*</tool>'
        tool_matches = re.findall(tool_pattern, content, re.DOTALL)
        
        for tool_match in tool_matches:
            tool_info = {}
            lines = tool_match.strip().split('\n')
            for line in lines:
                if line.startswith('name:'):
                    tool_info['name'] = line.replace('name:', '').strip()
                elif line.startswith('args:'):
                    args_str = line.replace('args:', '').strip()
                    try:
                        tool_info['args'] = json.loads(args_str)
                    except:
                        tool_info['args'] = {"query": args_str}
            
            if 'name' in tool_info:
                tools.append(tool_info)
        
        return tools
    
    def _extract_subagents(self, content: str) -> List[Dict]:
        """Extract subagent specifications from content"""
        subagents = []
        subagent_pattern = r'<subagent>\s*(.*?)\s*</subagent>'
        subagent_matches = re.findall(subagent_pattern, content, re.DOTALL)
        
        for subagent_match in subagent_matches:
            subagent_info = {}
            lines = subagent_match.strip().split('\n')
            for line in lines:
                if line.startswith('role:'):
                    subagent_info['role'] = line.replace('role:', '').strip()
                elif line.startswith('task:'):
                    subagent_info['task'] = line.replace('task:', '').strip()
                elif line.startswith('tools:'):
                    tools_str = line.replace('tools:', '').strip()
                    subagent_info['tools'] = [t.strip() for t in tools_str.split(',')]
            
            if all(k in subagent_info for k in ['role', 'task', 'tools']):
                subagents.append(subagent_info)
        
        return subagents


class SubAgent(FnCallAgent):
    """SubAgent - executes specific tasks"""
    
    def __init__(self, role: str, task: str, tools: List[BaseTool], 
                 llm: Union[Dict, BaseChatModel]):
        tools_desc = ', '.join([f"{tool.name}: {getattr(tool, 'description', 'No description')}" 
                              for tool in tools])
        
        system_message = SUBAGENT_PROMPT.format(
            role=role,
            task=task,
            tools=tools_desc
        )
        
        super().__init__(
            function_list=tools,
            llm=llm,
            system_message=system_message,
            name=f"SubAgent_{role}"
        )
        
        self.role = role
        self.task = task
        self.tools = tools
        self.messages = []  # Internal message history
        
    def execute(self, max_rounds: int = 3) -> str:
        """Execute task with multiple rounds if needed"""
        for round in range(max_rounds):
            if round == 0:
                prompt = f"Start executing your task: {self.task}"
            else:
                prompt = "Continue if needed."
                
            # Add to internal messages
            self.messages.append({"role": "user", "content": prompt})
            
            # Get response from LLM
            response = self.llm(self.messages)
            
            # Add to internal messages
            self.messages.append({"role": "assistant", "content": response})
            
            # Handle tool calls
            if '<tool>' in response:
                tool_result = self._call_tool_from_response(response)
                self.messages.append({
                    "role": "user", 
                    "content": f"Tool result: {tool_result}"
                })
            
            # Check if done
            if '<answer>' in response:
                answer = self._extract_tag(response, 'answer')
                self.messages.append({
                    "role": "user", 
                    "content": f"Task completed with answer: {answer}"
                })
                return answer
        
        # Max rounds reached
        final_msg = "Failed to execute task within max rounds"
        self.messages.append({"role": "user", "content": final_msg})
        return final_msg
    
    def _call_tool_from_response(self, response: str) -> str:
        """Parse and call tool from response"""
        tools = self._extract_tools(response)
        if not tools:
            return "No tool calls found"
        
        results = []
        for tool_info in tools:
            tool_name = tool_info.get('name', '')
            args = tool_info.get('args', {})
            
            if tool_name:
                try:
                    # Find and call the tool directly
                    for tool in self.tools:
                        if hasattr(tool, 'name') and tool.name == tool_name:
                            result = tool.call(args)
                            results.append(f"{tool_name}: {result}")
                            break
                    else:
                        results.append(f"{tool_name}: Tool not found")
                except Exception as e:
                    results.append(f"{tool_name} error: {e}")
        
        return "\n".join(results) if results else "Could not execute any tools"
    
    def _extract_tools(self, response: str) -> List[Dict]:
        """Extract tool calls from response"""
        tools = []
        tool_pattern = r'<tool>\s*(.*?)\s*</tool>'
        tool_matches = re.findall(tool_pattern, response, re.DOTALL)
        
        for tool_match in tool_matches:
            tool_info = {}
            lines = tool_match.strip().split('\n')
            for line in lines:
                if line.startswith('name:'):
                    tool_info['name'] = line.replace('name:', '').strip()
                elif line.startswith('args:'):
                    args_str = line.replace('args:', '').strip()
                    try:
                        tool_info['args'] = json.loads(args_str)
                    except:
                        tool_info['args'] = {"query": args_str}
            
            if 'name' in tool_info:
                tools.append(tool_info)
        
        return tools
    
    def _extract_tag(self, text: str, tag: str) -> str:
        """Extract content from XML-like tags"""
        match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
        return match.group(1).strip() if match else ""