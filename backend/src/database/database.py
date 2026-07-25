"""
Database configuration and utilities for SentinelMonitorIA
Uses SQLAlchemy async for PostgreSQL
"""

from typing import AsyncGenerator, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.pool import NullPool
from src.config.settings import settings
from src.config.logging import logger
from src.models.base import Base
from src.models import intelligence  # noqa: F401 - register AI and alert tables


class DatabaseManager:
    """Database manager for async PostgreSQL connections"""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database connection pool"""
        if self._initialized:
            return
        
        logger.info(
            "Initializing database connection",
            database_url=f"{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        
        try:
            # Create async engine
            self.engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=300,
                pool_size=20,
                max_overflow=10,
                poolclass=NullPool if settings.environment == "testing" else None,
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            
            self._initialized = True
            
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize database connection", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        if not self._initialized:
            await self.initialize()
        
        if not self.session_factory:
            raise RuntimeError("Database session factory not initialized")
        
        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error("Database session error", error=str(e))
                raise
            finally:
                await session.close()
    
    async def create_tables(self) -> None:
        """Create all database tables"""
        if not self.engine:
            await self.initialize()
        
        logger.info("Creating database tables")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    
    async def drop_tables(self) -> None:
        """Drop all database tables (for testing)"""
        if not self.engine:
            await self.initialize()
        
        logger.warning("Dropping all database tables")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("Database tables dropped")
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            if not self.engine:
                return False
            
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    async def get_stats(self) -> dict:
        """Get database statistics"""
        try:
            if not self.engine:
                return {"error": "Database not initialized"}
            
            async with self.engine.connect() as conn:
                # Get connection pool stats
                pool = self.engine.pool
                stats = {
                    "pool_size": pool.size() if pool else 0,
                    "checked_out": pool.checkedout() if pool else 0,
                    "checked_in": pool.checkedin() if pool else 0,
                    "overflow": pool.overflow() if pool else 0,
                }
                
                # Get table counts
                tables = {}
                for table_name in Base.metadata.tables.keys():
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    tables[table_name] = count
                
                stats["table_counts"] = tables
                
                return stats
        
        except Exception as e:
            logger.error("Failed to get database stats", error=str(e))
            return {"error": str(e)}


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session"""
    async for session in db_manager.get_session():
        yield session


# Context manager for database operations
class DatabaseContext:
    """Context manager for database operations"""
    
    def __init__(self):
        self.session: Optional[AsyncSession] = None
    
    async def __aenter__(self) -> AsyncSession:
        await db_manager.initialize()
        self.session = db_manager.session_factory() if db_manager.session_factory else None
        if not self.session:
            raise RuntimeError("Failed to create database session")
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()


# Utility functions
async def execute_query(query: str, params: dict = None) -> list:
    """Execute raw SQL query"""
    async with DatabaseContext() as session:
        result = await session.execute(query, params or {})
        return result.fetchall()


async def bulk_insert(model_class, data: list[dict]) -> None:
    """Perform bulk insert"""
    async with DatabaseContext() as session:
        instances = [model_class(**item) for item in data]
        session.add_all(instances)
        await session.commit()