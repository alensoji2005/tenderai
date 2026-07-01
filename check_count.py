import asyncio
from prisma import Prisma

async def main():
    db = Prisma()
    await db.connect()
    count = await db.awardedtender.count()
    print(f"Total Awarded Tenders: {count}")
    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
