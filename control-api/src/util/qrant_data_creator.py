"""
Qdrant Data Creator
====================
Insert documents with embeddings into Qdrant vector database.

Usage:
    python qdrant_data_creator.py
    
Or import and use programmatically:
    from qdrant_data_creator import QdrantDataCreator
    creator = QdrantDataCreator()
    creator.create_data(payload)
"""

import asyncio
import base64
import codecs
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import os
#from tkinter import Image
import uuid
import json
import re
from typing import Any, BinaryIO, Dict, Optional, Union
from dataclasses import dataclass, field
from dotenv import load_dotenv
from fastapi import HTTPException
from pdf2image import convert_from_bytes
from pypdf import PdfReader
import pytesseract
from sqlalchemy import JSON
from openai import BaseModel, OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from .utility import Util as util
import ast

#load_dotenv()

RAG_UPLOAD_DIR = "uploads/rag_files"

@dataclass
class Document:
    """Document structure for Qdrant insertion."""
    topic: str
    content: str
    metadata: dict = field(default_factory=dict)
    
    def to_payload(self) -> dict:
        """Convert document to Qdrant payload format."""
        return {
            "topic": self.topic,
            "content": self.content,
            **self.metadata
        }
    
    def get_text_for_embedding(self) -> str:
        """Get combined text for embedding generation."""
        return f"{self.topic}\n\n{self.content}"


@dataclass
class DataPayload:
    """Payload structure for batch document insertion."""
    collection: str
    documents: list[dict]
    
    @classmethod
    def from_dict(cls, data: dict) -> "DataPayload":
        """Create DataPayload from dictionary."""
        return cls(
            collection_name=data["collection"],
            documents=data["documents"]
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "DataPayload":
        """Create DataPayload from JSON string."""
        return cls.from_dict(json.loads(json_str))
    





class QdrantDataCreator:
    """
    Qdrant Data Creator with OpenAI Embeddings.
    
    Handles document insertion with automatic embedding generation,
    collection management, and batch processing.
    """
    
    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        embedding_dimension: int = 1536,
        batch_size: int = 100
    ):
        """
        Initialize QdrantDataCreator.
        
        Args:
            qdrant_url: Qdrant server URL (default: from env QDRANT_URL)
            qdrant_api_key: Qdrant API key (default: from env QDRANT_API_KEY)
            openai_api_key: OpenAI API key (default: from env OPENAI_API_KEY)
            embedding_model: OpenAI embedding model name
            embedding_dimension: Vector dimension for the embedding model
            batch_size: Number of documents to process per batch
        """
    
        self.qdrant_url = qdrant_url or util.get_qdrant_url()
        self.qdrant_api_key = util.get_api_key("openai-key")
        self.openai_api_key = util.get_api_key("openai-key")
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension
        self.batch_size = batch_size

       # print(f"🔗 Qdrant URL: {self.qdrant_api_key}")
        
        # Initialize clients
        self.qdrant_client = self._init_qdrant_client()
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
    def _init_qdrant_client(self) -> QdrantClient:
        """Initialize Qdrant client with appropriate settings."""
        if self.qdrant_api_key:
            return QdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key
            )
        return QdrantClient(url=self.qdrant_url)
    
    def ensure_collection(
        self,
        collection_name: str,
        distance: Distance = Distance.COSINE
    ) -> bool:
        """
        Ensure collection exists, create if not.
        
        Args:
            collection_name: Name of the collection
            distance: Distance metric (COSINE, EUCLID, DOT)
            
        Returns:
            True if collection was created, False if already exists
        """
        collections = self.qdrant_client.get_collections().collections
        existing_names = [c.name for c in collections]
        
        if collection_name in existing_names:
            print(f"✓ Collection '{collection_name}' already exists")
            return False
        
        self.qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dimension,
                distance=distance
            )
        )
        print(f"✓ Created collection '{collection_name}'")
        return True
    
    #=============================================================================
    #INSERT PERSONA BY VECTOR
    #=============================================================================
    def insert_persona_index(self, collection_index: str, content: str, metadata: dict = None):
        """
        Insert document with collection_index.
        
        Args:
            collection_index: Your database record ID
            content: Text to embed
            metadata: Optional extra data
            
        Returns:
            Dictionary containing operation status and details
        """
        COLLECTION_NAME="PERSONA_INDEX_COLLECTION"
        
        try:
            embedding = self.generate_embeddings([content])[0]
            point_id = str(uuid.uuid4())
            
            payload = {
                "collection_index": collection_index,
                "content": content[:500]  # Store preview
            }
            if metadata:
                payload.update(metadata)
            
            self.qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            return {
                "status": "success",
                "point_id": point_id,
                "collection_name": COLLECTION_NAME,
                "collection_index": collection_index,
                "message": "Document inserted successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "collection_name": COLLECTION_NAME,
                "collection_index": collection_index,
                "message": f"Failed to insert document: {str(e)}",
                "error": str(e)
            }
        
    
    # =============================================================================
    # INSERT DOCUMENT TOPIC INDEX
    # =============================================================================

    def insert_topic_index(self, collection_index: str, content: str, metadata: dict = None):
        """
        Insert document with collection_index.
        
        Args:
            collection_index: Your database record ID
            content: Text to embed
            metadata: Optional extra data
            
        Returns:
            Dictionary containing operation status and details
        """
        COLLECTION_NAME="TOPIC_INDEX_COLLECTION"
        
        try:
            embedding = self.generate_embeddings([content])[0]
            point_id = str(uuid.uuid4())
            
            payload = {
                "collection_index": collection_index,
                "content": content[:500]  # Store preview
            }
            if metadata:
                payload.update(metadata)
            
            self.qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            return {
                "status": "success",
                "point_id": point_id,
                "collection_name": COLLECTION_NAME,
                "collection_index": collection_index,
                "message": "Document inserted successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "collection_name": COLLECTION_NAME,
                "collection_index": collection_index,
                "message": f"Failed to insert document: {str(e)}",
                "error": str(e)
            }
        
    # =============================================================================
    # SEARCH - RETURNS collection_index
    # =============================================================================

    def search_topic_index(self,query: str, limit: int = 10) -> list:
        """
        Search and return collection_index values with scores.
        
        Returns:
            List of {"collection_index": int, "score": float, "content": str}
        """
        COLLECTION_NAME="TOPIC_INDEX_COLLECTION"
        
        query_embedding = self.generate_embeddings([query])[0]
        
        results = self.qdrant_client(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=limit
        )
        
        return [
            {
                "collection_index": hit.payload["collection_index"],
                "score": hit.score,
                "content": hit.payload.get("content", "")
            }
            for hit in results
        ]

    
    def search_topic_indexes(self,query: str, limit: int = 10) -> list:
        """Search and return only collection_index values."""
        results = self.search_topic_index(query, limit)
        return [r["collection_index"] for r in results]

        
    # =============================================================================
    
    def add_to_vector_db(self, collection_name: str, content_list: list[dict[str, Any]], batch_size: int = 100) -> dict[str, Any]:
        """
        Add extracted content to Qdrant vector database
        
        Args:
            collection_name: Name of the collection to add content to
            content_list: List of content dictionaries to add
            batch_size: Number of points to upload in one batch
            
        Returns:
            Dictionary containing operation status
        """
        if not content_list:
            return {
                "success": False,
                "total_items": 0,
                "total_batches": 0,
                "text_items": 0,
                "image_items": 0,
                "collection_name": collection_name,
                "message": "No content to add to database"
            }
        
        points = []
        text_count = 0
        image_count = 0
        batch_count = 0
        
        try:
            # First ensure the collection exists
            self.ensure_collection(collection_name)
            
            for idx, item in enumerate(content_list):  # Fixed: enumerate returns (index, item)
                # Count items by type
                if item["type"] == "text":
                    text_count += 1
                elif item["type"] == "image":
                    image_count += 1
                
                # Generate unique ID
                point_id = str(uuid.uuid4())
                
                # Create payload (metadata)
                payload = {
                    "type": item["type"],
                    "page_number": item["page_number"],
                    "source": item["source"],
                    "content": item["content"]  # Store full content in payload
                }
                
                # Add additional metadata based on type
                if item["type"] == "text":
                    payload["chunk_index"] = item.get("chunk_index", 0)
                    payload["total_chunks"] = item.get("total_chunks", 1)
                    payload["total_pages"] = item.get("total_pages", 1)
                elif item["type"] == "image":
                    payload["has_image"] = True
                    payload["image_size"] = item.get("image_size", "unknown")
                    # Store image separately or in a different way based on your needs
                    # For large images, consider storing them externally and keeping only references
                    if len(item.get("image_base64", "")) < 1000000:  # Less than 1MB
                        payload["image_base64"] = item.get("image_base64", "")
                
                # Generate embedding using OpenAI
                # Fixed: Using the correct OpenAI client method
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=item["content"]
                )
                embedding = response.data[0].embedding
                
                # Create point
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
                
                # Upload in batches
                if len(points) >= batch_size:
                    self.qdrant_client.upsert(  # Fixed: using qdrant_client
                        collection_name=collection_name,  # Fixed: using parameter
                        points=points
                    )
                    batch_count += 1
                    print(f"Uploaded batch {batch_count}: {len(points)} points to Qdrant")
                    points = []
            
            # Upload remaining points
            if points:
                self.qdrant_client.upsert(  # Fixed: using qdrant_client
                    collection_name=collection_name,  # Fixed: using parameter
                    points=points
                )
                batch_count += 1
                print(f"Uploaded final batch {batch_count}: {len(points)} points to Qdrant")
            
            message = f"Successfully added {len(content_list)} items to collection '{collection_name}'"
            print(message)
            
            return {
                "success": True,
                "total_items": len(content_list),
                "total_batches": batch_count,
                "text_items": text_count,
                "image_items": image_count,
                "collection_name": collection_name,
                "message": message
            }
            
        except Exception as e:
            error_message = f"Error adding content to database: {str(e)}"
            print(error_message)
            return {
                "success": False,
                "total_items": len(content_list),
                "total_batches": batch_count,
                "text_items": text_count,
                "image_items": image_count,
                "collection_name": collection_name,
                "message": error_message,
                "error": str(e)
            }
        
    #***************************Implement Search*********************************

    def query_by_pattern(
            self,
            query_text: str,
            collection_prefix: str,
            n_results: int = 5,
            filter_conditions: Optional[Dict] = None,
            score_threshold: Optional[float] = None
        ) -> dict[str, list[dict[str, Any]]]:
        """
        Query across multiple collections matching a pattern
        
        Args:
            query_text: Text to search for
            collection_prefix: Prefix pattern to match collections (e.g., "pdf_" matches "pdf_*")
            n_results: Number of results per collection
            filter_conditions: Optional filter conditions for metadata
            score_threshold: Minimum similarity score threshold
            
        Returns:
            Dictionary with collection names as keys and results as values
        """
        # Generate query embedding once
        query_embedding = self.embedder.encode(query_text).tolist()
        
        # Build filter if provided
        qdrant_filter = None
        if filter_conditions:
            must_conditions = []
            for key, value in filter_conditions.items():
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                )
            qdrant_filter = models.Filter(must=must_conditions)
        
        # Get all collections
        all_collections = self.client.get_collections().collections
        
        # Filter collections by pattern
        matching_collections = [
            col.name for col in all_collections 
            if col.name.startswith(collection_prefix)
        ]
        
        if not matching_collections:
            print(f"No collections found matching pattern: {collection_prefix}*")
            return {}
        
        print(f"Found {len(matching_collections)} collections matching pattern: {collection_prefix}*")
        
        # Query each matching collection
        all_results = {}
        
        for collection_name in matching_collections:
            try:
                # Search in this collection
                search_result = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    query_filter=qdrant_filter,
                    limit=n_results,
                    score_threshold=score_threshold,
                    with_payload=True
                )
                
                # Format results for this collection
                results = []
                for hit in search_result:
                    result = {
                        "id": hit.id,
                        "score": hit.score,
                        "content": hit.payload.get("content", ""),
                        "collection": collection_name,  # Add collection name
                        "metadata": {
                            "type": hit.payload.get("type"),
                            "source": hit.payload.get("source"),
                            "page_number": hit.payload.get("page_number"),
                            "chunk_index": hit.payload.get("chunk_index"),
                            "total_chunks": hit.payload.get("total_chunks"),
                        }
                    }
                    
                    # Add image data if available
                    if hit.payload.get("has_image"):
                        result["metadata"]["has_image"] = True
                        result["metadata"]["image_size"] = hit.payload.get("image_size")
                        if "image_base64" in hit.payload:
                            result["image_base64"] = hit.payload["image_base64"]
                    
                    results.append(result)
                
                all_results[collection_name] = results
                print(f"  - {collection_name}: {len(results)} results")
                
            except Exception as e:
                print(f"Error querying collection {collection_name}: {e}")
                all_results[collection_name] = []
        
        return all_results

    def query_by_pattern_merged(
            self,
            query_text: str,
            collection_prefix: str,
            n_results: int = 5,
            filter_conditions: Optional[Dict] = None,
            score_threshold: Optional[float] = None
        ) -> list[dict[str, Any]]:
        """
        Query across multiple collections matching a pattern and merge results
        
        Args:
            query_text: Text to search for
            collection_prefix: Prefix pattern to match collections
            n_results: Total number of results to return (merged from all collections)
            filter_conditions: Optional filter conditions for metadata
            score_threshold: Minimum similarity score threshold
            
        Returns:
            Merged and sorted list of results from all matching collections
        """
        # Get results from all matching collections
        all_results = self.query_by_pattern(
            query_text=query_text,
            collection_prefix=collection_prefix,
            n_results=n_results * 2,  # Get more results to ensure we have enough after merging
            filter_conditions=filter_conditions,
            score_threshold=score_threshold
        )
        
        # Merge all results into a single list
        merged_results = []
        for collection_name, results in all_results.items():
            merged_results.extend(results)
        
        # Sort by score (descending)
        merged_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top n_results
        return merged_results[:n_results]
    

    def query_pattern_by_collections(
            self,
            query_text: str,
            collections: list[dict[str, str]],
            n_results: int = 5,
            filter_conditions: Optional[dict] = None,
            score_threshold: Optional[float] = None
        ) -> dict[str, list[dict[str, any]]]:
        """
        Query specific collections by their names
        
        Args:
            query_text: Text to search for
            collections: List of collection dictionaries with 'collection_name' key
                        Example: [{"collection_name": "pdf_docs"}, {"collection_name": "pdf_reports"}]
            n_results: Number of results per collection
            filter_conditions: Optional filter conditions for metadata
            score_threshold: Minimum similarity score threshold
            
        Returns:
            Dictionary with collection names as keys and results as values
        """
        # Generate query embedding once
        query_embedding = self.embedder.encode(query_text).tolist()
        
        # Build filter if provided
        qdrant_filter = None
        if filter_conditions:
            must_conditions = []
            for key, value in filter_conditions.items():
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                )
            qdrant_filter = models.Filter(must=must_conditions)
        
        # Get all available collections for validation
        all_collections = self.client.get_collections().collections
        available_collection_names = [col.name for col in all_collections]
        
        # Extract collection names from the input list
        target_collection_names = [col.get("collection_name") for col in collections if col.get("collection_name")]
        
        # Validate collections exist
        valid_collections = []
        invalid_collections = []
        
        for col_name in target_collection_names:
            if col_name in available_collection_names:
                valid_collections.append(col_name)
            else:
                invalid_collections.append(col_name)
        
        if invalid_collections:
            print(f"Warning: Collections not found: {', '.join(invalid_collections)}")
        
        if not valid_collections:
            print("No valid collections to query")
            return {}
        
        print(f"Querying {len(valid_collections)} collections: {', '.join(valid_collections)}")
        
        # Query each collection
        all_results = {}
        
        for collection_name in valid_collections:
            try:
                # Search in this collection
                search_result = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    query_filter=qdrant_filter,
                    limit=n_results,
                    score_threshold=score_threshold,
                    with_payload=True
                )
                
                # Format results for this collection
                results = []
                for hit in search_result:
                    result = {
                        "id": hit.id,
                        "score": hit.score,
                        "content": hit.payload.get("content", ""),
                        "collection": collection_name,
                        "metadata": {
                            "type": hit.payload.get("type"),
                            "source": hit.payload.get("source"),
                            "page_number": hit.payload.get("page_number"),
                            "chunk_index": hit.payload.get("chunk_index"),
                            "total_chunks": hit.payload.get("total_chunks"),
                        }
                    }
                    
                    # Add image data if available
                    if hit.payload.get("has_image"):
                        result["metadata"]["has_image"] = True
                        result["metadata"]["image_size"] = hit.payload.get("image_size")
                        if "image_base64" in hit.payload:
                            result["image_base64"] = hit.payload["image_base64"]
                    
                    results.append(result)
                
                all_results[collection_name] = results
                print(f"  - {collection_name}: {len(results)} results")
                
            except Exception as e:
                print(f"Error querying collection {collection_name}: {e}")
                all_results[collection_name] = []
        
        return all_results


    #**************************End Search****************************************
        
    
    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        return [item.embedding for item in response.data]

        

    def _chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
        """
        Split text into chunks with overlap
        
        Args:
            text: Text to split
            chunk_size: Maximum size of each chunk
            chunk_overlap: Number of characters to overlap
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < text_length:
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size * 0.5:  # Only break if we have at least half the chunk
                    chunk = text[start:start + break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk)
            start = end - chunk_overlap
            
        return chunks
    
    
    def extract_text_from_pdf_filepath(self, file_name: str, start_page: int = 1, end_page: int = None) -> list[dict[str, Any]]:
        """
        Extract text from PDF file path with page range support
        
        Args:
            file_name: Name of the PDF file in RAG_UPLOAD_DIR
            start_page: Starting page number (1-indexed, inclusive)
            end_page: Ending page number (1-indexed, inclusive). If None, extract to end
            
        Returns:
            List of dictionaries containing page text and metadata
        """
        file_path = os.path.join(RAG_UPLOAD_DIR, file_name)
        with open(file_path, "rb") as pdf_file:
            return self.extract_text_from_pdf_file(pdf_file, filename=os.path.basename(file_name), start_page=start_page, end_page=end_page)

    def extract_text_from_pdf_file(self, pdf_file: Union[BinaryIO, bytes], filename: str = "uploaded.pdf", start_page: int = 1, end_page: int = None) -> list[dict[str, Any]]:
        """
        Extract text from PDF file object
        
        Args:
            pdf_file: File object or bytes from uploaded PDF
            filename: Original filename for reference
            start_page: Starting page number (1-indexed, inclusive)
            end_page: Ending page number (1-indexed, inclusive). If None, extract to end
            
        Returns:
            List of dictionaries containing page text and metadata
        """
        extracted_content = []
        
        try:
            # Handle both file objects and bytes
            if isinstance(pdf_file, bytes):
                pdf_stream = BytesIO(pdf_file)
            else:
                pdf_stream = BytesIO(pdf_file.read())
                
            reader = PdfReader(pdf_stream)
            total_pages = len(reader.pages)
            
            # Set end_page to last page if not specified
            if end_page is None:
                end_page = total_pages
            
            # Validate page range
            start_page = max(1, start_page)
            end_page = min(end_page, total_pages)
            
            for page_num, page in enumerate(reader.pages, 1):
                # Skip pages outside the requested range
                if page_num < start_page or page_num > end_page:
                    continue
                    
                text = page.extract_text()
                
                if text.strip():  # Only add non-empty pages
                    extracted_content.append({
                        "type": "text",
                        "content": text,
                        "page_number": page_num,
                        "source": filename,
                        "total_pages": total_pages
                    })
                    
        except Exception as e:
            print(f"Error extracting text from {filename}: {e}")
            
        return extracted_content
    
    def extract_images_from_pdf_file(self, pdf_file: BinaryIO, filename: str = "uploaded.pdf") -> list[dict[str, Any]]:
        """
        Extract images from PDF file object and apply OCR
        
        Args:
            pdf_file: File object or bytes from uploaded PDF
            filename: Original filename for reference
            
        Returns:
            List of dictionaries containing image data and metadata
        """
        extracted_images = []
        
        try:
            # Convert file object to bytes
            if isinstance(pdf_file, bytes):
                pdf_bytes = pdf_file
            else:
                pdf_file.seek(0)  # Reset file pointer
                pdf_bytes = pdf_file.read()
            
            # Convert PDF pages to images
            images = convert_from_bytes(pdf_bytes)
            
            for page_num, image in enumerate(images, 1):
                # Apply OCR to extract text from image
                ocr_text = pytesseract.image_to_string(image)
                
                # Resize image for storage if too large
                max_size = (800, 800)
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Convert image to base64 for storage
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                extracted_images.append({
                    "type": "image",
                    "content": ocr_text,  # OCR text from image
                    "image_base64": img_base64,  # Full base64 image
                    "page_number": page_num,
                    "source": filename,
                    "image_size": f"{image.width}x{image.height}"
                })
                
        except Exception as e:
            print(f"Error extracting images from {filename}: {e}")
            
        return extracted_images
    def extract_images_from_pdf_filepath(self, file_name: str)-> list[dict[str, Any]]:
        with open(os.path.join(RAG_UPLOAD_DIR, file_name), "rb") as pdf_file:
            return self.extract_images_from_pdf_file(pdf_file, filename=os.path.basename(file_name))
    

    def process_pdf_file_path(
        self, 
        pdf_file: str, 
        start_page: int = 1,
        end_page: int = None, 
        extract_images: bool = True,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> list[dict[str, any]]:
        """
        Process PDF file from file path to extract both text and images with page range support
        
        Args:
            pdf_file: Name of the PDF file in RAG_UPLOAD_DIR
            start_page: Starting page number (1-indexed, inclusive)
            end_page: Ending page number (1-indexed, inclusive). If None, extract to end
            extract_images: Whether to extract images from PDF
            chunk_size: Size of text chunks for better retrieval
            chunk_overlap: Overlap between chunks
            
        Returns:
            Combined list of all extracted content
        """
        all_content = []
        
        # Extract text with page range
        print(f"Extracting text from {pdf_file} (pages {start_page}-{end_page or 'end'})...")
        text_content = self.extract_text_from_pdf_filepath(pdf_file, start_page=start_page, end_page=end_page)
        
        # Chunk text content for better retrieval
        chunked_content = []
        for item in text_content:
            chunks = self._chunk_text(
                item["content"], 
                chunk_size, 
                chunk_overlap
            )
            for i, chunk in enumerate(chunks):
                chunked_item = item.copy()
                chunked_item["content"] = chunk
                chunked_item["chunk_index"] = i
                chunked_item["total_chunks"] = len(chunks)
                chunked_content.append(chunked_item)
        
        all_content.extend(chunked_content)
        
        # Extract images if requested
        if extract_images:
            print(f"Extracting images from {pdf_file}...")
            image_content = self.extract_images_from_pdf_filepath(pdf_file)
            all_content.extend(image_content)
            
        return all_content


    
    def process_pdf_file(
        self, 
        pdf_file: Union[BinaryIO, bytes], 
        filename: str = "uploaded.pdf", 
        extract_images: bool = True,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> list[dict[str, Any]]:
        """
        Process PDF file object to extract both text and images
        
        Args:
            pdf_file: File object or bytes from uploaded PDF
            filename: Original filename for reference
            extract_images: Whether to extract images from PDF
            chunk_size: Size of text chunks for better retrieval
            chunk_overlap: Overlap between chunks
            
        Returns:
            Combined list of all extracted content
        """
        all_content = []
        
        # If it's a file object, read the bytes
        if hasattr(pdf_file, 'read'):
            pdf_file.seek(0)  # Reset file pointer
            pdf_bytes = pdf_file.read()
        else:
            pdf_bytes = pdf_file
        
        # Extract text
        print(f"Extracting text from {filename}...")
        text_content = self.extract_text_from_pdf_file(pdf_bytes, filename)
        
        # Chunk text content for better retrieval
        chunked_content = []
        for item in text_content:
            chunks = self._chunk_text(
                item["content"], 
                chunk_size, 
                chunk_overlap
            )
            for i, chunk in enumerate(chunks):
                chunked_item = item.copy()
                chunked_item["content"] = chunk
                chunked_item["chunk_index"] = i
                chunked_item["total_chunks"] = len(chunks)
                chunked_content.append(chunked_item)
        
        all_content.extend(chunked_content)
        
        # Extract images if requested
        if extract_images:
            print(f"Extracting images from {filename}...")
            image_content = self.extract_images_from_pdf_file(pdf_bytes, filename)
            all_content.extend(image_content)
            
        return all_content
    
    
    def extract_content_and_topic_list(self,text: str) -> str:
        """
        Parse a JSON string of objects and return a JSON string
        with only 'content' and 'topic' fields for each object.
        """
        arr = json.loads(text)
        if not isinstance(arr, list):
            return "[]"
        result = [
            {
                "content": item.get("content", ""),
                "topic": item.get("topic", "")
            }
            for item in arr
        ]
        return json.dumps(result, ensure_ascii=False, indent=2) 
        

    def transform_json_to_list(json_str):
        # json.loads converts a JSON string into a Python object (list/dict)
        data = json.loads(json_str)
        return data
        
    def transform_json_to_list_raw(input_data: str):
        """
        Transform JSON string and return raw list directly.
        """
        results = json.loads(input_data)
        
        if not isinstance(results, list):
            raise HTTPException(
                status_code=400,
                detail="JSON string must be an array/list format"
            )
        
        return results
    
    
    
    def create_data(
        self,
        payload: dict | DataPayload,
        create_collection: bool = True
    ):
       

        
        #return(payload)
        collection_name = payload["collection"]
        
        # Handle different formats of payload["documents"]
        documents_list: list[dict] = []
        
        # Case 1: Already a list of dictionaries
        if isinstance(payload["documents"], list) and len(payload["documents"]) > 0:
            if isinstance(payload["documents"][0], dict):
                # Already in the correct format
                documents_list = payload["documents"]
            elif isinstance(payload["documents"][0], str):
                # List with JSON string - parse it
                json_string_cleaned = payload["documents"][0].replace('```', '')
                documents_list = json.loads(json_string_cleaned)
        # Case 2: Single string containing JSON
        elif isinstance(payload["documents"], str):
            json_string_cleaned = payload["documents"].replace('```', '')
            documents_list = json.loads(json_string_cleaned)
        
        # Transform documents to handle keyword field
        documents = []
        
        for doc in documents_list:
            if not isinstance(doc, dict):
                continue
                
            topic = doc.get("topic", "")
            if topic:
                # Handle both "content" and "description" fields
                content = doc.get("content", "") or doc.get("description", "")
                
                doc_dict = {
                    "topic": topic,
                    "content": content,
                    "metadata": {"keyword": doc.get("keyword", "")} if "keyword" in doc else doc.get("metadata", {})
                }
                documents.append(Document(**doc_dict))

        #text_field= payload["text_field"] if "text_field" in payload else "content"

        #print(documents)
        
        print(f"\n{'='*50}")
        print(f"📦 Processing {len(documents)} documents")
        print(f"📁 Collection: {collection_name}")
        print(f"{'='*50}\n")
        
        # # Ensure collection exists
        if create_collection:
             self.ensure_collection(collection_name)
        
        # # Process in batches
        total_inserted = 0
        results = []
        
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(documents) + self.batch_size - 1) // self.batch_size
            
            print(f"⏳ Processing batch {batch_num}/{total_batches} ({len(batch)} docs)...")
            
            # Generate embeddings for batch
            texts = [doc.get_text_for_embedding() for doc in batch]
            embeddings = self.generate_embeddings(texts)
            #print(embeddings)
            
            # Create points
            points = []
            
            for doc, embedding in zip(batch, embeddings):
                
                point_id = str(uuid.uuid4())
                #print(embedding)



                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=doc.to_payload()
                    )
                                        
                )
                results.append({
                    "id": point_id,
                    "topic": doc.topic
                })

            
            # Upsert to Qdrant
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            total_inserted += len(points)
            print(f"✓ Batch {batch_num} complete - {total_inserted}/{len(documents)} inserted")
        
        print(f"\n{'='*50}")
        print(f"✅ Successfully inserted {total_inserted} documents")
        print(f"{'='*50}\n")
        
        return {
            "status": "success",
            "collection": collection_name,
            "total_inserted": total_inserted,
            "documents": results
        }
    
    def add_vector_db_from_text(
        self,
        payload: dict,
        create_collection: bool = True,
        split_by: str = "paragraph"
    ):
        """
        Add documents to vector DB from plain text instead of JSON.
        
        Args:
            payload: Dictionary containing:
                - collection: Collection name
                - documents: List with single text string or list of text strings
                - topic: Optional topic/title for the text (default: "Document")
            create_collection: Whether to create collection if not exists
            split_by: How to split text ("paragraph", "sentence", "line", or "none")
                     - "paragraph": Split by double newlines
                     - "sentence": Split by periods/question marks
                     - "line": Split by single newlines
                     - "none": Keep as single document
        
        Returns:
            Dictionary with operation status
        """
        collection_name = payload["collection"]
        topic = payload.get("topic", "Document")
        
        # Handle documents - can be string or list
        raw_documents = payload["documents"]
        if isinstance(raw_documents, str):
            text_content = raw_documents
        elif isinstance(raw_documents, list) and len(raw_documents) > 0:
            text_content = raw_documents[0] if isinstance(raw_documents[0], str) else str(raw_documents[0])
        else:
            text_content = ""
        
        # Split text based on strategy
        text_chunks = []
        
        if split_by == "paragraph":
            # Split by double newlines (paragraphs)
            text_chunks = [chunk.strip() for chunk in text_content.split("\n\n") if chunk.strip()]
        elif split_by == "sentence":
            # Split by sentence endings
            import re
            sentences = re.split(r'[.!?]+', text_content)
            text_chunks = [s.strip() for s in sentences if s.strip()]
        elif split_by == "line":
            # Split by single newlines
            text_chunks = [line.strip() for line in text_content.split("\n") if line.strip()]
        else:  # "none" or any other value
            # Keep as single document
            text_chunks = [text_content.strip()] if text_content.strip() else []
        
        if not text_chunks:
            return {
                "status": "error",
                "collection": collection_name,
                "total_inserted": 0,
                "message": "No content to insert after text processing"
            }
        
        # Create Document objects from text chunks
        documents = []
        for idx, chunk in enumerate(text_chunks, 1):
            doc_topic = f"{topic} - Part {idx}" if len(text_chunks) > 1 else topic
            doc_dict = {
                "topic": doc_topic,
                "content": chunk,
                "metadata": {
                    "chunk_index": idx,
                    "total_chunks": len(text_chunks),
                    "split_method": split_by
                }
            }
            documents.append(Document(**doc_dict))
        
        print(f"\n{'='*50}")
        print(f"📝 Processing {len(documents)} text chunks")
        print(f"📁 Collection: {collection_name}")
        print(f"✂️  Split method: {split_by}")
        print(f"{'='*50}\n")
        
        # Ensure collection exists
        if create_collection:
            self.ensure_collection(collection_name)
        
        # Process in batches
        total_inserted = 0
        results = []
        
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(documents) + self.batch_size - 1) // self.batch_size
            
            print(f"⏳ Processing batch {batch_num}/{total_batches} ({len(batch)} docs)...")
            
            # Generate embeddings for batch
            texts = [doc.get_text_for_embedding() for doc in batch]
            embeddings = self.generate_embeddings(texts)
            
            # Create points
            points = []
            
            for doc, embedding in zip(batch, embeddings):
                point_id = str(uuid.uuid4())
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=doc.to_payload()
                    )
                )
                results.append({
                    "id": point_id,
                    "topic": doc.topic
                })
            
            # Upsert to Qdrant
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            total_inserted += len(points)
            print(f"✓ Batch {batch_num} complete - {total_inserted}/{len(documents)} inserted")
        
        print(f"\n{'='*50}")
        print(f"✅ Successfully inserted {total_inserted} text chunks")
        print(f"{'='*50}\n")
        
        return {
            "status": "success",
            "collection": collection_name,
            "total_inserted": total_inserted,
            "split_method": split_by,
            "documents": results
        }
    
    def search(
        self,
        collection_name: str,
        query: str,
        limit: int = 5
    ) -> list[dict]:
        """
        Search documents in collection.
        
        Args:
            collection_name: Name of the collection to search
            query: Search query text
            limit: Maximum number of results
            
        Returns:
            List of matching documents with scores
        """
        # Generate query embedding
        query_embedding = self.generate_embeddings([query])[0]
        
        # Search using query_points
        results = self.qdrant_client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=limit,
            with_payload=True  # Include payload in results
        )
        
        return [
            {
                "id": str(point.id),
                "score": point.score,
                "topic": point.payload.get("topic"),
                "content": point.payload.get("content"),
                "payload": point.payload
            }
            for point in results.points
        ]

    def search_collection_wildcard(
        self,
        collection_name: str,
        query: str,
        limit: int = 5
    ) -> list[dict]:
        """
        Search across all collections whose names start with collection_name (appends * wildcard).

        Args:
            collection_name: Collection name prefix to match (e.g., "physics" matches "physics", "physics_th", "physics_en", etc.)
            query: Search query text
            limit: Maximum number of results to return (total across all matched collections)

        Returns:
            List of matching documents sorted by score

        Example:
            results = creator.search_collection_wildcard(
                collection_name="physics",
                query="Newton's law",
                limit=10
            )
        """
        query_embedding = self.generate_embeddings([query])[0]

        # Get all available collection names
        available_names = [c.name for c in self.qdrant_client.get_collections().collections]

        # Match collections using prefix wildcard
        pattern = re.compile(f"^{re.escape(collection_name)}.*$")
        matched_collections = sorted([name for name in available_names if pattern.match(name)])

        if not matched_collections:
            print(f"⚠️ No collections matched prefix '{collection_name}*'")
            return []

        print(f"🔍 Searching {len(matched_collections)} collections matching '{collection_name}*': {matched_collections}")

        all_results = []

        for coll in matched_collections:
            try:
                results = self.qdrant_client.query_points(
                    collection_name=coll,
                    query=query_embedding,
                    limit=limit,
                    with_payload=True
                )
                all_results.extend([
                    {
                        "id": str(point.id),
                        "score": point.score,
                        "collection": coll,
                        "topic": point.payload.get("topic"),
                        "content": point.payload.get("content"),
                        "payload": point.payload
                    }
                    for point in results.points
                ])
                print(f"  ✓ {coll}: {len(results.points)} results")
            except Exception as e:
                print(f"  ✗ {coll}: Error - {str(e)}")

        all_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = all_results[:limit]

        print(f"📊 Total results: {len(all_results)}, returning top {len(top_results)}")

        return top_results

    async def search_all_async(
        self,
        query: str,
        limit: int = 5
    ) -> list[dict]:
        """Search all collections concurrently."""
        query_embedding = self.generate_embeddings([query])[0]
        collections = self.get_all_collections()
        
        async def search_collection(coll_name: str):
            try:
                results = self.qdrant_client.query_points(
                    collection_name=coll_name,
                    query=query_embedding,
                    limit=limit,
                    with_payload=True
                )
                return [(coll_name, point) for point in results.points]
            except:
                return []
        
        # Run searches concurrently
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            tasks = [
                loop.run_in_executor(executor, search_collection, coll)
                for coll in collections
            ]
            results = await asyncio.gather(*tasks)
        
        # Flatten and format results
        all_results = []
        for coll_results in results:
            for coll_name, point in coll_results:
                all_results.append({
                    "id": str(point.id),
                    "score": point.score,
                    "collection": coll_name,
                    "payload": point.payload
                })
        
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:limit]
        
    def search_all_collections(
            self,
            query: str,
            limit: int = 5
        ) -> list[dict]:
        """
        Search across ALL collections in Qdrant.
        
        Args:
            query: Search query text
            limit: Maximum number of results per collection
            
        Returns:
            List of matching documents from all collections
        """
        # Generate query embedding once
        query_embedding = self.generate_embeddings([query])[0]
        
        # Get all collection names
        collections = self.qdrant_client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        all_results = []
        
        for collection_name in collection_names:
            try:
                results = self.qdrant_client.query_points(
                    collection_name=collection_name,
                    query=query_embedding,
                    limit=limit,
                    with_payload=True
                )
                
                for point in results.points:
                    all_results.append({
                        "id": str(point.id),
                        "score": point.score,
                        "collection": collection_name,  # Track source collection
                        "topic": point.payload.get("topic"),
                        "content": point.payload.get("content"),
                        "payload": point.payload
                    })
            except Exception as e:
                print(f"Error searching {collection_name}: {e}")
                continue
        
        # Sort by score (highest first) and limit total results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:limit]


    
    def search_collections_by_pattern(
        self,
        query: str,
        collection_pattern: str = ".*",  # Regex pattern, ".*" = all
        limit: int = 5
    ) -> list[dict]:
        """
        Search collections matching a pattern.
        
        Args:
            query: Search query text
            collection_pattern: Regex pattern for collection names
                            ".*" = all collections
                            "physics.*" = collections starting with 'physics'
                            ".*_th$" = collections ending with '_th'
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        query_embedding = self.generate_embeddings([query])[0]
        
        # Get matching collections
        collections = self.qdrant_client.get_collections()
        #return collections
        pattern = re.compile(collection_pattern)
        print(pattern)
        matching_collections = [
            c.name for c in collections.collections 
            if pattern.match(c.name)
        ]
        
        all_results = []
        
        for collection_name in matching_collections:
            try:
                results = self.qdrant_client.query_points(
                    collection_name=collection_name,
                    query=query_embedding,
                    limit=limit,
                    with_payload=True
                )
                
                for point in results.points:
                    all_results.append({
                        "id": str(point.id),
                        "score": point.score,
                        "collection": collection_name,
                        "topic": point.payload.get("topic"),
                        "content": point.payload.get("content"),
                        "payload": point.payload
                    })
            except Exception as e:
                continue
        
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:limit]

    
    def search_multiple_collections(
        self,
        query: str,
        collections: list[str],
        limit: int = 5
    ) -> list[dict]:
        """
        Search across multiple collections with pattern matching support.
        
        Args:
            query: Search query text
            collections: List of collection names or patterns to search
                        Supports wildcard patterns:
                        - Exact: ['physics_th', 'chemistry_en']
                        - Wildcard: ['physics*', 'chemistry*', '*_basic']
                        - Regex: ['physics.*', '.*_th$', '^math.*']
            limit: Maximum number of results to return (total across all collections)
            
        Returns:
            List of matching documents sorted by score
            
        Examples:
            # Exact match
            results = creator.search_multiple_collections(
                query="Newton's law",
                collections=['physics_th', 'physics_en'],
                limit=10
            )
            
            # Pattern match
            results = creator.search_multiple_collections(
                query="Newton's law",
                collections=['physics*', 'science*'],
                limit=10
            )
        """
        if not collections:
            print("⚠️ No collections specified, returning empty results")
            return []
        
        # Generate query embedding once
        query_embedding = self.generate_embeddings([query])[0]
        
        # Get all available collection names
        available_names = [c.name for c in self.qdrant_client.get_collections().collections]
        
        # Match collections using patterns
        matched_collections = set()
        
        for pattern in collections:
            # Auto-append wildcard if not present
            pattern_with_wildcard = f"{pattern}*"
            
            # Determine if pattern contains regex special characters
            regex_chars = {'.', '^', '$', '[', ']', '(', ')', '+', '?'}
            is_regex = any(char in pattern for char in regex_chars)
            
            # Build regex pattern
            if '*' in pattern_with_wildcard:
                # Convert wildcard to regex: escape everything, then replace \* with .*
                regex_pattern = f"^{re.escape(pattern_with_wildcard).replace(r'\*', '.*')}$"
            elif is_regex:
                # User provided regex pattern
                regex_pattern = pattern
            else:
                # Exact match
                regex_pattern = f"^{re.escape(pattern)}$"
            
            try:
                compiled_pattern = re.compile(regex_pattern)
                matches = [name for name in available_names if compiled_pattern.match(name)]
                
                if matches:
                    matched_collections.update(matches)
                    print(f"  📋 Pattern '{pattern}' matched: {matches}")
                else:
                    print(f"  ⚠️ Pattern '{pattern}' matched no collections")
                    
            except re.error as e:
                print(f"  ✗ Invalid pattern '{pattern}': {e}")
        
        if not matched_collections:
            print("⚠️ No collections matched the patterns")
            return []
        
        matched_collections = sorted(matched_collections)  # Convert to sorted list
        print(f"🔍 Searching {len(matched_collections)} collections: {matched_collections}")
        
        # Search all matched collections and collect results
        all_results = []
        
        for collection_name in matched_collections:
            try:
                results = self.qdrant_client.query_points(
                    collection_name=collection_name,
                    query=query_embedding,
                    limit=limit,
                    with_payload=True
                )
                
                # Extend results with formatted data
                all_results.extend([
                    {
                        "id": str(point.id),
                        "score": point.score,
                        "collection": collection_name,
                        "topic": point.payload.get("topic"),
                        "content": point.payload.get("content"),
                        "payload": point.payload
                    }
                    for point in results.points
                ])
                
                print(f"  ✓ {collection_name}: {len(results.points)} results")
                
            except Exception as e:
                print(f"  ✗ {collection_name}: Error - {str(e)}")
        
        # Sort by score (highest first) and limit total results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = all_results[:limit]
        
        print(f"📊 Total results: {len(all_results)}, returning top {len(top_results)}")
        
        return top_results


    def get_collection_info(self, collection_name: str) -> dict:
        """Get collection information."""
        info = self.qdrant_client.get_collection(collection_name)
        #return info 
        return info.dict()

    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        self.qdrant_client.delete_collection(collection_name)
        print(f"✓ Deleted collection '{collection_name}'")
        return True


    def build_rag_context_from_search_results(self, search_results: list[dict]) -> str:
        """
        Build RAG context string from search results.
        
        Args:
            search_results: List of search results from search methods
                           Each result should have 'topic', 'content', 'collection', etc.
            
        Returns:
            Formatted context string concatenating all relevant information
        """
        if not search_results:
            return "ไม่พบข้อมูลที่เกี่ยวข้องในฐานข้อมูล"
        
        context_parts = []
        
        for idx, result in enumerate(search_results, 1):
            # Extract information from result
            topic = result.get("topic", "ไม่ระบุหัวข้อ")
            content = result.get("content", "")
            collection = result.get("collection", "")
            score = result.get("score", 0)
            
            # Format each result
            part = f"[{idx}] หัวข้อ: {topic}\n"
            if collection:
                part += f"คอลเลคชั่น: {collection}\n"
            part += f"เนื้อหา: {content}\n"
            part += f"คะแนนความเกี่ยวข้อง: {score:.4f}\n"
            
            context_parts.append(part)
        
        # Join all parts with separator
        rag_context = "\n" + "="*80 + "\n".join(context_parts)
        
        return rag_context


# =============================================================================
# Example Usage
# =============================================================================

# def main():
#     """Example usage of QdrantDataCreator."""
    
#     # Sample data payload
#     sample_payload = {
#         "collection": "physics_knowledge",
#         "documents": [
#             {
#                 "topic": "Newton's First Law",
#                 "content": "An object at rest stays at rest and an object in motion stays in motion with the same speed and in the same direction unless acted upon by an unbalanced force. This is also known as the law of inertia.",
#                 "metadata": {
#                     "keyword": "Newton's first law, inertia, force, motion, physics",
#                     "subject": "physics",
#                     "chapter": "mechanics",
#                     "difficulty": "basic",
#                     "language": "en"
#                 }
#             },
#             {
#                 "topic": "กฎข้อที่สองของนิวตัน",
#                 "content": "แรงลัพธ์ที่กระทำต่อวัตถุ เท่ากับอัตราการเปลี่ยนแปลงโมเมนตัมของวัตถุ หรือ F = ma โดยที่ F คือแรง m คือมวล และ a คือความเร่ง",
#                 "metadata": {
#                     "keyword": "กฎข้อที่สองของนิวตัน, F=ma, แรง, มวล, ความเร่ง",
#                     "subject": "physics",
#                     "chapter": "mechanics",
#                     "difficulty": "basic",
#                     "language": "th"
#                 }
#             },
#             {
#                 "topic": "Kinetic Energy Formula",
#                 "content": "Kinetic energy is the energy an object possesses due to its motion. The formula is KE = ½mv², where m is mass (kg) and v is velocity (m/s). The SI unit of kinetic energy is Joule (J).",
#                 "metadata": {
#                     "keyword": "kinetic energy, KE, ½mv², energy, motion, Joule",
#                     "subject": "physics",
#                     "chapter": "energy",
#                     "difficulty": "basic",
#                     "language": "en"
#                 }
#             },
#             {
#                 "topic": "สมการการเคลื่อนที่",
#                 "content": "สมการการเคลื่อนที่แบบเส้นตรงด้วยความเร่งคงที่: v = u + at, s = ut + ½at², v² = u² + 2as โดย u คือความเร็วต้น v คือความเร็วปลาย a คือความเร่ง t คือเวลา s คือการกระจัด",
#                 "metadata": {
#                     "keyword": "สมการการเคลื่อนที่, v=u+at, s=ut+½at², ความเร่ง, kinematics",
#                     "subject": "physics",
#                     "chapter": "kinematics",
#                     "difficulty": "intermediate",
#                     "language": "th"
#                 }
#             }
#         ]
#     }
    
#     # Initialize creator
#     creator = QdrantDataCreator()
    
#     # Create data
#     result = creator.create_data(sample_payload)
#     print("\n📊 Result:")
#     print(json.dumps(result, indent=2, ensure_ascii=False))
    
#     # Get collection info
#     info = creator.get_collection_info("physics_knowledge")
#     print("\n📁 Collection Info:")
#     print(json.dumps(info, indent=2))
    
#     # Test search
#     print("\n🔍 Search Test: 'Newton force motion'")
#     search_results = creator.search("physics_knowledge", "Newton force motion", limit=3)
#     for i, r in enumerate(search_results, 1):
#         print(f"\n{i}. {r['topic']} (score: {r['score']:.4f})")
#         print(f"   {r['content'][:100]}...")


# if __name__ == "__main__":
#     main()