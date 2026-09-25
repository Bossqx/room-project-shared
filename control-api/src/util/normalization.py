"""
Content Normalizer - Python Package for normalizing text content

This package provides utilities for normalizing different types of content
(plain text, HTML, and JSON) to make it easier to read and process.
"""
import re
import json
from typing import Optional
from collections import Counter
import html as html_module
from html.parser import HTMLParser
import xml.dom.minidom as minidom


class NormalizerOptions:
    """Base class for normalizer options"""
    pass

class TextNormalizerOptions(NormalizerOptions):
    """Options for text normalization"""
    
    def __init__(
        self,
        trim_whitespace: bool = True,
        normalize_line_breaks: bool = True,
        remove_excessive_spaces: bool = True,
        remove_excessive_line_breaks: bool = True,
        normalize_indentation: bool = False
    ):
        """
        Initialize text normalizer options
        
        Args:
            trim_whitespace: Remove leading/trailing whitespace
            normalize_line_breaks: Standardize line breaks to \n
            remove_excessive_spaces: Replace multiple spaces with single space
            remove_excessive_line_breaks: Replace multiple line breaks with single line break
            normalize_indentation: Detect and normalize indentation
        """
        self.trim_whitespace = trim_whitespace
        self.normalize_line_breaks = normalize_line_breaks
        self.remove_excessive_spaces = remove_excessive_spaces
        self.remove_excessive_line_breaks = remove_excessive_line_breaks
        self.normalize_indentation = normalize_indentation


class HtmlNormalizerOptions(NormalizerOptions):
    """Options for HTML normalization"""
    
    def __init__(
        self,
        remove_comments: bool = False,
        normalize_self_closing_tags: bool = True,
        normalize_attribute_quotes: bool = True,
        normalize_tag_whitespace: bool = True,
        pretty_print: bool = True
    ):
        """
        Initialize HTML normalizer options
        
        Args:
            remove_comments: Remove HTML comments
            normalize_self_closing_tags: Normalize self-closing tags
            normalize_attribute_quotes: Normalize attribute quotes
            normalize_tag_whitespace: Normalize whitespace between tags
            pretty_print: Format HTML with proper indentation
        """
        self.remove_comments = remove_comments
        self.normalize_self_closing_tags = normalize_self_closing_tags
        self.normalize_attribute_quotes = normalize_attribute_quotes
        self.normalize_tag_whitespace = normalize_tag_whitespace
        self.pretty_print = pretty_print


class JsonNormalizerOptions(NormalizerOptions):
    """Options for JSON normalization"""
    
    def __init__(
        self,
        indent_spaces: int = 2,
        sort_keys: bool = False
    ):
        """
        Initialize JSON normalizer options
        
        Args:
            indent_spaces: Number of spaces for indentation
            sort_keys: Whether to sort dictionary keys
        """
        self.indent_spaces = indent_spaces
        self.sort_keys = sort_keys


def normalize_content(
    content: str,
    options: Optional[TextNormalizerOptions] = None
) -> str:
    """
    Normalizes text content for easier reading and processing
    
    Args:
        content: The content to normalize
        options: Configuration options
        
    Returns:
        Normalized content
    """
    if not content or not isinstance(content, str):
        return ""
    
    if options is None:
        options = TextNormalizerOptions()
    
    normalized = content
    
    # Normalize line breaks (convert \r\n and \r to \n)
    if options.normalize_line_breaks:
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    
    # Remove excessive line breaks
    if options.remove_excessive_line_breaks:
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    
    # Remove excessive spaces
    if options.remove_excessive_spaces:
        normalized = re.sub(r"[ \t]+", " ", normalized)
    
    # Normalize indentation if requested
    if options.normalize_indentation:
        normalized = normalize_indentation(normalized)
    
    # Trim whitespace
    if options.trim_whitespace:
        normalized = normalized.strip()
    
    return normalized


def normalize_indentation(content: str) -> str:
    """
    Detects and normalizes indentation in text content
    
    Args:
        content: The content to normalize indentation for
        
    Returns:
        Content with normalized indentation
    """
    lines = content.split("\n")
    
    # Find all indentations
    indentations = []
    indent_pattern = re.compile(r"^(\s+)")
    
    for line in lines:
        if not line.strip():
            continue
        
        match = indent_pattern.match(line)
        if match:
            indentations.append(match.group(1))
    
    # If no indentation found, return original content
    if not indentations:
        return content
    
    # Find most common indentation type and size
    indent_counter = Counter(indentations)
    most_common_indent = indent_counter.most_common(1)[0][0]
    
    # Determine if tabs or spaces are used
    uses_tabs = "\t" in most_common_indent
    standard_indent = "\t" if uses_tabs else "  "  # Default to 2 spaces
    
    # Normalize indentation for each line
    normalized_lines = []
    for line in lines:
        if not line.strip():
            normalized_lines.append("")
            continue
        
        match = indent_pattern.match(line)
        if not match:
            normalized_lines.append(line)
            continue
        
        current_indent = match.group(1)
        if uses_tabs:
            # For tabs, count the number of tabs
            indent_level = len(current_indent)
        else:
            # For spaces, estimate the level based on 2-space indentation
            indent_level = round(len(current_indent) / 2)
        
        normalized_lines.append(standard_indent * indent_level + line[len(current_indent):])
    
    return "\n".join(normalized_lines)


class HTMLNormalizer(HTMLParser):
    """Custom HTML parser for normalization"""
    
    def __init__(self, options: HtmlNormalizerOptions):
        super().__init__()
        self.options = options
        self.result = []
        self.in_comment = False
    
    def handle_starttag(self, tag, attrs):
        attr_str = ""
        if attrs:
            normalized_attrs = []
            for name, value in attrs:
                if value is None:
                    normalized_attrs.append(f"{name}")
                else:
                    normalized_attrs.append(f'{name}="{html_module.escape(value)}"')
            attr_str = " " + " ".join(normalized_attrs)
        
        self.result.append(f"<{tag}{attr_str}>")
    
    def handle_endtag(self, tag):
        self.result.append(f"</{tag}>")
    
    def handle_startendtag(self, tag, attrs):
        if self.options.normalize_self_closing_tags:
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)
        else:
            attr_str = ""
            if attrs:
                normalized_attrs = []
                for name, value in attrs:
                    if value is None:
                        normalized_attrs.append(f"{name}")
                    else:
                        normalized_attrs.append(f'{name}="{html_module.escape(value)}"')
                attr_str = " " + " ".join(normalized_attrs)
            
            self.result.append(f"<{tag}{attr_str}/>")
    
    def handle_data(self, data):
        self.result.append(data)
    
    def handle_comment(self, data):
        if not self.options.remove_comments:
            self.result.append(f"<!--{data}-->")
    
    def get_normalized_html(self) -> str:
        return "".join(self.result)


def normalize_html(
    html_content: str,
    options: Optional[HtmlNormalizerOptions] = None
) -> str:
    """
    Normalizes HTML content
    
    Args:
        html_content: The HTML content to normalize
        options: Configuration options
        
    Returns:
        Normalized HTML content
    """
    if not html_content or not isinstance(html_content, str):
        return ""
    
    if options is None:
        options = HtmlNormalizerOptions()
    
    # Basic pre-processing
    normalized = html_content.replace("\r\n", "\n").replace("\r", "\n")
    
    try:
        # Use the custom parser for initial normalization
        parser = HTMLNormalizer(options)
        parser.feed(normalized)
        normalized = parser.get_normalized_html()
        
        # Additional processing
        if options.normalize_attribute_quotes:
            normalized = re.sub(r"=\s*'([^']*)'", r'="\1"', normalized)
        
        if options.normalize_tag_whitespace:
            normalized = re.sub(r">\s+<", ">\n<", normalized)
        
        # Pretty print if requested
        if options.pretty_print:
            try:
                dom = minidom.parseString(normalized)
                normalized = dom.toprettyxml(indent='  ')
                
                # Remove XML declaration
                normalized = re.sub(r'<\?xml[^>]+\?>\s*', '', normalized)
                
                # Remove excessive blank lines from pretty print
                normalized = re.sub(r'\n\s*\n', '\n', normalized)
            except Exception:
                # If pretty printing fails, just return the basic normalized version
                pass
        
        return normalized
    except Exception as e:
        # If parsing fails, return the basic normalized version
        print(f"HTML normalization error: {e}")
        return normalized


def normalize_json(
    json_content: str,
    options: Optional[JsonNormalizerOptions] = None
) -> str:
    """
    Normalizes JSON content
    
    Args:
        json_content: The JSON content to normalize
        options: Configuration options
        
    Returns:
        Normalized JSON content
    """
    if not json_content or not isinstance(json_content, str):
        return ""
    
    if options is None:
        options = JsonNormalizerOptions()
    
    try:
        # Parse and stringify to normalize format
        parsed = json.loads(json_content.strip())
        return json.dumps(
            parsed,
            indent=options.indent_spaces,
            sort_keys=options.sort_keys
        )
    except json.JSONDecodeError as e:
        # If parsing fails, return original content
        print(f"Failed to normalize JSON: {e}")
        return json_content


def is_valid_json(content: str) -> bool:
    """
    Checks if a string is valid JSON
    
    Args:
        content: The string to check
        
    Returns:
        Whether the string is valid JSON
    """
    if not content or not isinstance(content, str):
        return False
    
    try:
        json.loads(content.strip())
        return True
    except json.JSONDecodeError:
        return False


def detect_content_type(content: str) -> str:
    """
    Attempts to detect the content type
    
    Args:
        content: The content to analyze
        
    Returns:
        The detected content type ('html', 'json', or 'text')
    """
    if not content or not isinstance(content, str):
        return "text"
    
    # Simple detection based on content patterns
    trimmed = content.strip()
    
    # Check if it's HTML
    if trimmed.startswith("<") and trimmed.endswith(">"):
        return "html"
    
    # Check if it's JSON
    if is_valid_json(content):
        return "json"
    
    # Default to text
    return "text"


def auto_normalize(
    content: str,
    text_options: Optional[TextNormalizerOptions] = None,
    html_options: Optional[HtmlNormalizerOptions] = None,
    json_options: Optional[JsonNormalizerOptions] = None
) -> str:
    """
    Auto-normalizes content based on its detected type
    
    Args:
        content: The content to normalize
        text_options: Options for text normalization
        html_options: Options for HTML normalization
        json_options: Options for JSON normalization
        
    Returns:
        Normalized content
    """
    content_type = detect_content_type(content)
    
    if content_type == "html":
        return normalize_html(content, html_options)
    elif content_type == "json":
        return normalize_json(content, json_options)
    else:
        return normalize_content(content, text_options)
