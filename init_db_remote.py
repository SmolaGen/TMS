
import asyncio
from src.database.connection import init_db, engine
from src.database.models import Base

async def run():
    print("Initializing database...")
    try:
        await init_db()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error during initialization: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run())
