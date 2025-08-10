"""
Resource management routes for K-Orbit API.
Handles file uploads, document processing, and knowledge base management.
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Query, BackgroundTasks
from supabase import create_client, Client

from app.auth.middleware import get_current_user, require_sme, require_manager
from app.resources.models import (
    FileUploadResponse,
    DocumentProcessingResponse,
    KnowledgeDocumentResponse,
    CreateKnowledgeDocumentRequest,
    UpdateKnowledgeDocumentRequest,
    DocumentSearchRequest,
    DocumentSearchResponse
)

logger = structlog.get_logger()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

router = APIRouter()

# Allowed file types and size limits
ALLOWED_FILE_TYPES = {
    # Documents
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
    
    # Spreadsheets
    "text/csv": ".csv",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    
    # Images (for OCR)
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    
    # Videos (for transcript extraction)
    "video/mp4": ".mp4",
    "video/avi": ".avi",
    "video/mov": ".mov",
    "video/wmv": ".wmv",
    
    # Audio (for transcript extraction)
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/m4a": ".m4a"
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB (increased for videos)


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(require_sme)
):
    """
    Upload a file to the knowledge base (SME and managers only).
    """
    try:
        # Validate file type
        if file.content_type not in ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file.content_type} not supported"
            )
        
        # Validate file size
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Generate unique filename
        file_extension = ALLOWED_FILE_TYPES[file.content_type]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Upload to Supabase Storage
        storage_response = supabase.storage.from_("knowledge-documents").upload(
            unique_filename, 
            file_content,
            {"content-type": file.content_type}
        )
        
        if storage_response.get("error"):
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")
        
        # Get public URL
        public_url = supabase.storage.from_("knowledge-documents").get_public_url(unique_filename)
        
        # Save file metadata to database
        file_data = {
            "filename": unique_filename,
            "original_name": file.filename,
            "mime_type": file.content_type,
            "size_bytes": len(file_content),
            "url": public_url.get("publicURL", ""),
            "uploaded_by": user["sub"],
            "org_id": user["org_id"],
            "is_processed": False,
            "metadata": {
                "upload_ip": "unknown",  # In production, capture real IP
                "user_agent": "unknown"  # In production, capture real user agent
            }
        }
        
        file_response = supabase.table("file_uploads").insert(file_data).execute()
        uploaded_file = file_response.data[0]
        
        # Schedule background processing
        background_tasks.add_task(process_document, uploaded_file["id"], file_content, user["org_id"])
        
        logger.info(
            "File uploaded successfully",
            file_id=uploaded_file["id"],
            filename=file.filename,
            user_id=user["sub"]
        )
        
        return FileUploadResponse(
            id=uploaded_file["id"],
            filename=uploaded_file["filename"],
            original_name=uploaded_file["original_name"],
            mime_type=uploaded_file["mime_type"],
            size_bytes=uploaded_file["size_bytes"],
            url=uploaded_file["url"],
            is_processed=uploaded_file["is_processed"],
            uploaded_at=uploaded_file["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload file", error=str(e), filename=file.filename)
        raise HTTPException(status_code=500, detail="Failed to upload file")


async def process_document(file_id: str, content: bytes, org_id: str):
    """
    Background task to process uploaded document and extract content.
    """
    try:
        import io
        import PyPDF2
        import docx
        import pandas as pd
        from PIL import Image
        import pytesseract
        import google.generativeai as genai_embed
        
        # Configure Gemini for embeddings
        genai_embed.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))
        
        extracted_text = ""
        file_info = supabase.table("file_uploads").select("*").eq("id", file_id).execute()
        if not file_info.data:
            raise Exception("File not found")
        
        file_data = file_info.data[0]
        filename = file_data["filename"]
        mime_type = file_data["mime_type"]
        
        # Extract text based on file type
        if mime_type == "application/pdf":
            # PDF processing
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                extracted_text += page.extract_text() + "\n"
                
        elif mime_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            # Word document processing
            if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                doc_file = io.BytesIO(content)
                doc = docx.Document(doc_file)
                for paragraph in doc.paragraphs:
                    extracted_text += paragraph.text + "\n"
            else:
                # .doc files need special handling (for production, use python-docx2txt)
                extracted_text = "DOC file processing requires additional setup. Please use DOCX format."
                
        elif mime_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "text/csv"]:
            # Excel/CSV processing
            try:
                if mime_type == "text/csv":
                    df = pd.read_csv(io.BytesIO(content))
                else:
                    df = pd.read_excel(io.BytesIO(content))
                
                # Convert dataframe to text representation
                extracted_text = f"Spreadsheet Data:\n"
                extracted_text += f"Columns: {', '.join(df.columns.tolist())}\n"
                extracted_text += f"Rows: {len(df)}\n\n"
                extracted_text += df.to_string(max_rows=100)  # Limit to first 100 rows
            except Exception as e:
                extracted_text = f"Error processing spreadsheet: {str(e)}"
                
        elif mime_type.startswith("image/"):
            # Image OCR processing
            try:
                image = Image.open(io.BytesIO(content))
                extracted_text = pytesseract.image_to_string(image)
                if not extracted_text.strip():
                    extracted_text = "No text found in image"
            except Exception as e:
                extracted_text = f"Error processing image: {str(e)}"
                
        elif mime_type.startswith("video/") or mime_type.startswith("audio/"):
            # Video/Audio processing (placeholder - requires additional setup)
            extracted_text = f"Video/Audio file uploaded: {filename}. Transcript extraction requires additional setup with speech-to-text services."
            
        elif mime_type in ["text/plain", "text/markdown"]:
            # Text file processing
            try:
                extracted_text = content.decode('utf-8')
            except UnicodeDecodeError:
                extracted_text = content.decode('utf-8', errors='ignore')
        else:
            extracted_text = f"Unsupported file type: {mime_type}"
        
        # Limit content length
        if len(extracted_text) > 10000:
            extracted_text = extracted_text[:10000] + "... (content truncated)"
        
        # Generate embeddings using Google Gemini
        embedding_vector = None
        try:
            if extracted_text.strip():
                embedding_result = genai_embed.embed_content(
                    model="gemini-embedding-001",
                    content=extracted_text,
                    task_type="retrieval_document"
                )
                embedding_vector = embedding_result["embedding"]["values"]
                logger.info("Generated embedding for document", file_id=file_id, embedding_dim=len(embedding_vector))
        except Exception as e:
            logger.warning("Failed to generate embedding", error=str(e), file_id=file_id)
        
        # Update file as processed
        supabase.table("file_uploads").update({"is_processed": True}).eq("id", file_id).execute()
        
        # Create knowledge document with embedding
        knowledge_doc = {
            "title": file_data["original_name"],  # Use original filename as title
            "content": extracted_text,
            "source_type": "upload",
            "source_id": file_id,
            "org_id": org_id,
            "embedding": embedding_vector,  # Store the actual embedding
            "metadata": {
                "processing_date": datetime.utcnow().isoformat(),
                "content_length": len(extracted_text),
                "mime_type": mime_type,
                "original_filename": file_data["original_name"],
                "file_size": file_data["size_bytes"]
            }
        }
        
        supabase.table("knowledge_documents").insert(knowledge_doc).execute()
        
        logger.info("Document processed successfully", 
                   file_id=file_id, 
                   text_length=len(extracted_text),
                   has_embedding=embedding_vector is not None)
        
    except Exception as e:
        logger.error("Failed to process document", error=str(e), file_id=file_id)
        # Mark as processed even if failed to avoid retry loops
        try:
            supabase.table("file_uploads").update({
                "is_processed": True,
                "processing_error": str(e)
            }).eq("id", file_id).execute()
        except:
            pass


@router.get("/uploads", response_model=List[FileUploadResponse])
async def list_uploads(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """
    List uploaded files.
    """
    try:
        offset = (page - 1) * limit
        
        # Build query based on user role
        query = supabase.table("file_uploads").select("*")
        
        if user.get("role") == "manager":
            # Managers can see all org files
            query = query.eq("org_id", user["org_id"])
        elif user.get("role") == "sme":
            # SMEs can see all org files
            query = query.eq("org_id", user["org_id"])
        else:
            # Learners can only see their own uploads
            query = query.eq("uploaded_by", user["sub"])
        
        response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        uploads = []
        for upload in response.data:
            uploads.append(FileUploadResponse(
                id=upload["id"],
                filename=upload["filename"],
                original_name=upload["original_name"],
                mime_type=upload["mime_type"],
                size_bytes=upload["size_bytes"],
                url=upload["url"],
                is_processed=upload["is_processed"],
                uploaded_at=upload["created_at"]
            ))
        
        return uploads
        
    except Exception as e:
        logger.error("Failed to list uploads", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve uploads")


@router.get("/knowledge-documents", response_model=DocumentSearchResponse)
async def search_knowledge_documents(
    query: Optional[str] = Query(None, description="Search query"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """
    Search knowledge documents.
    """
    try:
        offset = (page - 1) * limit
        
        # Build search query
        db_query = supabase.table("knowledge_documents").select("*").eq("org_id", user["org_id"])
        
        if source_type:
            db_query = db_query.eq("source_type", source_type)
        
        if query:
            # Simple text search (in production, use vector similarity)
            db_query = db_query.ilike("content", f"%{query}%")
        
        response = db_query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        documents = []
        for doc in response.data:
            documents.append(KnowledgeDocumentResponse(
                id=doc["id"],
                title=doc["title"],
                content=doc["content"][:500] + "..." if len(doc["content"]) > 500 else doc["content"],
                source_type=doc["source_type"],
                source_id=doc.get("source_id"),
                metadata=doc.get("metadata", {}),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"]
            ))
        
        return DocumentSearchResponse(
            documents=documents,
            total_count=len(response.data),
            page=page,
            limit=limit,
            has_more=len(response.data) == limit
        )
        
    except Exception as e:
        logger.error("Failed to search knowledge documents", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to search documents")


@router.post("/knowledge-documents", response_model=KnowledgeDocumentResponse)
async def create_knowledge_document(
    request: CreateKnowledgeDocumentRequest,
    user: dict = Depends(require_sme)
):
    """
    Create a knowledge document manually (SME and managers only).
    """
    try:
        doc_data = {
            "title": request.title,
            "content": request.content,
            "source_type": "manual",
            "source_id": None,
            "org_id": user["org_id"],
            "metadata": {
                "created_by": user["sub"],
                "manual_entry": True,
                **request.metadata
            }
        }
        
        response = supabase.table("knowledge_documents").insert(doc_data).execute()
        doc = response.data[0]
        
        return KnowledgeDocumentResponse(
            id=doc["id"],
            title=doc["title"],
            content=doc["content"],
            source_type=doc["source_type"],
            source_id=doc.get("source_id"),
            metadata=doc.get("metadata", {}),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )
        
    except Exception as e:
        logger.error("Failed to create knowledge document", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create document")


@router.put("/knowledge-documents/{document_id}", response_model=KnowledgeDocumentResponse)
async def update_knowledge_document(
    document_id: str,
    request: UpdateKnowledgeDocumentRequest,
    user: dict = Depends(require_sme)
):
    """
    Update a knowledge document (SME and managers only).
    """
    try:
        # Check if document exists and user has permission
        existing_doc = supabase.table("knowledge_documents").select("*").eq(
            "id", document_id
        ).eq("org_id", user["org_id"]).execute()
        
        if not existing_doc.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Update document
        update_data = {
            "title": request.title,
            "content": request.content,
            "metadata": {
                **existing_doc.data[0].get("metadata", {}),
                "updated_by": user["sub"],
                "last_modified": datetime.utcnow().isoformat(),
                **request.metadata
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = supabase.table("knowledge_documents").update(update_data).eq("id", document_id).execute()
        doc = response.data[0]
        
        return KnowledgeDocumentResponse(
            id=doc["id"],
            title=doc["title"],
            content=doc["content"],
            source_type=doc["source_type"],
            source_id=doc.get("source_id"),
            metadata=doc.get("metadata", {}),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update knowledge document", error=str(e), document_id=document_id)
        raise HTTPException(status_code=500, detail="Failed to update document")


@router.delete("/knowledge-documents/{document_id}")
async def delete_knowledge_document(
    document_id: str,
    user: dict = Depends(require_sme)
):
    """
    Delete a knowledge document (SME and managers only).
    """
    try:
        # Check if document exists and user has permission
        existing_doc = supabase.table("knowledge_documents").select("*").eq(
            "id", document_id
        ).eq("org_id", user["org_id"]).execute()
        
        if not existing_doc.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete document
        supabase.table("knowledge_documents").delete().eq("id", document_id).execute()
        
        logger.info("Knowledge document deleted", document_id=document_id, user_id=user["sub"])
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete knowledge document", error=str(e), document_id=document_id)
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/health")
async def resources_health():
    """
    Health check for resources service.
    """
    return {
        "status": "healthy",
        "service": "resources",
        "timestamp": datetime.utcnow().isoformat()
    } 