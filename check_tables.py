import asyncio
from sqlalchemy import text
from backend.app.database.connection import engine

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        print("Tables:")
        for row in result:
            print(row[0])

asyncio.run(check())
