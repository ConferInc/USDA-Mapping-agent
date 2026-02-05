"""
Tool Wrapper - Convert functions to CrewAI-compatible tools
"""

from typing import Callable, Any, Optional
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import inspect


def create_tool(func: Callable, name: Optional[str] = None, description: Optional[str] = None) -> StructuredTool:
    """
    Create a CrewAI-compatible tool from a Python function using StructuredTool.
    
    Args:
        func: The function to wrap
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
    
    Returns:
        StructuredTool instance
    """
    tool_name = name or func.__name__
    tool_description = description or (func.__doc__ or f"Tool: {tool_name}")
    
    # Clean up description
    tool_description = tool_description.strip()
    
    # Get function signature to create proper tool
    sig = inspect.signature(func)
    params = {}
    
    # Create a simple tool that calls the function
    # For CrewAI, we'll use StructuredTool with a simple schema
    return StructuredTool.from_function(
        func=func,
        name=tool_name,
        description=tool_description
    )

