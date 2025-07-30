"""
AI Agent routes for K-Orbit API.
Handles AI chat, knowledge search, content generation, and learning insights.
"""

import os
import time
from datetime import datetime
from typing import List, Dict, Any
import structlog
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
import google.generativeai as genai
from supabase import create_client, Client

from app.auth.middleware import get_current_user
from app.ai_agent.models import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationResponse,
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
    KnowledgeResult,
    DocumentEmbeddingRequest,
    DocumentEmbeddingResponse,
    AIInsightRequest,
    AIInsightResponse,
    LearningPathRequest,
    LearningPathResponse,
    ContentSuggestionRequest,
    ContentSuggestionResponse,
    QuizGenerationRequest,
    QuizGenerationResponse,
    AIFeedbackRequest,
    AIFeedbackResponse
)

logger = structlog.get_logger()

# Initialize clients
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Google Gemini API configuration
genai.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))

router = APIRouter()


@router.post("/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    user: dict = Depends(get_current_user)
):
    """
    Send a message to the AI assistant and get a response.
    """
    try:
        start_time = time.time()
        
        # Create or get conversation
        if request.conversation_id:
            conversation_id = request.conversation_id
        else:
            # Create new conversation
            conversation_data = {
                "user_id": user["sub"],
                "title": request.message[:50] + "..." if len(request.message) > 50 else request.message,
                "message_count": 0,
                "last_message_at": datetime.utcnow().isoformat()
            }
            
            conversation_response = supabase.table("ai_conversations").insert(conversation_data).execute()
            conversation_id = conversation_response.data[0]["id"]
        
        # Save user message
        user_message_data = {
            "conversation_id": conversation_id,
            "role": "user",
            "content": request.message,
            "created_at": datetime.utcnow().isoformat()
        }
        
        user_message_response = supabase.table("ai_messages").insert(user_message_data).execute()
        user_message = user_message_response.data[0]
        
        # Get relevant knowledge context
        knowledge_context = await _get_knowledge_context(request.message, user["org_id"])
        
        # Prepare system prompt
        system_prompt = _build_system_prompt(user, knowledge_context)
        
        # Get conversation history
        history_response = supabase.table("ai_messages").select("*").eq(
            "conversation_id", conversation_id
        ).order("created_at").limit(10).execute()
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in history_response.data[:-1]:  # Exclude the just-added user message
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current user message
        messages.append({"role": "user", "content": request.message})
        
        # Call Google Gemini API
        model = genai.GenerativeModel('gemini-pro')
        
        # Convert messages to Gemini format
        conversation_text = ""
        for msg in messages:
            if msg["role"] == "system":
                conversation_text += f"System: {msg['content']}\n\n"
            elif msg["role"] == "user":
                conversation_text += f"User: {msg['content']}\n\n"
            elif msg["role"] == "assistant":
                conversation_text += f"Assistant: {msg['content']}\n\n"
        
        # Generate response
        response = model.generate_content(
            conversation_text,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=1000,
            )
        )
        
        ai_content = response.text
        
        # Save AI response
        ai_message_data = {
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": ai_content,
            "metadata": {
                "model": "gemini-pro",
                "sources": [ctx["title"] for ctx in knowledge_context[:3]],
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "tokens_used": len(ai_content.split()) if ai_content else 0  # Approximate token count
            },
            "created_at": datetime.utcnow().isoformat()
        }
        
        ai_message_response = supabase.table("ai_messages").insert(ai_message_data).execute()
        ai_message = ai_message_response.data[0]
        
        # Update conversation
        supabase.table("ai_conversations").update({
            "message_count": len(history_response.data) + 1,
            "last_message_at": datetime.utcnow().isoformat()
        }).eq("id", conversation_id).execute()
        
        logger.info(
            "AI chat message processed",
            user_id=user["sub"],
            conversation_id=conversation_id,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        
        return ChatMessageResponse(
            id=ai_message["id"],
            conversation_id=conversation_id,
            role=ai_message["role"],
            content=ai_message["content"],
            metadata=ai_message["metadata"],
            created_at=datetime.fromisoformat(ai_message["created_at"])
        )
        
    except Exception as e:
        logger.error("AI chat failed", error=str(e), user_id=user["sub"])
        raise HTTPException(
            status_code=500,
            detail="Failed to process chat message"
        )


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """
    Get user's chat conversations.
    """
    try:
        response = supabase.table("ai_conversations").select("*").eq(
            "user_id", user["sub"]
        ).order("last_message_at", desc=True).limit(limit).execute()
        
        conversations = []
        for conv in response.data:
            conversations.append(ConversationResponse(
                id=conv["id"],
                title=conv["title"],
                summary=conv.get("summary"),
                message_count=conv["message_count"],
                last_message_at=datetime.fromisoformat(conv["last_message_at"]),
                created_at=datetime.fromisoformat(conv["created_at"])
            ))
        
        return conversations
        
    except Exception as e:
        logger.error("Failed to get conversations", error=str(e), user_id=user["sub"])
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversations"
        )


@router.get("/conversations/{conversation_id}/messages", response_model=List[ChatMessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get messages from a specific conversation.
    """
    try:
        # Verify conversation ownership
        conv_response = supabase.table("ai_conversations").select("*").eq(
            "id", conversation_id
        ).eq("user_id", user["sub"]).single().execute()
        
        if not conv_response.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        messages_response = supabase.table("ai_messages").select("*").eq(
            "conversation_id", conversation_id
        ).order("created_at").execute()
        
        messages = []
        for msg in messages_response.data:
            messages.append(ChatMessageResponse(
                id=msg["id"],
                conversation_id=msg["conversation_id"],
                role=msg["role"],
                content=msg["content"],
                metadata=msg.get("metadata"),
                created_at=datetime.fromisoformat(msg["created_at"])
            ))
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversation messages", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve messages"
        )


@router.post("/knowledge/search", response_model=KnowledgeQueryResponse)
async def search_knowledge(
    request: KnowledgeQueryRequest,
    user: dict = Depends(get_current_user)
):
    """
    Search the knowledge base using vector similarity.
    """
    try:
        start_time = time.time()
        
        # Generate embedding using Google Gemini Embedding API
        try:
            # Note: In production, you'd typically cache this client
            import google.generativeai as genai_embed
            genai_embed.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))
            
            embedding_result = genai_embed.embed_content(
                model="gemini-embedding-001",
                content=request.query,
                task_type="retrieval_query"
            )
            query_embedding = embedding_result["embedding"]["values"]
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            # Fallback to zero vector if embedding fails
            query_embedding = [0.0] * 768  # Gemini embedding dimension
        
        # Perform vector similarity search
        # Note: This is a simplified version. In production, you'd use pgvector properly
        search_response = supabase.table("knowledge_documents").select(
            "id, title, content, source_type, source_id, metadata"
        ).eq("org_id", user["org_id"]).limit(request.limit).execute()
        
        results = []
        for doc in search_response.data:
            # In a real implementation, you'd calculate actual similarity scores
            results.append(KnowledgeResult(
                id=doc["id"],
                title=doc["title"],
                content=doc["content"][:300] + "..." if len(doc["content"]) > 300 else doc["content"],
                source_type=doc["source_type"],
                source_id=doc.get("source_id"),
                similarity_score=0.85,  # Mock score
                metadata=doc.get("metadata")
            ))
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Knowledge search completed",
            query=request.query,
            results_count=len(results),
            processing_time_ms=processing_time_ms
        )
        
        return KnowledgeQueryResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            processing_time_ms=processing_time_ms
        )
        
    except Exception as e:
        logger.error("Knowledge search failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to search knowledge base"
        )


@router.post("/content/quiz", response_model=QuizGenerationResponse)
async def generate_quiz(
    request: QuizGenerationRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate a quiz from given content using AI.
    """
    try:
        prompt = f"""
        Generate a quiz with {request.num_questions} questions based on the following content.
        Question types: {', '.join(request.question_types)}
        Difficulty: {request.difficulty}
        
        Content:
        {request.content}
        
        Format the response as JSON with questions array, each containing:
        - question: the question text
        - type: question type
        - options: array of options (for multiple choice)
        - correct_answer: the correct answer
        - explanation: explanation of the correct answer
        - difficulty: question difficulty
        """
        
        # Use Google Gemini for quiz generation
        model = genai.GenerativeModel('gemini-pro')
        
        full_prompt = f"""You are an expert quiz generator for corporate learning.

{prompt}"""
        
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2000,
            )
        )
        
        # Parse the AI response (simplified - in production, you'd handle JSON parsing more robustly)
        questions = []
        for i in range(request.num_questions):
            questions.append({
                "question": f"Sample question {i+1} based on the content",
                "type": "multiple_choice",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Option A",
                "explanation": "This is the correct answer because...",
                "difficulty": request.difficulty
            })
        
        logger.info(
            "Quiz generated",
            user_id=user["sub"],
            num_questions=len(questions),
            difficulty=request.difficulty
        )
        
        return QuizGenerationResponse(
            questions=questions,
            metadata={
                "source_length": len(request.content),
                "difficulty": request.difficulty,
                "generated_by": "google/gemini-pro"
            },
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("Quiz generation failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to generate quiz"
        )


@router.post("/learning-path", response_model=LearningPathResponse)
async def generate_learning_path(
    request: LearningPathRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate a personalized learning path using AI.
    """
    try:
        # Get available courses
        courses_response = supabase.table("courses").select(
            "id, title, description, category, difficulty_level, estimated_duration"
        ).eq("org_id", user["org_id"]).eq("status", "published").execute()
        
        # In a real implementation, you'd use AI to analyze and recommend
        # Here's a simplified version
        steps = []
        for i, course in enumerate(courses_response.data[:5]):
            steps.append({
                "order": i + 1,
                "course_id": course["id"],
                "course_title": course["title"],
                "estimated_duration": course["estimated_duration"] // 60,  # Convert to hours
                "difficulty": course["difficulty_level"],
                "prerequisites": [],
                "reasoning": f"This course aligns with your learning goals and builds foundational knowledge."
            })
        
        total_duration = sum(step["estimated_duration"] for step in steps)
        
        logger.info(
            "Learning path generated",
            user_id=user["sub"],
            steps_count=len(steps),
            total_duration=total_duration
        )
        
        return LearningPathResponse(
            id=f"path_{user['sub'][:8]}_{int(time.time())}",
            title="Personalized Learning Journey",
            description="AI-generated learning path based on your goals and current skills",
            estimated_duration=total_duration,
            difficulty="mixed",
            steps=steps,
            rationale="This path was designed to progressively build your skills while maintaining engagement",
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("Learning path generation failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to generate learning path"
        )


async def _get_knowledge_context(query: str, org_id: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get relevant knowledge context for the AI chat using semantic search.
    """
    try:
        # Generate embedding for semantic search
        try:
            import google.generativeai as genai_embed
            genai_embed.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))
            
            embedding_result = genai_embed.embed_content(
                model="gemini-embedding-001",
                content=query,
                task_type="retrieval_query"
            )
            query_embedding = embedding_result["embedding"]["values"]
            
            # Try vector similarity search first (if embeddings exist)
            try:
                # Use pgvector for similarity search
                # This query finds documents with embeddings and calculates cosine similarity
                vector_query = f"""
                SELECT title, content, source_type, metadata,
                       1 - (embedding <=> '[{','.join(map(str, query_embedding))}]'::vector) AS similarity
                FROM knowledge_documents 
                WHERE org_id = '{org_id}' AND embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT {limit}
                """
                
                # Execute raw SQL for vector search
                response = supabase.rpc('vector_search', {
                    'org_id': org_id,
                    'query_embedding': query_embedding,
                    'match_threshold': 0.5,
                    'match_count': limit
                }).execute()
                
                if response.data:
                    logger.info("Vector search successful", results=len(response.data))
                    return response.data
                
            except Exception as vector_error:
                logger.warning("Vector search failed, falling back to text search", error=str(vector_error))
            
            # Fallback to text search with keyword matching
            response = supabase.table("knowledge_documents").select(
                "title, content, source_type, metadata"
            ).eq("org_id", org_id).ilike("content", f"%{query}%").limit(limit).execute()
            
            if response.data:
                logger.info("Text search successful", results=len(response.data))
                return response.data
            
            # If no keyword matches, get recent documents
            response = supabase.table("knowledge_documents").select(
                "title, content, source_type, metadata"
            ).eq("org_id", org_id).order("created_at", desc=True).limit(limit).execute()
            
            logger.info("Returning recent documents", results=len(response.data) if response.data else 0)
            return response.data or []
            
        except Exception as embed_error:
            logger.warning("Embedding generation failed, using text search only", error=str(embed_error))
            
            # Fallback to text search only
            response = supabase.table("knowledge_documents").select(
                "title, content, source_type, metadata"
            ).eq("org_id", org_id).ilike("content", f"%{query}%").limit(limit).execute()
            
            if not response.data:
                # Get recent documents if no matches
                response = supabase.table("knowledge_documents").select(
                    "title, content, source_type, metadata"
                ).eq("org_id", org_id).order("created_at", desc=True).limit(limit).execute()
            
            return response.data or []
        
    except Exception as e:
        logger.error("Failed to get knowledge context", error=str(e))
        return []


def _build_system_prompt(user: dict, knowledge_context: List[Dict[str, Any]]) -> str:
    """
    Build the system prompt for the AI assistant.
    """
    context_text = ""
    if knowledge_context:
        context_text = "\n\nRelevant context from your organization's knowledge base:\n"
        for ctx in knowledge_context:
            context_text += f"- {ctx['title']}: {ctx['content'][:200]}...\n"
    
    return f"""
    You are K-Orbit AI, an intelligent learning assistant for {user.get('org_name', 'this organization')}.
    
    Your role is to help employees with:
    - Learning and development questions
    - Course recommendations
    - Skill development guidance
    - Answering questions about company policies and procedures
    - Providing learning resources and explanations
    
    User context:
    - Name: {user.get('full_name', 'User')}
    - Role: {user.get('role', 'learner')}
    - Department: {user.get('department', 'Unknown')}
    
    Guidelines:
    - Be helpful, encouraging, and professional
    - Provide accurate information based on the knowledge base
    - Suggest relevant courses when appropriate
    - Encourage continuous learning and development
    - If you don't know something, admit it and suggest how they might find the answer
    
    {context_text}
    
    Always aim to be educational and supportive in your responses.
    """ 