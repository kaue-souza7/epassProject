#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python -c "
import asyncio, asyncpg, os, sys, time

url = os.environ['DATABASE_URL_SYNC']

async def check():
    for i in range(30):
        try:
            conn = await asyncpg.connect(url, timeout=3)
            await conn.close()
            print('PostgreSQL is ready.')
            return True
        except Exception as e:
            print(f'Waiting for PostgreSQL... ({e})')
            await asyncio.sleep(1)
    print('ERROR: PostgreSQL not available after 30 attempts')
    return False

if not asyncio.run(check()):
    sys.exit(1)
"

echo "Running migrations..."
alembic upgrade head

echo "Seeding database..."
python seed_data.py

echo "Starting FastAPI..."
exec "$@"
