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
            timeout=5.0
        )
        records = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [r['table_name'] for r in records]
        print(f"Tables in public schema: {tables}")
        await conn.close()
    except Exception as e:
        print(f"Failed to query DB: {e}")

asyncio.run(check())
