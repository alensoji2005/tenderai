import asyncio
from prisma import Prisma

async def main():
    db = Prisma()
    await db.connect()
    
    # Delete garbage records
    deleted = await db.awardedtender.delete_many(
        where={
            'tender_no': {
                'in': ['Page', '«Previous', '«First']
            }
        }
    )
    print(f"Deleted {deleted} garbage records from AwardedTenders")
    
    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
