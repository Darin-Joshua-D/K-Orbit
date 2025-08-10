"""
Centralized database connection management with connection pooling.
Optimizes Supabase client usage and provides connection monitoring.
"""

import os
import asyncio
import time
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import structlog
from supabase import create_client, Client
from supabase.client import ClientOptions
import asyncpg
from asyncpg import Pool
import ssl

logger = structlog.get_logger()


class DatabaseManager:
    """
    Centralized database manager with connection pooling and optimization.
    """
    
    def __init__(self):
        self._supabase_client: Optional[Client] = None
        self._supabase_admin_client: Optional[Client] = None
        self._pg_pool: Optional[Pool] = None
        self._connection_stats = {
            "total_queries": 0,
            "active_connections": 0,
            "query_times": [],
            "errors": 0
        }
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connections and pools."""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing database connections...")
            
            # Initialize Supabase clients with optimized configuration
            await self._init_supabase_clients()
            
            # Initialize PostgreSQL connection pool for direct queries
            await self._init_pg_pool()
            
            self._initialized = True
            logger.info("Database connections initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize database connections", error=str(e))
            raise
    
    async def _init_supabase_clients(self):
        """Initialize optimized Supabase clients."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not all([supabase_url, supabase_anon_key]):
            raise ValueError("Missing required Supabase environment variables")
        
        # Optimized client options for Supabase
        # Note: `persist_session` is handled automatically by the client.
        # Realtime options like timeout are passed directly to `create_client`.
        client_options = ClientOptions(
            auto_refresh_token=True,
            postgrest_client_timeout=10,  # Example: set a reasonable timeout
        )
        
        # Create optimized clients
        try:
            self._supabase_client = create_client(
                supabase_url, 
                supabase_anon_key,
                options=client_options
            )
            
            if supabase_service_key:
                self._supabase_admin_client = create_client(
                    supabase_url,
                    supabase_service_key,
                    options=client_options
                )
            logger.info("Supabase clients initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Supabase clients", error=str(e))
            raise
    
    async def _init_pg_pool(self):
        """Initialize PostgreSQL connection pool for direct queries."""
        try:
            # Extract PostgreSQL URL from Supabase URL
            supabase_url = os.getenv("SUPABASE_URL")
            if not supabase_url:
                return
                
            # Convert Supabase URL to PostgreSQL URL
            db_url = supabase_url.replace("https://", "postgresql://postgres:")
            db_password = os.getenv("SUPABASE_DB_PASSWORD", "")
            
            if db_password:
                # Create connection pool with optimized settings
                self._pg_pool = await asyncpg.create_pool(
                    f"{db_url}:{db_password}@db.{supabase_url.split('//')[1]}/postgres",
                    min_size=2,
                    max_size=10,
                    max_queries=50000,
                    max_inactive_connection_lifetime=300.0,
                    command_timeout=60.0,
                    ssl=True,
                    server_settings={
                        'application_name': 'k-orbit-backend',
                        'jit': 'off'  # Disable JIT for faster simple queries
                    }
                )
                logger.info("PostgreSQL connection pool initialized")
                
        except Exception as e:
            logger.warning("Failed to initialize PostgreSQL pool", error=str(e))
            # Continue without direct PostgreSQL access
    
    @property
    def supabase(self) -> Client:
        """Get the main Supabase client."""
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        return self._supabase_client
    
    @property 
    def supabase_admin(self) -> Optional[Client]:
        """Get the admin Supabase client."""
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        return self._supabase_admin_client
    
    @asynccontextmanager
    async def get_pg_connection(self):
        """Get a PostgreSQL connection from the pool."""
        if not self._pg_pool:
            raise RuntimeError("PostgreSQL pool not available")
            
        async with self._pg_pool.acquire() as connection:
            self._connection_stats["active_connections"] += 1
            try:
                yield connection
            finally:
                self._connection_stats["active_connections"] -= 1
    
    async def execute_query(self, query: str, *args, use_pool: bool = True) -> List[Dict[str, Any]]:
        """
        Execute a query with performance tracking.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            use_pool: Whether to use PostgreSQL pool or Supabase
        
        Returns:
            Query results
        """
        start_time = time.time()
        
        try:
            self._connection_stats["total_queries"] += 1
            
            if use_pool and self._pg_pool:
                # Use PostgreSQL pool for better performance
                async with self.get_pg_connection() as conn:
                    rows = await conn.fetch(query, *args)
                    result = [dict(row) for row in rows]
            else:
                # Fallback to Supabase
                response = await self._supabase_client.rpc('exec_sql', {
                    'sql': query,
                    'params': list(args)
                }).execute()
                result = response.data or []
            
            # Track query performance
            query_time = time.time() - start_time
            self._connection_stats["query_times"].append(query_time)
            
            # Keep only last 1000 query times for memory efficiency
            if len(self._connection_stats["query_times"]) > 1000:
                self._connection_stats["query_times"] = self._connection_stats["query_times"][-1000:]
            
            if query_time > 1.0:  # Log slow queries
                logger.warning("Slow query detected", 
                             query=query[:100],
                             duration=query_time)
            
            return result
            
        except Exception as e:
            self._connection_stats["errors"] += 1
            logger.error("Query execution failed",
                        query=query[:100],
                        error=str(e))
            raise
    
    async def execute_batch(self, queries: List[tuple]) -> List[Any]:
        """
        Execute multiple queries in a batch for better performance.
        
        Args:
            queries: List of (query, *args) tuples
            
        Returns:
            List of results for each query
        """
        if not self._pg_pool:
            # Fallback to sequential execution with Supabase
            results = []
            for query_data in queries:
                query = query_data[0]
                args = query_data[1:] if len(query_data) > 1 else []
                result = await self.execute_query(query, *args, use_pool=False)
                results.append(result)
            return results
        
        async with self.get_pg_connection() as conn:
            async with conn.transaction():
                results = []
                for query_data in queries:
                    query = query_data[0]
                    args = query_data[1:] if len(query_data) > 1 else []
                    rows = await conn.fetch(query, *args)
                    results.append([dict(row) for row in rows])
                return results
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection and performance statistics."""
        query_times = self._connection_stats["query_times"]
        
        return {
            "total_queries": self._connection_stats["total_queries"],
            "active_connections": self._connection_stats["active_connections"],
            "errors": self._connection_stats["errors"],
            "avg_query_time": sum(query_times) / len(query_times) if query_times else 0,
            "max_query_time": max(query_times) if query_times else 0,
            "min_query_time": min(query_times) if query_times else 0,
            "pool_available": self._pg_pool is not None,
            "pool_size": self._pg_pool.get_size() if self._pg_pool else 0,
            "pool_free_connections": self._pg_pool.get_idle_size() if self._pg_pool else 0
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        try:
            # Test Supabase connection
            response = await self._supabase_client.table("organizations").select("id").limit(1).execute()
            supabase_healthy = True
        except Exception as e:
            logger.error("Supabase health check failed", error=str(e))
            supabase_healthy = False
        
        # Test PostgreSQL pool if available
        pg_healthy = True
        if self._pg_pool:
            try:
                async with self.get_pg_connection() as conn:
                    await conn.fetchval("SELECT 1")
            except Exception as e:
                logger.error("PostgreSQL health check failed", error=str(e))
                pg_healthy = False
        
        return {
            "supabase_healthy": supabase_healthy,
            "postgresql_healthy": pg_healthy,
            "pool_available": self._pg_pool is not None,
            **self.get_connection_stats()
        }
    
    async def cleanup(self):
        """Clean up database connections."""
        if self._pg_pool:
            await self._pg_pool.close()
            logger.info("PostgreSQL connection pool closed")
        
        self._initialized = False
        logger.info("Database connections cleaned up")


# Global instance
_db_manager: Optional[DatabaseManager] = None


async def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    
    return _db_manager


async def init_database():
    """Initialize the global database manager."""
    await get_db_manager()


async def cleanup_database():
    """Cleanup database connections."""
    global _db_manager
    if _db_manager:
        await _db_manager.cleanup()
        _db_manager = None 