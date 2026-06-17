import asyncio
import asyncpg
import sys

async def check():
    try:
        conn = await asyncpg.connect(
            user="postgres.lneaumecnqrbywitjkya",
            password="tyagitushar",
            database="postgres",
            host="aws-1-ap-southeast-1.pooler.supabase.com",
            port=6543,
            ssl="require",
            timeout=5.0,
            statement_cache_size=0,
            prepared_statement_cache_size=0
        )
        print("Connected!")
        await conn.close()
    except Exception as e:
        print(f"Failed to connect: {e}")

asyncio.run(check())
