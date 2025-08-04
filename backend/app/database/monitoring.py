"""
Database performance monitoring and metrics collection.
Tracks query performance, connection health, and provides alerting.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import structlog
from collections import defaultdict, deque

logger = structlog.get_logger()


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class QueryMetric:
    """Individual query performance metric."""
    query_hash: str
    query_preview: str
    execution_time: float
    timestamp: float
    success: bool
    error_message: Optional[str] = None
    affected_rows: int = 0
    connection_id: Optional[str] = None


@dataclass
class DatabaseAlert:
    """Database alert."""
    level: AlertLevel
    message: str
    timestamp: float
    metric_name: str
    current_value: Any
    threshold: Any
    resolved: bool = False


@dataclass
class PerformanceThresholds:
    """Performance monitoring thresholds."""
    slow_query_threshold: float = 1.0  # seconds
    error_rate_threshold: float = 0.05  # 5%
    connection_usage_threshold: float = 0.8  # 80%
    avg_query_time_threshold: float = 0.5  # seconds
    memory_usage_threshold: int = 1000000  # bytes


class DatabaseMetrics:
    """
    Database performance monitoring and metrics collection.
    """
    
    def __init__(self, max_metrics_history: int = 10000):
        self._max_metrics_history = max_metrics_history
        self._query_metrics: deque = deque(maxlen=max_metrics_history)
        self._query_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "min_time": float('inf'),
            "max_time": 0.0,
            "error_count": 0,
            "last_executed": 0.0
        })
        
        self._connection_metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "connection_errors": 0,
            "peak_connections": 0
        }
        
        self._alerts: List[DatabaseAlert] = []
        self._alert_callbacks: List[Callable] = []
        self._thresholds = PerformanceThresholds()
        
        self._monitoring_task: Optional[asyncio.Task] = None
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Start background monitoring task."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self._check_thresholds()
                await self._cleanup_old_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Monitoring loop error", error=str(e))
    
    async def _check_thresholds(self):
        """Check performance thresholds and generate alerts."""
        current_time = time.time()
        
        # Check average query time
        if self._query_metrics:
            recent_queries = [
                m for m in self._query_metrics 
                if current_time - m.timestamp < 300  # Last 5 minutes
            ]
            
            if recent_queries:
                avg_time = sum(q.execution_time for q in recent_queries) / len(recent_queries)
                if avg_time > self._thresholds.avg_query_time_threshold:
                    await self._create_alert(
                        AlertLevel.WARNING,
                        f"Average query time is high: {avg_time:.3f}s",
                        "avg_query_time",
                        avg_time,
                        self._thresholds.avg_query_time_threshold
                    )
        
        # Check error rate
        if self._query_metrics:
            recent_queries = [
                m for m in self._query_metrics 
                if current_time - m.timestamp < 300
            ]
            
            if recent_queries:
                error_count = sum(1 for q in recent_queries if not q.success)
                error_rate = error_count / len(recent_queries)
                
                if error_rate > self._thresholds.error_rate_threshold:
                    await self._create_alert(
                        AlertLevel.ERROR,
                        f"High error rate: {error_rate:.2%}",
                        "error_rate",
                        error_rate,
                        self._thresholds.error_rate_threshold
                    )
        
        # Check connection usage
        if self._connection_metrics["total_connections"] > 0:
            usage_rate = (self._connection_metrics["active_connections"] / 
                         self._connection_metrics["total_connections"])
            
            if usage_rate > self._thresholds.connection_usage_threshold:
                await self._create_alert(
                    AlertLevel.WARNING,
                    f"High connection usage: {usage_rate:.2%}",
                    "connection_usage",
                    usage_rate,
                    self._thresholds.connection_usage_threshold
                )
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics and alerts."""
        current_time = time.time()
        
        # Clean up old alerts (keep for 24 hours)
        self._alerts = [
            alert for alert in self._alerts
            if current_time - alert.timestamp < 86400
        ]
    
    async def _create_alert(self, level: AlertLevel, message: str, 
                           metric_name: str, current_value: Any, threshold: Any):
        """Create a new alert."""
        alert = DatabaseAlert(
            level=level,
            message=message,
            timestamp=time.time(),
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold
        )
        
        self._alerts.append(alert)
        
        # Call alert callbacks
        for callback in self._alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error("Alert callback error", error=str(e))
        
        logger.log(
            level.value,
            "Database alert",
            message=message,
            metric=metric_name,
            value=current_value,
            threshold=threshold
        )
    
    async def record_query(self, query: str, execution_time: float, 
                          success: bool, error_message: Optional[str] = None,
                          affected_rows: int = 0, connection_id: Optional[str] = None):
        """
        Record a query execution metric.
        
        Args:
            query: SQL query
            execution_time: Query execution time in seconds
            success: Whether query succeeded
            error_message: Error message if query failed
            affected_rows: Number of affected rows
            connection_id: Connection identifier
        """
        import hashlib
        
        query_hash = hashlib.md5(query.encode()).hexdigest()
        query_preview = query[:100] + "..." if len(query) > 100 else query
        
        metric = QueryMetric(
            query_hash=query_hash,
            query_preview=query_preview,
            execution_time=execution_time,
            timestamp=time.time(),
            success=success,
            error_message=error_message,
            affected_rows=affected_rows,
            connection_id=connection_id
        )
        
        self._query_metrics.append(metric)
        
        # Update query statistics
        stats = self._query_stats[query_hash]
        stats["count"] += 1
        stats["total_time"] += execution_time
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["max_time"] = max(stats["max_time"], execution_time)
        stats["last_executed"] = metric.timestamp
        
        if not success:
            stats["error_count"] += 1
        
        # Check for slow queries
        if execution_time > self._thresholds.slow_query_threshold:
            await self._create_alert(
                AlertLevel.WARNING,
                f"Slow query detected: {execution_time:.3f}s",
                "slow_query",
                execution_time,
                self._thresholds.slow_query_threshold
            )
    
    async def record_connection_event(self, event_type: str, connection_id: Optional[str] = None):
        """
        Record a connection event.
        
        Args:
            event_type: Type of event (connect, disconnect, error)
            connection_id: Connection identifier
        """
        if event_type == "connect":
            self._connection_metrics["total_connections"] += 1
            self._connection_metrics["active_connections"] += 1
            self._connection_metrics["peak_connections"] = max(
                self._connection_metrics["peak_connections"],
                self._connection_metrics["active_connections"]
            )
        elif event_type == "disconnect":
            self._connection_metrics["active_connections"] = max(
                0, self._connection_metrics["active_connections"] - 1
            )
        elif event_type == "error":
            self._connection_metrics["connection_errors"] += 1
    
    def get_query_stats(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top query statistics.
        
        Args:
            limit: Number of queries to return
            
        Returns:
            List of query statistics
        """
        sorted_queries = sorted(
            self._query_stats.items(),
            key=lambda x: x[1]["avg_time"],
            reverse=True
        )
        
        result = []
        for query_hash, stats in sorted_queries[:limit]:
            # Find a recent example of this query
            example_metric = None
            for metric in reversed(self._query_metrics):
                if metric.query_hash == query_hash:
                    example_metric = metric
                    break
            
            result.append({
                "query_hash": query_hash,
                "query_preview": example_metric.query_preview if example_metric else "N/A",
                "count": stats["count"],
                "avg_time": stats["avg_time"],
                "min_time": stats["min_time"],
                "max_time": stats["max_time"],
                "error_count": stats["error_count"],
                "error_rate": stats["error_count"] / stats["count"] if stats["count"] > 0 else 0,
                "last_executed": stats["last_executed"]
            })
        
        return result
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return self._connection_metrics.copy()
    
    def get_recent_metrics(self, minutes: int = 5) -> List[QueryMetric]:
        """
        Get recent query metrics.
        
        Args:
            minutes: Number of minutes to look back
            
        Returns:
            List of recent query metrics
        """
        cutoff_time = time.time() - (minutes * 60)
        return [
            metric for metric in self._query_metrics
            if metric.timestamp > cutoff_time
        ]
    
    def get_alerts(self, unresolved_only: bool = True) -> List[DatabaseAlert]:
        """
        Get database alerts.
        
        Args:
            unresolved_only: Only return unresolved alerts
            
        Returns:
            List of alerts
        """
        if unresolved_only:
            return [alert for alert in self._alerts if not alert.resolved]
        return self._alerts.copy()
    
    async def resolve_alert(self, alert_timestamp: float):
        """
        Mark an alert as resolved.
        
        Args:
            alert_timestamp: Timestamp of alert to resolve
        """
        for alert in self._alerts:
            if alert.timestamp == alert_timestamp:
                alert.resolved = True
                logger.info("Alert resolved", message=alert.message)
                break
    
    def add_alert_callback(self, callback: Callable):
        """
        Add an alert callback function.
        
        Args:
            callback: Async function to call when alerts are created
        """
        self._alert_callbacks.append(callback)
    
    def update_thresholds(self, **kwargs):
        """
        Update performance thresholds.
        
        Args:
            **kwargs: Threshold values to update
        """
        for key, value in kwargs.items():
            if hasattr(self._thresholds, key):
                setattr(self._thresholds, key, value)
                logger.info("Threshold updated", key=key, value=value)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        current_time = time.time()
        recent_metrics = self.get_recent_metrics(5)
        
        if recent_metrics:
            avg_query_time = sum(m.execution_time for m in recent_metrics) / len(recent_metrics)
            error_count = sum(1 for m in recent_metrics if not m.success)
            error_rate = error_count / len(recent_metrics)
        else:
            avg_query_time = 0
            error_rate = 0
        
        return {
            "total_queries": len(self._query_metrics),
            "recent_query_count": len(recent_metrics),
            "avg_query_time": avg_query_time,
            "error_rate": error_rate,
            "active_alerts": len(self.get_alerts(unresolved_only=True)),
            "connection_stats": self.get_connection_stats(),
            "top_slow_queries": self.get_query_stats(5),
            "timestamp": current_time
        }
    
    async def shutdown(self):
        """Shutdown monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Database monitoring shutdown complete")


# Global metrics instance
_db_metrics: Optional[DatabaseMetrics] = None


async def get_db_metrics() -> DatabaseMetrics:
    """Get the global database metrics instance."""
    global _db_metrics
    
    if _db_metrics is None:
        _db_metrics = DatabaseMetrics()
    
    return _db_metrics


async def init_monitoring():
    """Initialize database monitoring."""
    await get_db_metrics()


async def cleanup_monitoring():
    """Cleanup monitoring resources."""
    global _db_metrics
    if _db_metrics:
        await _db_metrics.shutdown()
        _db_metrics = None 