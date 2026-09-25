
#!/usr/bin/env python3
"""
Pretty Content Formatter

This module transforms raw content into formatted "pretty" output with various
formatting options including indentation, syntax highlighting, and structure improvements.
"""

import re
import json
from typing import Dict, List, Any, Union
import logging


class PrettyFormatter:
    """
    A class to transform raw content into a prettier formatted version.
    Supports multiple content types including text, code, and structured data.
    """

    def __init__(self, indent: int = 4, max_line_length: int = 80):
        """
        Initialize the formatter with configuration parameters.

        Args:
            indent: Number of spaces to use for indentation
            max_line_length: Maximum length of a line before wrapping
        """
        self.indent = indent
        self.max_line_length = max_line_length
        self.logger = self._setup_logger()

    @staticmethod
    def _setup_logger() -> logging.Logger:
        """Set up and configure logger."""
        logger = logging.getLogger("PrettyFormatter")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def format_text(self, raw_text: str) -> str:
        """
        Format plain text with proper line breaks and paragraph spacing.
        
        Args:
            raw_text: The raw text to format
            
        Returns:
            Formatted text
        """
        if not raw_text:
            return ""
            
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', raw_text).strip()
        
        # Split into paragraphs
        paragraphs = re.split(r'\n\s*\n|\.\s+', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # Format each paragraph with proper line breaks
        formatted_paragraphs = []
        for paragraph in paragraphs:
            lines = []
            current_line = ""
            
            for word in paragraph.split():
                if len(current_line) + len(word) + 1 <= self.max_line_length:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
                
            formatted_paragraphs.append("\n".join(lines))
        
        return "\n\n".join(formatted_paragraphs)
    
    def format_code(self, raw_code: str, language: str = "python") -> str:
        """
        Format code with proper indentation and syntax structure.
        
        Args:
            raw_code: The raw code to format
            language: Programming language of the code
            
        Returns:
            Formatted code
        """
        if language.lower() == "python":
            return self._format_python_code(raw_code)
        elif language.lower() in ["javascript", "js"]:
            return self._format_js_code(raw_code)
        elif language.lower() in ["json"]:
            return self._format_json(raw_code)
        else:
            # Basic indentation for other languages
            return self._format_generic_code(raw_code)
    
    def _format_python_code(self, raw_code: str) -> str:
        """Format Python code with PEP 8 style guidelines."""
        try:
            # Note: In a real implementation, you might use the 'black' or 'autopep8' library
            # This is a simplified version for demonstration
            
            lines = raw_code.strip().split("\n")
            result = []
            indent_level = 0
            
            for line in lines:
                stripped = line.strip()
                
                # Adjust indent level based on content
                if stripped.endswith(":"):
                    # Add the line with current indentation
                    result.append(" " * (self.indent * indent_level) + stripped)
                    indent_level += 1
                elif stripped in ["break", "continue", "pass", "return"] or not stripped:
                    # Keep same indentation
                    if stripped:
                        result.append(" " * (self.indent * indent_level) + stripped)
                    else:
                        result.append("")
                elif stripped.startswith(("else:", "elif ", "except:", "finally:", "except ")):
                    # Decrease for else/elif/except blocks
                    indent_level = max(0, indent_level - 1)
                    result.append(" " * (self.indent * indent_level) + stripped)
                    indent_level += 1
                else:
                    result.append(" " * (self.indent * indent_level) + stripped)
            
            return "\n".join(result)
        except Exception as e:
            self.logger.error(f"Error formatting Python code: {e}")
            return raw_code
    
    def _format_js_code(self, raw_code: str) -> str:
        """Format JavaScript code."""
        # Similar to Python formatting but with JavaScript syntax
        # In a real implementation, you might use a library like 'js-beautify'
        try:
            lines = raw_code.strip().split("\n")
            result = []
            indent_level = 0
            
            for line in lines:
                stripped = line.strip()
                
                # Handle brackets for indentation
                if stripped.endswith("{"):
                    result.append(" " * (self.indent * indent_level) + stripped)
                    indent_level += 1
                elif stripped == "}":
                    indent_level = max(0, indent_level - 1)
                    result.append(" " * (self.indent * indent_level) + stripped)
                else:
                    result.append(" " * (self.indent * indent_level) + stripped)
            
            return "\n".join(result)
        except Exception as e:
            self.logger.error(f"Error formatting JavaScript code: {e}")
            return raw_code
    
    def _format_json(self, raw_json: str) -> str:
        """Format JSON data with proper indentation."""
        try:
            parsed = json.loads(raw_json)
            return json.dumps(parsed, indent=self.indent, sort_keys=True)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON: {e}")
            return raw_json
    
    def _format_generic_code(self, raw_code: str) -> str:
        """Basic formatting for generic code."""
        try:
            lines = raw_code.strip().split("\n")
            result = []
            
            for line in lines:
                stripped = line.strip()
                # Count leading spaces to preserve relative indentation
                leading_spaces = len(line) - len(line.lstrip())
                indent_units = leading_spaces // 2  # Assuming original uses 2 spaces
                result.append(" " * (self.indent * indent_units) + stripped)
            
            return "\n".join(result)
        except Exception as e:
            self.logger.error(f"Error in generic code formatting: {e}")
            return raw_code
    
    def format_structured_data(self, data: Union[Dict, List]) -> str:
        """
        Format structured data (dictionaries, lists) into a readable format.
        
        Args:
            data: The structured data to format
            
        Returns:
            Formatted string representation
        """
        try:
            return json.dumps(data, indent=self.indent, sort_keys=True)
        except Exception as e:
            self.logger.error(f"Error formatting structured data: {e}")
            if isinstance(data, (dict, list)):
                # Fallback to str representation
                return str(data)
            return ""
    
    def format_content(self, raw_content: str, content_type: str = "text") -> str:
        """
        Main method to format content based on its type.
        
        Args:
            raw_content: The raw content to format
            content_type: Type of content ('text', 'code:<language>', 'json', etc.)
            
        Returns:
            Formatted content
        """
        self.logger.info(f"Formatting content of type: {content_type}")
        
        if not raw_content:
            return ""
            
        if content_type == "text":
            return self.format_text(raw_content)
        elif content_type.startswith("code:"):
            language = content_type.split(":", 1)[1]
            return self.format_code(raw_content, language)
        elif content_type == "json":
            return self._format_json(raw_content)
        else:
            self.logger.warning(f"Unknown content type: {content_type}")
            # Default to text formatting
            return self.format_text(raw_content)