
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from src.database.models import Base
from src.config import settings
from sqlalchemy import text

async def sync_db():
    print(f"Syncing DB: {settings.DATABASE_URL}")
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        # Create extensions
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        
        # We might need to drop everything first if it's messed up
        # Но осторожно!
        # await conn.run_sync(Base.metadata.drop_all)
        
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created!")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(sync_db())
