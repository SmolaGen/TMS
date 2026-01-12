
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import settings

async def debug_db():
    print(f"Connecting to: {settings.DATABASE_URL}")
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        print("Connected!")
        # Check types
        result = await conn.execute(text("SELECT typname FROM pg_type WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')"))
        types = [r[0] for r in result]
        print(f"Types in public: {types}")
        
        # Check tables
        result = await conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))
        tables = [r[0] for r in result]
        print(f"Tables in public: {tables}")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(debug_db())
