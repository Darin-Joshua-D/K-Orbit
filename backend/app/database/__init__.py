"""
Database optimization module for K-Orbit.
Provides centralized connection management, query optimization, and performance monitoring.
"""

from .connection import DatabaseManager, get_db_manager, init_database, cleanup_database
from .cache import QueryCache, get_query_cache, init_cache, cleanup_cache
from .monitoring import DatabaseMetrics, get_db_metrics, init_monitoring, cleanup_monitoring
from .optimization import QueryOptimizer, BatchProcessor

__all__ = [
    "DatabaseManager",
    "get_db_manager", 
    "init_database",
    "cleanup_database",
    "QueryCache",
    "get_query_cache",
    "init_cache",
    "cleanup_cache",
    "DatabaseMetrics",
    "get_db_metrics",
    "init_monitoring",
    "cleanup_monitoring",
    "QueryOptimizer",
    "BatchProcessor",
] 