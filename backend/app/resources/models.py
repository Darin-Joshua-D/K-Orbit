"""
Resource management models for K-Orbit API.
Pydantic models for file uploads, document processing, and knowledge management.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response model for file uploads."""
    id: str = Field(..., description="File upload ID")
    filename: str = Field(..., description="Generated filename")
    original_name: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="File MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    url: str = Field(..., description="File URL")
    is_processed: bool = Field(..., description="Whether file has been processed")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


class DocumentProcessingResponse(BaseModel):
    """Response model for document processing status."""
    file_id: str = Field(..., description="File ID")
    status: str = Field(..., description="Processing status")
    extracted_text_length: Optional[int] = Field(None, description="Length of extracted text")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class KnowledgeDocumentResponse(BaseModel):
    """Response model for knowledge documents."""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content (truncated)")
    source_type: str = Field(..., description="Source type (upload, manual, course, etc.)")
    source_id: Optional[str] = Field(None, description="Source ID if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class CreateKnowledgeDocumentRequest(BaseModel):
    """Request model for creating knowledge documents."""
    title: str = Field(..., min_length=1, max_length=255, description="Document title")
    content: str = Field(..., min_length=1, description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class UpdateKnowledgeDocumentRequest(BaseModel):
    """Request model for updating knowledge documents."""
    title: str = Field(..., min_length=1, max_length=255, description="Document title")
    content: str = Field(..., min_length=1, description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DocumentSearchRequest(BaseModel):
    """Request model for searching documents."""
    query: Optional[str] = Field(None, description="Search query")
    source_type: Optional[str] = Field(None, description="Filter by source type")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")


class DocumentSearchResponse(BaseModel):
    """Response model for document search results."""
    documents: List[KnowledgeDocumentResponse] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total number of results")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether there are more results")


class FileUpload(BaseModel):
    """File upload record model."""
    id: str = Field(..., description="Upload ID")
    filename: str = Field(..., description="Generated filename")
    original_name: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="File MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    url: str = Field(..., description="File URL")
    uploaded_by: str = Field(..., description="User ID who uploaded")
    org_id: str = Field(..., description="Organization ID")
    is_processed: bool = Field(default=False, description="Processing status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata")
    created_at: datetime = Field(..., description="Upload timestamp")


class KnowledgeDocument(BaseModel):
    """Knowledge document model."""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content")
    source_type: str = Field(..., description="Source type")
    source_id: Optional[str] = Field(None, description="Source ID")
    org_id: str = Field(..., description="Organization ID")
    embedding: Optional[List[float]] = Field(None, description="Document embedding vector")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class EmbeddingRequest(BaseModel):
    """Request model for generating embeddings."""
    text: str = Field(..., min_length=1, description="Text to embed")
    task_type: str = Field(default="retrieval_document", description="Task type for embedding")


class EmbeddingResponse(BaseModel):
    """Response model for embedding generation."""
    embedding: List[float] = Field(..., description="Generated embedding vector")
    dimension: int = Field(..., description="Embedding dimension")
    model: str = Field(..., description="Model used for embedding")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


class DocumentAnalyticsResponse(BaseModel):
    """Response model for document analytics."""
    total_documents: int = Field(..., description="Total number of documents")
    documents_by_source: Dict[str, int] = Field(..., description="Document count by source type")
    recent_uploads: List[FileUploadResponse] = Field(..., description="Recent uploads")
    most_accessed: List[KnowledgeDocumentResponse] = Field(..., description="Most accessed documents")
    storage_usage_bytes: int = Field(..., description="Total storage usage in bytes")


class BulkUploadRequest(BaseModel):
    """Request model for bulk upload operations."""
    source_urls: List[str] = Field(..., description="List of URLs to import")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata for all uploads")


class BulkUploadResponse(BaseModel):
    """Response model for bulk upload operations."""
    total_requested: int = Field(..., description="Total number of URLs requested")
    successfully_uploaded: int = Field(..., description="Number of successful uploads")
    failed_uploads: List[Dict[str, str]] = Field(..., description="Failed uploads with errors")
    upload_ids: List[str] = Field(..., description="IDs of successful uploads")


class DocumentValidationResponse(BaseModel):
    """Response model for document validation."""
    is_valid: bool = Field(..., description="Whether document is valid")
    issues: List[str] = Field(default_factory=list, description="Validation issues found")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    quality_score: float = Field(..., description="Document quality score (0-1)")


class ResourceHealthResponse(BaseModel):
    """Health check response for resources service."""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    timestamp: datetime = Field(..., description="Health check timestamp")
    storage_connectivity: bool = Field(..., description="Storage service connectivity")
    database_connectivity: bool = Field(..., description="Database connectivity") 