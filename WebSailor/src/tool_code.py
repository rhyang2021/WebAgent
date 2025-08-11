#!/usr/bin/env python3
"""
Code Tool for Controller
"""

from qwen_agent.tools.base import BaseTool, register_tool
from typing import Union


@register_tool('code', allow_overwrite=True)
class Code(BaseTool):
    name = 'code'
    description = 'Execute Python code and return the result.'
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            }
        },
        "required": ["code"]
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        try:
            code = params["code"]
        except:
            return "[Code] Invalid request format: Input must be a JSON object containing 'code' field"
        
        try:
            # Execute the code in a safe environment
            # Note: In production, you should use a sandboxed environment
            result = eval(code)
            return f"Code executed successfully. Result: {result}"
        except Exception as e:
            return f"Code execution error: {str(e)}"