"""
Chat Models - Pydantic models for chat endpoints
"""
from typing import List, Dict, Optional
from pydantic import BaseModel
from .chat_constant import JSON_EXTRACT_PROMPT, METADATA_EXTRACT_PROMPT 


class Message_Detect(BaseModel):
    """Model for content detection requests"""
    content: str


class Message(BaseModel):
    """Basic message model with role and content"""
    role: str  # "user" or "assistant"
    content: str

class TransformJSONRequest(BaseModel):
    """Request model for streaming chat endpoints"""
    message: str
    stream: bool = True
    model: str = "gemini-2.5-flash-lite"
    max_tokens: int = 10000
    temperature: float = 0.7
    history: List[Dict[str, str]] = []  # List of {role, content} messages
    persona: str = JSON_EXTRACT_PROMPT


class StreamRequest(BaseModel):
    """Request model for streaming chat endpoints"""
    message: str
    stream: bool = True
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 10000
    temperature: float = 0.7
    history: List[Dict[str, str]] = []  # List of {role, content} messages
    persona: str = ''


class StreamRequestRAG(StreamRequest):
    """Request model for streaming chat endpoints"""
    rag_context: str = ""
    message: str = ""
    model: str = "gemini-2.5-flash-lite"
    extension_prompts: str = ""  # List of {role, content} messages


class StreamRequestImages(BaseModel):
    """Request model for streaming chat with image support"""
    message: str
    stream: bool = True
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 10000
    temperature: float = 0.7
    history: List[Dict[str, str]] = []  # List of {role, content} messages
    images: Optional[List[str]] = None  # List of base64 image strings
    persona: str = ''


class StreamChunk(BaseModel):
    """Response chunk model for streaming"""
    content: str
    type: str = "content"


class Message_Base(BaseModel):
    """Token count request model"""
    message: str
    model: str = "claude-3-sonnet-20240229"