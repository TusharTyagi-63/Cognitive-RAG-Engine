import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.core.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"command_timeout": 5})
    async with engine.connect() as conn:
        print("Connected. Checking pg_stat_activity...")
        from sqlalchemy import text
        result = await conn.execute(text("SELECT pid, state, wait_event_type, wait_event, query FROM pg_stat_activity WHERE state != 'idle';"))
        for row in result:
            print(dict(row._mapping))
            
        print("Checking locks...")
        result = await conn.execute(text("SELECT relation::regclass, mode, granted, pid FROM pg_locks WHERE NOT granted;"))
        for row in result:
            print(dict(row._mapping))

if __name__ == "__main__":
    asyncio.run(main())
