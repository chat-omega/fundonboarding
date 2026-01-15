"""Research data caching service for fund categorization system."""

import json
import logging
import hashlib
import pickle
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from contextlib import contextmanager
import asyncio
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Individual cache entry."""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int
    last_accessed: datetime
    tags: List[str]
    size_bytes: int
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return datetime.now() > self.expires_at
    
    def is_stale(self, max_age: timedelta) -> bool:
        """Check if entry is stale based on max age."""
        return datetime.now() > (self.created_at + max_age)


class ResearchDataCache:
    """
    Research data caching service with multiple storage backends.
    
    Features:
    - SQLite-based persistent storage
    - In-memory cache for frequently accessed data
    - TTL-based expiration
    - Tag-based cache invalidation
    - Size-based eviction
    - Access pattern tracking
    """
    
    def __init__(self, 
                 cache_dir: str = "/app/data/cache",
                 max_memory_size: int = 100 * 1024 * 1024,  # 100MB
                 max_disk_size: int = 1024 * 1024 * 1024,    # 1GB
                 default_ttl: timedelta = timedelta(hours=24)):
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.cache_dir / "research_cache.db"
        self.max_memory_size = max_memory_size
        self.max_disk_size = max_disk_size
        self.default_ttl = default_ttl
        
        # In-memory cache for frequently accessed items
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.memory_size = 0
        
        # Initialize database
        self._init_database()
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "memory_hits": 0,
            "disk_hits": 0,
            "evictions": 0,
            "cleanups": 0
        }
        
        logger.info(f"📦 Initialized ResearchDataCache at {self.cache_dir}")
    
    def _init_database(self):
        """Initialize SQLite database for persistent cache."""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    tags TEXT,  -- JSON array of tags
                    size_bytes INTEGER
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tags ON cache_entries(tags)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_entries(last_accessed)
            """)
            
        logger.info("📦 Cache database initialized")
    
    @contextmanager
    def _get_db_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        return pickle.loads(data)
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate size of value in bytes."""
        return len(self._serialize_value(value))
    
    async def get(self, 
                  key: Optional[str] = None, 
                  *args, 
                  tags: List[str] = None,
                  **kwargs) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Explicit cache key (if not provided, generated from args/kwargs)
            *args: Arguments to generate key from
            tags: Tags to filter by
            **kwargs: Keyword arguments to generate key from
        
        Returns:
            Cached value or None if not found/expired
        """
        
        if key is None:
            key = self._generate_key(*args, **kwargs)
        
        # Check memory cache first
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                self.stats["hits"] += 1
                self.stats["memory_hits"] += 1
                logger.debug(f"📦 Memory cache hit for key: {key[:16]}...")
                return entry.value
            else:
                # Remove expired entry from memory
                self._remove_from_memory(key)
        
        # Check disk cache
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT value, created_at, expires_at, access_count, tags, size_bytes
                    FROM cache_entries 
                    WHERE key = ? AND expires_at > ?
                """, (key, datetime.now()))
                
                row = cursor.fetchone()
                
                if row:
                    value = self._deserialize_value(row["value"])
                    
                    # Update access stats
                    conn.execute("""
                        UPDATE cache_entries 
                        SET access_count = access_count + 1, last_accessed = ?
                        WHERE key = ?
                    """, (datetime.now(), key))
                    
                    # Add to memory cache if it's frequently accessed
                    access_count = row["access_count"] + 1
                    if access_count >= 3:  # Add to memory after 3+ accesses
                        await self._add_to_memory(key, value, dict(row))
                    
                    self.stats["hits"] += 1
                    self.stats["disk_hits"] += 1
                    logger.debug(f"📦 Disk cache hit for key: {key[:16]}...")
                    return value
        
        except Exception as e:
            logger.warning(f"📦 Cache read error for key {key[:16]}...: {e}")
        
        self.stats["misses"] += 1
        logger.debug(f"📦 Cache miss for key: {key[:16]}...")
        return None
    
    async def set(self, 
                  value: Any,
                  key: Optional[str] = None,
                  *args,
                  ttl: Optional[timedelta] = None,
                  tags: List[str] = None,
                  **kwargs):
        """
        Set value in cache.
        
        Args:
            value: Value to cache
            key: Explicit cache key (if not provided, generated from args/kwargs)
            *args: Arguments to generate key from
            ttl: Time to live (if not provided, uses default)
            tags: Tags for cache invalidation
            **kwargs: Keyword arguments to generate key from
        """
        
        if key is None:
            key = self._generate_key(*args, **kwargs)
        
        if ttl is None:
            ttl = self.default_ttl
        
        if tags is None:
            tags = []
        
        now = datetime.now()
        expires_at = now + ttl
        size_bytes = self._calculate_size(value)
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=expires_at,
            access_count=1,
            last_accessed=now,
            tags=tags,
            size_bytes=size_bytes
        )
        
        # Store in database
        try:
            serialized_value = self._serialize_value(value)
            tags_json = json.dumps(tags)
            
            with self._get_db_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, value, created_at, expires_at, access_count, last_accessed, tags, size_bytes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (key, serialized_value, now, expires_at, 1, now, tags_json, size_bytes))
            
            logger.debug(f"📦 Stored in disk cache: {key[:16]}... ({size_bytes} bytes)")
            
        except Exception as e:
            logger.error(f"📦 Cache write error for key {key[:16]}...: {e}")
            return
        
        # Add to memory cache if small enough
        if size_bytes <= self.max_memory_size // 10:  # Max 10% of memory per item
            await self._add_to_memory(key, value, asdict(entry))
        
        # Periodic cleanup
        if len(self.memory_cache) % 100 == 0:  # Every 100 operations
            await self._cleanup_expired()
    
    async def _add_to_memory(self, key: str, value: Any, entry_data: Dict[str, Any]):
        """Add entry to memory cache with eviction if needed."""
        
        size_bytes = entry_data.get("size_bytes", self._calculate_size(value))
        
        # Check if we need to evict
        while (self.memory_size + size_bytes > self.max_memory_size and 
               len(self.memory_cache) > 0):
            await self._evict_from_memory()
        
        # Create memory entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=entry_data.get("created_at", datetime.now()),
            expires_at=entry_data.get("expires_at", datetime.now() + self.default_ttl),
            access_count=entry_data.get("access_count", 1),
            last_accessed=entry_data.get("last_accessed", datetime.now()),
            tags=entry_data.get("tags", []),
            size_bytes=size_bytes
        )
        
        self.memory_cache[key] = entry
        self.memory_size += size_bytes
        
        logger.debug(f"📦 Added to memory cache: {key[:16]}... ({size_bytes} bytes)")
    
    async def _evict_from_memory(self):
        """Evict least recently used item from memory cache."""
        
        if not self.memory_cache:
            return
        
        # Find LRU item
        lru_key = min(self.memory_cache.keys(), 
                     key=lambda k: self.memory_cache[k].last_accessed)
        
        self._remove_from_memory(lru_key)
        self.stats["evictions"] += 1
    
    def _remove_from_memory(self, key: str):
        """Remove item from memory cache."""
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            self.memory_size -= entry.size_bytes
            del self.memory_cache[key]
            logger.debug(f"📦 Removed from memory cache: {key[:16]}...")
    
    async def delete(self, key: Optional[str] = None, *args, **kwargs):
        """Delete entry from cache."""
        
        if key is None:
            key = self._generate_key(*args, **kwargs)
        
        # Remove from memory
        self._remove_from_memory(key)
        
        # Remove from disk
        try:
            with self._get_db_connection() as conn:
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            logger.debug(f"📦 Deleted from cache: {key[:16]}...")
        except Exception as e:
            logger.error(f"📦 Cache delete error for key {key[:16]}...: {e}")
    
    async def delete_by_tags(self, tags: List[str]):
        """Delete all entries with any of the specified tags."""
        
        if not tags:
            return
        
        deleted_keys = []
        
        try:
            with self._get_db_connection() as conn:
                # Find entries with matching tags
                cursor = conn.execute("""
                    SELECT key, tags FROM cache_entries
                """)
                
                for row in cursor:
                    entry_tags = json.loads(row["tags"] or "[]")
                    if any(tag in entry_tags for tag in tags):
                        deleted_keys.append(row["key"])
                
                # Delete matching entries
                if deleted_keys:
                    placeholders = ",".join(["?"] * len(deleted_keys))
                    conn.execute(f"DELETE FROM cache_entries WHERE key IN ({placeholders})", deleted_keys)
        
        except Exception as e:
            logger.error(f"📦 Cache delete by tags error: {e}")
            return
        
        # Remove from memory cache
        for key in deleted_keys:
            self._remove_from_memory(key)
        
        logger.info(f"📦 Deleted {len(deleted_keys)} entries by tags: {tags}")
    
    async def _cleanup_expired(self):
        """Remove expired entries from cache."""
        
        now = datetime.now()
        
        # Clean memory cache
        expired_keys = [key for key, entry in self.memory_cache.items() 
                       if entry.is_expired()]
        
        for key in expired_keys:
            self._remove_from_memory(key)
        
        # Clean disk cache
        try:
            with self._get_db_connection() as conn:
                result = conn.execute("DELETE FROM cache_entries WHERE expires_at <= ?", (now,))
                deleted_count = result.rowcount
                
            if deleted_count > 0 or expired_keys:
                self.stats["cleanups"] += 1
                logger.info(f"📦 Cleaned up {deleted_count} expired disk entries and {len(expired_keys)} memory entries")
        
        except Exception as e:
            logger.error(f"📦 Cache cleanup error: {e}")
    
    async def clear_all(self):
        """Clear all cache data."""
        
        # Clear memory
        self.memory_cache.clear()
        self.memory_size = 0
        
        # Clear disk
        try:
            with self._get_db_connection() as conn:
                conn.execute("DELETE FROM cache_entries")
            logger.info("📦 Cleared all cache data")
        except Exception as e:
            logger.error(f"📦 Cache clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        
        hit_rate = (self.stats["hits"] / (self.stats["hits"] + self.stats["misses"]) 
                   if (self.stats["hits"] + self.stats["misses"]) > 0 else 0.0)
        
        # Get disk cache stats
        disk_entries = 0
        disk_size = 0
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*), SUM(size_bytes) FROM cache_entries")
                row = cursor.fetchone()
                if row:
                    disk_entries = row[0] or 0
                    disk_size = row[1] or 0
        except Exception as e:
            logger.error(f"📦 Stats query error: {e}")
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "memory_hits": self.stats["memory_hits"],
            "disk_hits": self.stats["disk_hits"],
            "evictions": self.stats["evictions"],
            "cleanups": self.stats["cleanups"],
            "memory_entries": len(self.memory_cache),
            "memory_size_mb": self.memory_size / (1024 * 1024),
            "memory_utilization": self.memory_size / self.max_memory_size,
            "disk_entries": disk_entries,
            "disk_size_mb": disk_size / (1024 * 1024),
            "disk_utilization": disk_size / self.max_disk_size if self.max_disk_size > 0 else 0.0
        }
    
    async def fund_research_key(self, ticker: str, research_type: str = "comprehensive") -> str:
        """Generate cache key for fund research data."""
        return self._generate_key("fund_research", ticker.upper(), research_type)
    
    async def classification_key(self, ticker: str, research_hash: Optional[str] = None) -> str:
        """Generate cache key for fund classification data."""
        return self._generate_key("fund_classification", ticker.upper(), research_hash or "")
    
    async def web_search_key(self, query: str, search_type: str = "general") -> str:
        """Generate cache key for web search results."""
        return self._generate_key("web_search", query, search_type)


# Global cache instance
research_cache = ResearchDataCache()


class CacheableResearchMixin:
    """Mixin class to add caching capabilities to research agents."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = research_cache
    
    async def cached_fund_research(self, ticker: str, research_function, *args, **kwargs):
        """Execute fund research with caching."""
        
        cache_key = await self.cache.fund_research_key(ticker)
        
        # Try to get from cache
        cached_result = await self.cache.get(cache_key, tags=[f"fund:{ticker}", "research"])
        if cached_result:
            logger.info(f"📦 Using cached research for {ticker}")
            return cached_result
        
        # Execute research function
        logger.info(f"🔍 Executing fresh research for {ticker}")
        result = await research_function(*args, **kwargs)
        
        # Cache the result
        await self.cache.set(
            result,
            key=cache_key,
            ttl=timedelta(hours=24),
            tags=[f"fund:{ticker}", "research"]
        )
        
        return result
    
    async def cached_classification(self, ticker: str, classification_function, research_data, *args, **kwargs):
        """Execute fund classification with caching."""
        
        # Generate hash of research data for cache key
        research_hash = hashlib.md5(str(research_data).encode()).hexdigest()[:8]
        cache_key = await self.cache.classification_key(ticker, research_hash)
        
        # Try to get from cache
        cached_result = await self.cache.get(cache_key, tags=[f"fund:{ticker}", "classification"])
        if cached_result:
            logger.info(f"📦 Using cached classification for {ticker}")
            return cached_result
        
        # Execute classification function
        logger.info(f"🏷️ Executing fresh classification for {ticker}")
        result = await classification_function(research_data, *args, **kwargs)
        
        # Cache the result
        await self.cache.set(
            result,
            key=cache_key,
            ttl=timedelta(hours=12),  # Classifications may change more often
            tags=[f"fund:{ticker}", "classification"]
        )
        
        return result
    
    async def invalidate_fund_cache(self, ticker: str):
        """Invalidate all cached data for a specific fund."""
        await self.cache.delete_by_tags([f"fund:{ticker}"])
        logger.info(f"📦 Invalidated cache for fund {ticker}")
    
    async def invalidate_research_cache(self):
        """Invalidate all research cache data."""
        await self.cache.delete_by_tags(["research"])
        logger.info(f"📦 Invalidated all research cache data")


# Decorator for caching function results
def cache_result(ttl_hours: int = 24, tags: List[str] = None):
    """Decorator to cache function results."""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache_key = research_cache._generate_key(func.__name__, *args, **kwargs)
            
            # Try cache first
            cached = await research_cache.get(cache_key, tags=tags or [])
            if cached is not None:
                return cached
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await research_cache.set(
                result,
                key=cache_key,
                ttl=timedelta(hours=ttl_hours),
                tags=tags or []
            )
            
            return result
        
        return wrapper
    return decorator