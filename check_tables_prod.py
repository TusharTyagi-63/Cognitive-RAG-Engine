import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine(
        "postgresql+asyncpg://postgres.lneaumecnqrbywitjkya:tyagitushar@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres",
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        print("Tables:")
        for row in result:
            print(row[0])
    await engine.dispose()

asyncio.run(check())
