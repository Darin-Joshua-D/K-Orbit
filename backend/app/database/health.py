"""
Database health and optimization status endpoints.
Provides insights into database performance and optimization status.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
import structlog

from app.auth.middleware import get_current_user
from app.database import get_db_manager, get_query_cache, get_db_metrics

logger = structlog.get_logger()

router = APIRouter()


@router.get("/health")
async def database_health_check(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Comprehensive database health check.
    
    Returns:
        Database health status and performance metrics
    """
    try:
        db_manager = await get_db_manager()
        cache = await get_query_cache()
        metrics = await get_db_metrics()
        
        # Get health status from all components
        db_health = await db_manager.health_check()
        cache_stats = cache.get_stats()
        performance_summary = metrics.get_performance_summary()
        
        return {
            "status": "healthy" if db_health["supabase_healthy"] else "degraded",
            "database": db_health,
            "cache": cache_stats,
            "performance": performance_summary,
            "optimizations": {
                "connection_pooling": db_health["pool_available"],
                "query_caching": cache_stats["hit_rate"] > 0,
                "performance_monitoring": len(performance_summary["top_slow_queries"]) >= 0
            }
        }
        
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Database health check failed"
        )


@router.get("/stats")
async def database_stats(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get detailed database performance statistics.
    
    Returns:
        Comprehensive database performance statistics
    """
    try:
        db_manager = await get_db_manager()
        cache = await get_query_cache()
        metrics = await get_db_metrics()
        
        return {
            "connection_stats": db_manager.get_connection_stats(),
            "cache_stats": cache.get_stats(),
            "query_stats": metrics.get_query_stats(20),
            "recent_alerts": metrics.get_alerts(unresolved_only=True),
            "performance_summary": metrics.get_performance_summary()
        }
        
    except Exception as e:
        logger.error("Failed to get database stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve database statistics"
        )


@router.post("/cache/clear")
async def clear_query_cache(user: dict = Depends(get_current_user)) -> Dict[str, str]:
    """
    Clear the query cache.
    
    Returns:
        Cache clear status
    """
    try:
        # Check if user has admin privileges
        if user.get("role") not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=403,
                detail="Admin privileges required"
            )
        
        cache = await get_query_cache()
        await cache.clear()
        
        logger.info("Query cache cleared", user_id=user["sub"])
        
        return {"message": "Query cache cleared successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to clear cache", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to clear cache"
        )


@router.get("/optimization/analyze")
async def analyze_query_performance(
    query: str,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Analyze a query for optimization opportunities.
    
    Args:
        query: SQL query to analyze
        
    Returns:
        Query analysis and optimization suggestions
    """
    try:
        from app.database.optimization import QueryOptimizer
        
        optimizer = QueryOptimizer()
        analysis = optimizer.analyze_query(query)
        optimization_plan = optimizer.optimize_query(query)
        
        return {
            "analysis": analysis,
            "optimization_plan": {
                "original_query": optimization_plan.original_query,
                "optimized_query": optimization_plan.optimized_query,
                "estimated_performance_gain": optimization_plan.performance_gain,
                "optimization_type": optimization_plan.optimization_type.value if optimization_plan.optimization_type else None,
                "estimated_cost": optimization_plan.estimated_cost,
                "indexes_used": optimization_plan.indexes_used
            }
        }
        
    except Exception as e:
        logger.error("Query analysis failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Query analysis failed"
        ) 