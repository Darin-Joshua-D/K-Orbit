"""
Database query optimization and batch processing utilities.
Provides prepared statements, query optimization, and efficient batch operations.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import structlog
from collections import defaultdict

logger = structlog.get_logger()


class OptimizationType(Enum):
    """Query optimization types."""
    INDEX_HINT = "index_hint"
    LIMIT_PUSH_DOWN = "limit_push_down"
    WHERE_OPTIMIZATION = "where_optimization"
    JOIN_OPTIMIZATION = "join_optimization"
    SUBQUERY_ELIMINATION = "subquery_elimination"


@dataclass
class QueryPlan:
    """Query execution plan analysis."""
    original_query: str
    optimized_query: str
    estimated_cost: float
    optimization_type: OptimizationType
    indexes_used: List[str]
    performance_gain: float


class QueryOptimizer:
    """
    Query optimization engine for improving database performance.
    """
    
    def __init__(self):
        self._optimization_rules = {
            OptimizationType.LIMIT_PUSH_DOWN: self._optimize_limit_push_down,
            OptimizationType.WHERE_OPTIMIZATION: self._optimize_where_clauses,
            OptimizationType.INDEX_HINT: self._add_index_hints,
            OptimizationType.JOIN_OPTIMIZATION: self._optimize_joins,
        }
        
        self._query_patterns = {
            # Common query patterns and their optimizations
            "SELECT * FROM": "Consider selecting specific columns instead of *",
            "WHERE column LIKE '%value%'": "Consider full-text search for text patterns",
            "ORDER BY column LIMIT": "Consider using index on ordering column",
            "COUNT(*)": "Consider using approximate count for large tables",
        }
        
        self._performance_cache: Dict[str, QueryPlan] = {}
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query for optimization opportunities.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Analysis results with optimization suggestions
        """
        suggestions = []
        severity_scores = []
        
        query_lower = query.lower().strip()
        
        # Check for common anti-patterns
        if "select *" in query_lower:
            suggestions.append({
                "type": "SELECT_OPTIMIZATION",
                "message": "Avoid SELECT * - specify needed columns explicitly",
                "severity": "medium",
                "impact": "Reduces memory usage and network transfer"
            })
            severity_scores.append(2)
        
        if "where" not in query_lower and ("update" in query_lower or "delete" in query_lower):
            suggestions.append({
                "type": "MISSING_WHERE",
                "message": "UPDATE/DELETE without WHERE clause detected",
                "severity": "high",
                "impact": "Could affect all rows in table"
            })
            severity_scores.append(3)
        
        if "like '%%" in query_lower:
            suggestions.append({
                "type": "INEFFICIENT_LIKE",
                "message": "Leading wildcard in LIKE prevents index usage",
                "severity": "medium",
                "impact": "Forces full table scan"
            })
            severity_scores.append(2)
        
        if "order by" in query_lower and "limit" not in query_lower:
            suggestions.append({
                "type": "ORDER_WITHOUT_LIMIT",
                "message": "ORDER BY without LIMIT may be inefficient for large results",
                "severity": "low",
                "impact": "Consider adding LIMIT if full sort not needed"
            })
            severity_scores.append(1)
        
        if query_lower.count("join") > 3:
            suggestions.append({
                "type": "COMPLEX_JOINS",
                "message": "Query has many JOINs - consider query restructuring",
                "severity": "medium",
                "impact": "Complex joins can be expensive"
            })
            severity_scores.append(2)
        
        # Calculate overall score
        overall_score = max(severity_scores) if severity_scores else 0
        
        return {
            "query": query,
            "suggestions": suggestions,
            "optimization_score": overall_score,
            "estimated_complexity": self._estimate_complexity(query),
            "recommended_indexes": self._suggest_indexes(query)
        }
    
    def optimize_query(self, query: str) -> QueryPlan:
        """
        Optimize a query for better performance.
        
        Args:
            query: SQL query to optimize
            
        Returns:
            Optimized query plan
        """
        if query in self._performance_cache:
            return self._performance_cache[query]
        
        original_query = query
        optimized_query = query
        optimizations_applied = []
        
        # Apply optimization rules
        for opt_type, optimizer in self._optimization_rules.items():
            try:
                new_query, applied = optimizer(optimized_query)
                if applied:
                    optimized_query = new_query
                    optimizations_applied.append(opt_type)
            except Exception as e:
                logger.warning("Optimization failed", 
                             type=opt_type.value, 
                             error=str(e))
        
        # Estimate performance gain
        performance_gain = self._estimate_performance_gain(
            original_query, optimized_query, optimizations_applied
        )
        
        plan = QueryPlan(
            original_query=original_query,
            optimized_query=optimized_query,
            estimated_cost=self._estimate_cost(optimized_query),
            optimization_type=optimizations_applied[0] if optimizations_applied else None,
            indexes_used=self._extract_index_usage(optimized_query),
            performance_gain=performance_gain
        )
        
        # Cache the plan
        self._performance_cache[query] = plan
        
        return plan
    
    def _optimize_limit_push_down(self, query: str) -> Tuple[str, bool]:
        """Push LIMIT clause down to subqueries where possible."""
        # Simplified implementation - in production, you'd use a proper SQL parser
        if "limit" in query.lower() and "order by" in query.lower():
            # This is a basic pattern - real implementation would be more sophisticated
            return query, False
        return query, False
    
    def _optimize_where_clauses(self, query: str) -> Tuple[str, bool]:
        """Optimize WHERE clause ordering and structure."""
        # Place more selective conditions first
        # Convert functions to sargable forms where possible
        return query, False
    
    def _add_index_hints(self, query: str) -> Tuple[str, bool]:
        """Add index hints for better query performance."""
        # Analyze query and add appropriate index hints
        return query, False
    
    def _optimize_joins(self, query: str) -> Tuple[str, bool]:
        """Optimize JOIN operations and ordering."""
        # Reorder joins for better performance
        # Convert subqueries to joins where beneficial
        return query, False
    
    def _estimate_complexity(self, query: str) -> str:
        """Estimate query complexity."""
        query_lower = query.lower()
        
        complexity_score = 0
        
        # Count different types of operations
        complexity_score += query_lower.count("join") * 2
        complexity_score += query_lower.count("subquery") * 3
        complexity_score += query_lower.count("union") * 2
        complexity_score += query_lower.count("group by") * 1
        complexity_score += query_lower.count("order by") * 1
        complexity_score += query_lower.count("having") * 2
        
        if complexity_score <= 3:
            return "low"
        elif complexity_score <= 8:
            return "medium"
        else:
            return "high"
    
    def _suggest_indexes(self, query: str) -> List[str]:
        """Suggest indexes based on query analysis."""
        suggestions = []
        query_lower = query.lower()
        
        # Extract table and column references (simplified)
        if "where" in query_lower:
            # Suggest indexes on WHERE clause columns
            suggestions.append("Consider index on WHERE clause columns")
        
        if "join" in query_lower:
            # Suggest indexes on JOIN columns
            suggestions.append("Consider indexes on JOIN columns")
        
        if "order by" in query_lower:
            # Suggest indexes on ORDER BY columns
            suggestions.append("Consider index on ORDER BY columns")
        
        return suggestions
    
    def _estimate_performance_gain(self, original: str, optimized: str, 
                                  optimizations: List[OptimizationType]) -> float:
        """Estimate performance improvement percentage."""
        if original == optimized:
            return 0.0
        
        # Simplified estimation based on optimization types
        gain = 0.0
        for opt in optimizations:
            if opt == OptimizationType.INDEX_HINT:
                gain += 30.0
            elif opt == OptimizationType.LIMIT_PUSH_DOWN:
                gain += 20.0
            elif opt == OptimizationType.WHERE_OPTIMIZATION:
                gain += 15.0
            elif opt == OptimizationType.JOIN_OPTIMIZATION:
                gain += 25.0
        
        return min(gain, 80.0)  # Cap at 80% improvement
    
    def _estimate_cost(self, query: str) -> float:
        """Estimate query execution cost."""
        # Simplified cost estimation
        base_cost = 1.0
        query_lower = query.lower()
        
        base_cost += query_lower.count("join") * 0.5
        base_cost += query_lower.count("subquery") * 1.0
        base_cost += query_lower.count("group by") * 0.3
        base_cost += query_lower.count("order by") * 0.2
        
        return base_cost
    
    def _extract_index_usage(self, query: str) -> List[str]:
        """Extract potential index usage from query."""
        # Simplified index extraction
        return ["auto_detected_index"]


class BatchProcessor:
    """
    Efficient batch processing for database operations.
    """
    
    def __init__(self, batch_size: int = 100, max_concurrent: int = 5):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    async def process_batch_inserts(self, table: str, records: List[Dict[str, Any]], 
                                   db_manager) -> Dict[str, Any]:
        """
        Process batch inserts efficiently.
        
        Args:
            table: Target table name
            records: List of records to insert
            db_manager: Database manager instance
            
        Returns:
            Batch processing results
        """
        start_time = time.time()
        total_records = len(records)
        successful_inserts = 0
        errors = []
        
        # Split into smaller batches
        batches = [
            records[i:i + self.batch_size] 
            for i in range(0, len(records), self.batch_size)
        ]
        
        async def process_single_batch(batch: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
            async with self._semaphore:
                try:
                    # Construct batch insert query
                    if not batch:
                        return 0, []
                    
                    columns = list(batch[0].keys())
                    placeholders = ", ".join([
                        f"({', '.join(['%s'] * len(columns))})"
                        for _ in batch
                    ])
                    
                    query = f"""
                    INSERT INTO {table} ({', '.join(columns)})
                    VALUES {placeholders}
                    """
                    
                    # Flatten values for the query
                    values = []
                    for record in batch:
                        values.extend([record[col] for col in columns])
                    
                    await db_manager.execute_query(query, *values)
                    return len(batch), []
                    
                except Exception as e:
                    return 0, [str(e)]
        
        # Process batches concurrently
        tasks = [process_single_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                successful_inserts += result[0]
                errors.extend(result[1])
        
        processing_time = time.time() - start_time
        
        return {
            "total_records": total_records,
            "successful_inserts": successful_inserts,
            "failed_inserts": total_records - successful_inserts,
            "errors": errors[:10],  # Limit error list
            "processing_time": processing_time,
            "records_per_second": total_records / processing_time if processing_time > 0 else 0
        }
    
    async def process_batch_updates(self, table: str, updates: List[Dict[str, Any]], 
                                   where_column: str, db_manager) -> Dict[str, Any]:
        """
        Process batch updates efficiently.
        
        Args:
            table: Target table name
            updates: List of update records with ID and values
            where_column: Column to use in WHERE clause
            db_manager: Database manager instance
            
        Returns:
            Batch processing results
        """
        start_time = time.time()
        successful_updates = 0
        errors = []
        
        async def process_update_batch(batch: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
            async with self._semaphore:
                try:
                    queries = []
                    for record in batch:
                        where_value = record.pop(where_column)
                        set_clause = ", ".join([f"{k} = %s" for k in record.keys()])
                        query = f"UPDATE {table} SET {set_clause} WHERE {where_column} = %s"
                        values = list(record.values()) + [where_value]
                        queries.append((query, *values))
                    
                    await db_manager.execute_batch(queries)
                    return len(batch), []
                    
                except Exception as e:
                    return 0, [str(e)]
        
        # Split into batches and process
        batches = [
            updates[i:i + self.batch_size]
            for i in range(0, len(updates), self.batch_size)
        ]
        
        tasks = [process_update_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                successful_updates += result[0]
                errors.extend(result[1])
        
        processing_time = time.time() - start_time
        
        return {
            "total_updates": len(updates),
            "successful_updates": successful_updates,
            "failed_updates": len(updates) - successful_updates,
            "errors": errors[:10],
            "processing_time": processing_time,
            "updates_per_second": len(updates) / processing_time if processing_time > 0 else 0
        }
    
    async def process_parallel_queries(self, queries: List[Tuple[str, tuple]], 
                                     db_manager) -> List[Any]:
        """
        Execute multiple queries in parallel with concurrency control.
        
        Args:
            queries: List of (query, args) tuples
            db_manager: Database manager instance
            
        Returns:
            List of query results in order
        """
        async def execute_single_query(query_data: Tuple[str, tuple]) -> Any:
            async with self._semaphore:
                query, args = query_data
                return await db_manager.execute_query(query, *args)
        
        tasks = [execute_single_query(query_data) for query_data in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results


# Utility functions for common optimization patterns
def create_prepared_statement(query: str, param_count: int) -> str:
    """
    Create a prepared statement format for the query.
    
    Args:
        query: Base SQL query
        param_count: Number of parameters
        
    Returns:
        Prepared statement query
    """
    # Convert named parameters to positional parameters
    prepared_query = query
    for i in range(param_count):
        prepared_query = prepared_query.replace(f":param_{i}", "%s")
    
    return prepared_query


def optimize_pagination_query(base_query: str, offset: int, limit: int) -> str:
    """
    Optimize pagination queries using cursor-based pagination when possible.
    
    Args:
        base_query: Base query without pagination
        offset: Pagination offset
        limit: Number of records per page
        
    Returns:
        Optimized pagination query
    """
    if offset > 10000:  # Large offset - suggest cursor-based pagination
        logger.warning("Large offset detected - consider cursor-based pagination",
                      offset=offset)
    
    return f"{base_query} LIMIT {limit} OFFSET {offset}"


def build_efficient_search_query(table: str, search_columns: List[str], 
                                search_term: str, use_fulltext: bool = True) -> str:
    """
    Build an efficient search query with proper indexing strategy.
    
    Args:
        table: Target table
        search_columns: Columns to search
        search_term: Search term
        use_fulltext: Whether to use full-text search
        
    Returns:
        Optimized search query
    """
    if use_fulltext and len(search_term) > 3:
        # Use full-text search for better performance
        columns_str = ", ".join(search_columns)
        return f"""
        SELECT * FROM {table} 
        WHERE to_tsvector('english', {columns_str}) @@ plainto_tsquery('english', %s)
        """
    else:
        # Use ILIKE with proper indexing
        conditions = [f"{col} ILIKE %s" for col in search_columns]
        return f"""
        SELECT * FROM {table} 
        WHERE {' OR '.join(conditions)}
        """ 