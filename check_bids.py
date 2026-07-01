import asyncio
from prisma import Prisma

async def main():
    db = Prisma()
    await db.connect()
    count = await db.awardedtenderbid.count()
    print(f"Total Bids in Database: {count}")
    
    first_bid = await db.awardedtenderbid.find_first()
    print(f"First bid: {first_bid}")
    
    awarded_count = await db.awardedtender.count()
    print(f"Total Awarded Tenders: {awarded_count}")
    
    await db.disconnect()

asyncio.run(main())
