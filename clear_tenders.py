import asyncio
from prisma import Prisma

async def main():
    db = Prisma()
    await db.connect()
    # This will delete all tenders and cascade delete related records if configured
    deleted = await db.tender.delete_many()
    print(f"Deleted {deleted} tenders")
    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
