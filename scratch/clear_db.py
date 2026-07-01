import asyncio
from prisma import Prisma

async def clear_db():
    db = Prisma()
    await db.connect()
    
    deleted_b = await db.boqitem.delete_many()
    print(f"Deleted {deleted_b} BOQItems")
    
    deleted_t = await db.tender.delete_many()
    print(f"Deleted {deleted_t} Tenders")
    
    deleted_a = await db.awardedtender.delete_many()
    print(f"Deleted {deleted_a} AwardedTenders")
    
    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(clear_db())
