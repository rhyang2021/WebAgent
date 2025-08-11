#!/usr/bin/env python3
"""
Modified Agent Definitions with Internal Message History
"""

import re
import json
from typing import List, Dict, Any, Optional, Union
from qwen_agent.agents.fncall_agent import FnCallAgent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import DEFAULT_SYSTEM_MESSAGE, Message
from qwen_agent.tools import BaseTool
from openai import OpenAI


class Controller(FnCallAgent):
    """Controller - makes decisions and coordinates tasks"""
    
    def __init__(self, 
                 all_tools: List[BaseTool], 
                 llm: Union[Dict, BaseChatModel],
                 system_message: Optional[str] = None):
        # Controller can only directly use search, visit, code tools
        direct_tools = [tool for tool in all_tools if tool.name in ['search', 'visit', 'code']]
        
        # Build tool schemas for all tools (for subagent assignment)
        self.all_tool_schemas = {}
        for tool in all_tools:
            self.all_tool_schemas[tool.name] = {
                'name': tool.name,
                'description': getattr(tool, 'description', ''),
                'parameters': getattr(tool, 'parameters', {})
            }
        
        # Custom system message that includes all tool schemas
        if system_message is None:
            tools_desc = self._format_all_tools_description()
            system_message = f"""You are a Controller agent. You coordinate tasks and make decisions.

Available tools for direct use: search, visit, code
All available tools (for subagent assignment): {', '.join(self.all_tool_schemas.keys())}

{tools_desc}

Output format:
- For direct tool calls: <tool_call>{{"name": "tool_name", "arguments": {{}}}}</tool_call>
- For subagent creation: <subagent>{{"role": "role_name", "task": "task_description", "tools": ["tool1", "tool2"]}}</subagent>
- For final answers: <answer>your answer</answer>

Always think step by step and decide whether to use tools directly, create subagents, or provide answers."""
        
        super().__init__(
            function_list=direct_tools,
            llm=llm,
            system_message=system_message,
            name="Controller"
        )
        
        self.all_tools = all_tools
        self.direct_tools = direct_tools
        self.messages = []  # Internal message history
        self.subagents = {}  # Store created subagents
        
        # Initialize OpenAI client if llm is a dict
        if isinstance(llm, dict):
            self.client = OpenAI(
                api_key=llm.get('api_key', 'EMPTY'),
                base_url=llm.get('model_server', 'http://11.216.48.78:8032/v1')
            )
            self.llm_cfg = llm
        else:
            self.client = None
            self.llm_cfg = None

    def _format_all_tools_description(self) -> str:
        """Format descriptions of all available tools"""
        descriptions = []
        for name, schema in self.all_tool_schemas.items():
            desc = f"- {name}: {schema['description']}"
            descriptions.append(desc)
        return "\n".join(descriptions)

    def step(self, task: str) -> Dict:
        """Make one decision step"""
        # Add user message to history
        user_msg = {"role": "user", "content": task}
        self.messages.append(user_msg)
        
        # Get response from LLM
        if self.client and self.llm_cfg:
            response = self._call_llm_api(self.messages)
        else:
            # Fallback to parent class method
            response = "Error: LLM not properly configured"
        
        # Add assistant response to history
        assistant_msg = {"role": "assistant", "content": response}
        self.messages.append(assistant_msg)
        
        # Parse response and execute actions
        result = self._parse_and_execute_response(response)
        
        return {
            'response': response,
            'result': result,
            'messages': self.messages.copy()
        }

    def _call_llm_api(self, messages: List[Dict]) -> str:
        """Call LLM API"""
        try:
            # Prepend system message
            full_messages = [{"role": "system", "content": self.system_message}] + messages
            
            response = self.client.chat.completions.create(
                model=self.llm_cfg['model'],
                messages=full_messages,
                temperature=self.llm_cfg.get('temperature', 0.6),
                stop=["<tool_response>", "\n<tool_response"]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"LLM API Error: {str(e)}"

    def _parse_and_execute_response(self, response: str) -> Dict:
        """Parse response and execute tool calls or create subagents"""
        result = {'type': 'text', 'content': response}
        
        # Handle tool calls
        if '<tool_call>' in response and '</tool_call>' in response:
            tool_call_content = self._extract_tag(response, 'tool_call')
            result = self._execute_tool_call(tool_call_content)
            
        # Handle subagent creation
        elif '<subagent>' in response and '</subagent>' in response:
            subagent_content = self._extract_tag(response, 'subagent')
            result = self._create_and_run_subagent(subagent_content)
            
        # Handle final answer
        elif '<answer>' in response and '</answer>' in response:
            answer = self._extract_tag(response, 'answer')
            result = {'type': 'answer', 'content': answer}
        
        return result

    def _extract_tag(self, text: str, tag: str) -> str:
        """Extract content between XML tags"""
        match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _execute_tool_call(self, tool_call_content: str) -> Dict:
        """Execute a tool call"""
        try:
            tool_call = json.loads(tool_call_content)
            tool_name = tool_call.get('name', '')
            tool_args = tool_call.get('arguments', {})
            
            # Check if tool is in direct tools
            if tool_name not in [t.name for t in self.direct_tools]:
                return {'type': 'error', 'content': f'Tool {tool_name} not available for direct use'}
            
            # Execute tool
            result = self._call_tool(tool_name, tool_args)
            
            # Add tool response to messages
            tool_response = f"<tool_response>\n{result}\n</tool_response>"
            self.messages.append({"role": "user", "content": tool_response})
            
            return {'type': 'tool_result', 'content': result}
            
        except Exception as e:
            error_msg = f'Tool execution error: {str(e)}'
            self.messages.append({"role": "user", "content": f"<tool_response>\n{error_msg}\n</tool_response>"})
            return {'type': 'error', 'content': error_msg}

    def _create_and_run_subagent(self, subagent_content: str) -> Dict:
        """Create and run a subagent"""
        try:
            subagent_spec = json.loads(subagent_content)
            role = subagent_spec.get('role', '')
            task = subagent_spec.get('task', '')
            tool_names = subagent_spec.get('tools', [])
            
            # Get tools for subagent
            subagent_tools = []
            for tool_name in tool_names:
                for tool in self.all_tools:
                    if tool.name == tool_name:
                        subagent_tools.append(tool)
                        break
            
            # Create subagent
            subagent = SubAgent(role, task, subagent_tools, self.llm_cfg or {})
            
            # Store subagent
            self.subagents[role] = subagent
            
            # Execute subagent
            result = subagent.execute()
            
            # Add subagent result to messages
            subagent_response = f"<subagent_response>\nRole: {role}\nResult: {result}\n</subagent_response>"
            self.messages.append({"role": "user", "content": subagent_response})
            
            return {'type': 'subagent_result', 'content': result, 'role': role}
            
        except Exception as e:
            error_msg = f'Subagent creation error: {str(e)}'
            self.messages.append({"role": "user", "content": f"<subagent_response>\n{error_msg}\n</subagent_response>"})
            return {'type': 'error', 'content': error_msg}


class SubAgent(FnCallAgent):
    """SubAgent - executes specific tasks with assigned tools"""
    
    def __init__(self, 
                 role: str, 
                 task: str, 
                 tools: List[BaseTool], 
                 llm_cfg: Dict):
        
        tools_desc = ', '.join([t.name for t in tools])
        system_message = f"""You are a SubAgent with role: {role}
Your task: {task}
Available tools: {tools_desc}

Execute your task using the available tools. Use this format:
<tool_call>{{"name": "tool_name", "arguments": {{}}}}</tool_call>

When you have completed your task, provide your final result:
<answer>your final result</answer>"""
        
        super().__init__(
            function_list=tools,
            llm=llm_cfg,  # This will be passed to parent class
            system_message=system_message,
            name=f"SubAgent_{role}"
        )
        
        self.role = role
        self.task = task
        self.messages = []  # Internal message history
        
        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=llm_cfg.get('api_key', 'EMPTY'),
            base_url=llm_cfg.get('model_server', 'http://11.216.48.78:8032/v1')
        )
        self.llm_cfg = llm_cfg

    def execute(self, max_rounds: int = 5) -> str:
        """Execute task with multiple rounds if needed"""
        # Initialize with task
        start_msg = {"role": "user", "content": "Start executing your task."}
        self.messages.append(start_msg)
        
        for round_num in range(max_rounds):
            # Get response from LLM
            response = self._call_llm_api(self.messages)
            
            # Add assistant response to history
            assistant_msg = {"role": "assistant", "content": response}
            self.messages.append(assistant_msg)
            
            # Handle tool calls
            if '<tool_call>' in response and '</tool_call>' in response:
                tool_result = self._execute_tool_call(response)
                if tool_result:
                    tool_response = f"<tool_response>\n{tool_result}\n</tool_response>"
                    self.messages.append({"role": "user", "content": tool_response})
            
            # Check if task is completed
            if '<answer>' in response and '</answer>' in response:
                answer = self._extract_tag(response, 'answer')
                return answer
            
            # Continue message for next round
            if round_num < max_rounds - 1:
                continue_msg = {"role": "user", "content": "Continue if needed or provide your final answer."}
                self.messages.append(continue_msg)
        
        # If max rounds reached without answer
        return "Task execution incomplete - max rounds reached"

    def _call_llm_api(self, messages: List[Dict]) -> str:
        """Call LLM API"""
        try:
            # Prepend system message
            full_messages = [{"role": "system", "content": self.system_message}] + messages
            
            response = self.client.chat.completions.create(
                model=self.llm_cfg['model'],
                messages=full_messages,
                temperature=self.llm_cfg.get('temperature', 0.6),
                stop=["<tool_response>", "\n<tool_response"]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"LLM API Error: {str(e)}"

    def _execute_tool_call(self, response: str) -> str:
        """Parse and execute tool call from response"""
        tool_call_content = self._extract_tag(response, 'tool_call')
        if not tool_call_content:
            return "No tool call found"
        
        try:
            tool_call = json.loads(tool_call_content)
            tool_name = tool_call.get('name', '')
            tool_args = tool_call.get('arguments', {})
            
            result = self._call_tool(tool_name, tool_args)
            return result
            
        except Exception as e:
            return f"Tool execution error: {str(e)}"

    def _extract_tag(self, text: str, tag: str) -> str:
        """Extract content between XML tags"""
        match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
        return match.group(1).strip() if match else ""