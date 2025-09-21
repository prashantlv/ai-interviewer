#!/usr/bin/env python3
"""Test database connection"""

import asyncio
from services.database import DatabaseService

async def test():
    db = DatabaseService()
    await db.connect()
    status = await db.health_check()
    print(f'DB Status: {status}')
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test())
