import asyncio
from prisma import Prisma

async def main():
    db = Prisma()
    await db.connect()
    users = await db.user.find_many()
    for u in users:
        print(f"User: {u.email}, Role: {u.role}")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
