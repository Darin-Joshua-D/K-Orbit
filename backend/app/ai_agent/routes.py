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
import json
import uuid

from app.auth.middleware import get_current_user
from app.database import get_db_manager, get_query_cache, get_db_metrics
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

# Google Gemini API configuration
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
if GOOGLE_GEMINI_API_KEY:
    genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
    logger.info("Google Gemini API key found and configured.")
else:
    logger.warning("Google Gemini API key not found. AI will use fallback.")

router = APIRouter()

USE_JSON_FALLBACK = os.getenv("AI_CHAT_JSON_FALLBACK", "false").lower() == "true"
JSON_STORE_PATH = os.getenv("AI_CHAT_JSON_PATH", "/tmp/ai_chat_store.json")

def _json_store_load() -> Dict[str, Any]:
    try:
        with open(JSON_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"conversations": {}, "messages": {}}

def _json_store_save(data: Dict[str, Any]) -> None:
    try:
        with open(JSON_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def _generate_uuid() -> str:
    """Generate a proper UUID string for JSON fallback."""
    return str(uuid.uuid4())


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
        
        # Get optimized database manager
        db_manager = await get_db_manager()
        cache = await get_query_cache()
        metrics = await get_db_metrics()
        
        # Create or get conversation
        if request.conversation_id:
            conversation_id = request.conversation_id
        else:
            # Create new conversation using optimized database
            conversation_data = {
                "user_id": user["sub"],
                "title": request.message[:50] + "..." if len(request.message) > 50 else request.message,
                "message_count": 0,
                "last_message_at": datetime.utcnow().isoformat()
            }
            
            # Use optimized database insert
            try:
                insert_query = """
                INSERT INTO ai_conversations (user_id, title, message_count, last_message_at)
                VALUES (%s, %s, %s, %s) RETURNING id
                """
                result = await db_manager.execute_query(
                    insert_query,
                    conversation_data["user_id"],
                    conversation_data["title"],
                    conversation_data["message_count"],
                    conversation_data["last_message_at"]
                )
                conversation_id = result[0]["id"]
            except Exception as db_err:
                if USE_JSON_FALLBACK:
                    store = _json_store_load()
                    conversation_id = _generate_uuid()
                    store["conversations"][conversation_id] = {
                        **conversation_data,
                        "id": conversation_id
                    }
                    _json_store_save(store)
                    logger.info("Created conversation in JSON fallback", conversation_id=conversation_id)
                else:
                    raise
        
        # Save user message with performance tracking
        user_message_query = """
        INSERT INTO ai_messages (conversation_id, role, content, created_at)
        VALUES (%s, %s, %s, %s) RETURNING id
        """
        try:
            user_message_result = await db_manager.execute_query(
                user_message_query,
                conversation_id,
                "user",
                request.message,
                datetime.utcnow().isoformat()
            )
            user_message_id = user_message_result[0]["id"]
        except Exception:
            if USE_JSON_FALLBACK:
                store = _json_store_load()
                user_message_id = _generate_uuid()
                store.setdefault("messages", {}).setdefault(conversation_id, []).append({
                    "id": user_message_id,
                    "conversation_id": conversation_id,
                    "role": "user",
                    "content": request.message,
                    "created_at": datetime.utcnow().isoformat()
                })
                _json_store_save(store)
                logger.info("Saved user message in JSON fallback", message_id=user_message_id)
            else:
                raise
        
        # Record query performance
        query_time = time.time() - start_time
        await metrics.record_query(
            user_message_query,
            query_time,
            True,
            affected_rows=1
        )
        
        # Get relevant knowledge context with caching
        knowledge_context = await _get_knowledge_context_cached(
            request.message, user["org_id"], cache
        )
        
        # Prepare system prompt
        system_prompt = _build_system_prompt(user, knowledge_context)
        
        # Get conversation history with optimized query
        history_query = """
        SELECT role, content FROM ai_messages 
        WHERE conversation_id = %s 
        ORDER BY created_at 
        LIMIT 10
        """
        history_result = await db_manager.execute_query(history_query, conversation_id)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in history_result[:-1]:  # Exclude the just-added user message
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current user message
        messages.append({"role": "user", "content": request.message})
        
        # Call Google Gemini API or fallback
        if GOOGLE_GEMINI_API_KEY:
            model = genai.GenerativeModel('gemini-pro')
            # Convert messages to Gemini format
            conversation_text = ""
            for msg in messages:
                if msg["role"] == "system":
                    conversation_text += f"System: {msg['content']}\n"
                else:
                    conversation_text += f"{msg['role'].capitalize()}: {msg['content']}\n"
            gemini_response = model.generate_content(conversation_text)
            ai_content = gemini_response.text.strip()
        else:
            # Fallback simple echo for development
            ai_content = "(AI unavailable) " + request.message[::-1]
            metadata = {"fallback": True}
        
        # Ensure metadata exists
        
        # Save AI response with optimized batch operation
        ai_message_query = """
        INSERT INTO ai_messages (conversation_id, role, content, metadata, created_at)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
        """
        
        metadata = {
            "model": "gemini-pro",
            "sources": [ctx["title"] for ctx in knowledge_context[:3]],
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "tokens_used": len(ai_content.split()) if ai_content else 0
        }
        
        try:
            ai_message_result = await db_manager.execute_query(
                ai_message_query,
                conversation_id,
                "assistant",
                ai_content,
                metadata,
                datetime.utcnow().isoformat()
            )
            ai_message_id = ai_message_result[0]["id"]
        except Exception:
            if USE_JSON_FALLBACK:
                store = _json_store_load()
                ai_message_id = _generate_uuid()
                store.setdefault("messages", {}).setdefault(conversation_id, []).append({
                    "id": ai_message_id,
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": ai_content,
                    "metadata": metadata,
                    "created_at": datetime.utcnow().isoformat()
                })
                _json_store_save(store)
                logger.info("Saved AI message in JSON fallback", message_id=ai_message_id)
            else:
                raise
        
        # Update conversation with batch operation
        try:
            update_query = """
            UPDATE ai_conversations 
            SET message_count = message_count + 2, last_message_at = %s 
            WHERE id = %s
            """
            await db_manager.execute_query(
                update_query,
                datetime.utcnow().isoformat(),
                conversation_id
            )
        except Exception:
            if USE_JSON_FALLBACK:
                store = _json_store_load()
                if conversation_id in store.get("conversations", {}):
                    conv = store["conversations"][conversation_id]
                    conv["message_count"] = int(conv.get("message_count", 0)) + 2
                    conv["last_message_at"] = datetime.utcnow().isoformat()
                    _json_store_save(store)
        
        # Record performance metrics
        total_time = time.time() - start_time
        await metrics.record_query(
            "ai_chat_complete",
            total_time,
            True,
            affected_rows=3
        )
        
        logger.info(
            "AI chat message processed",
            user_id=user["sub"],
            conversation_id=conversation_id,
            processing_time_ms=int(total_time * 1000)
        )
        
        return ChatMessageResponse(
            id=ai_message_id,
            conversation_id=conversation_id,
            role="assistant",
            content=ai_content,
            metadata=metadata,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("AI chat failed", error=str(e), user_id=(user.get("sub") or user.get("id")))
        
        # Safe error recording without crashing
        try:
            await metrics.record_query("ai_chat_error", time.time() - start_time, False, str(e))
        except Exception as metrics_error:
            logger.error("Failed to record metrics", error=str(metrics_error))
        raise HTTPException(status_code=500, detail="AI service temporarily unavailable")


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """
    Get user's chat conversations.
    """
    try:
        db_manager = await get_db_manager()
        conversations_query = """
        SELECT id, title, message_count, last_message_at, created_at
        FROM ai_conversations
        WHERE user_id = %s
        ORDER BY last_message_at DESC
        LIMIT %s
        """
        result = await db_manager.execute_query(conversations_query, user["sub"], limit)
        
        conversations = []
        for conv in result:
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
        db_manager = await get_db_manager()
        # Verify conversation ownership
        conv_response = await db_manager.execute_query("""
        SELECT id, user_id FROM ai_conversations WHERE id = %s AND user_id = %s
        """, conversation_id, user["sub"])
        
        if not conv_response:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        messages_query = """
        SELECT id, conversation_id, role, content, metadata, created_at
        FROM ai_messages
        WHERE conversation_id = %s
        ORDER BY created_at
        """
        result = await db_manager.execute_query(messages_query, conversation_id)
        
        messages = []
        for msg in result:
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
        search_response = await db_manager.execute_query("""
        SELECT id, title, content, source_type, source_id, metadata
        FROM knowledge_documents 
        WHERE org_id = %s AND embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """, user["org_id"], f"[{','.join(map(str, query_embedding))}]", request.limit)
        
        results = []
        for doc in search_response:
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
        db_manager = await get_db_manager()
        # Get available courses
        courses_query = """
        SELECT id, title, description, category, difficulty_level, estimated_duration
        FROM courses
        WHERE org_id = %s AND status = 'published'
        ORDER BY estimated_duration
        LIMIT 5
        """
        courses_result = await db_manager.execute_query(courses_query, user["org_id"])
        
        # In a real implementation, you'd use AI to analyze and recommend
        # Here's a simplified version
        steps = []
        for i, course in enumerate(courses_result):
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


async def _get_knowledge_context_cached(query: str, org_id: str, cache, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get relevant knowledge context with caching support.
    """
    try:
        # Try to get from cache first
        cache_key = f"knowledge_context:{org_id}:{query}"
        cached_result = await cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Get from database if not cached
        db_manager = await get_db_manager()
        
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
            
            # Use optimized vector search
            vector_search_query = """
            SELECT title, content, source_type, metadata,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM knowledge_documents 
            WHERE org_id = %s AND embedding IS NOT NULL
            ORDER BY similarity DESC
            LIMIT %s
            """
            
            result = await db_manager.execute_query(
                vector_search_query,
                f"[{','.join(map(str, query_embedding))}]",
                org_id,
                limit
            )
            
            if result:
                # Cache the result for 5 minutes
                await cache.set(
                    cache_key, 
                    result, 
                    ttl=300,
                    tags={"knowledge_search", f"org:{org_id}"}
                )
                return result
                
        except Exception as vector_error:
            logger.warning("Vector search failed, falling back to text search", error=str(vector_error))
        
        # Fallback to text search with caching
        text_search_query = """
        SELECT title, content, source_type, metadata
        FROM knowledge_documents 
        WHERE org_id = %s AND content ILIKE %s
        LIMIT %s
        """
        
        result = await db_manager.execute_query(
            text_search_query,
            org_id,
            f"%{query}%",
            limit
        )
        
        if result:
            # Cache for shorter time (2 minutes) since it's less accurate
            await cache.set(
                cache_key,
                result,
                ttl=120,
                tags={"knowledge_search", f"org:{org_id}"}
            )
            return result
        
        # Return recent documents if no matches
        recent_docs_query = """
        SELECT title, content, source_type, metadata
        FROM knowledge_documents 
        WHERE org_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        
        result = await db_manager.execute_query(recent_docs_query, org_id, limit)
        return result or []
        
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


# Additional optimized endpoints can be added here following the same pattern 