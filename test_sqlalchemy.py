import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sys

async def check():
    engine = create_async_engine(
        "postgresql+asyncpg://postgres.lneaumecnqrbywitjkya:tyagitushar@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres",
        echo=True,
        future=True,
        pool_size=10,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        connect_args={
            "command_timeout": 60,
            "server_settings": {"application_name": "test"},
            "statement_cache_size": 0
        }
    )
    
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("Successfully connected via SQLAlchemy!")
    except Exception as e:
        print(f"Failed to connect: {e}")
    finally:
        await engine.dispose()

asyncio.run(check())
