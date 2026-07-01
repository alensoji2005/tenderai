import asyncio
from prisma import Prisma

async def main():
    db = Prisma()
    await db.connect()
    tenders = await db.tender.find_many()
    
    with open("C:/Users/alens/.gemini/antigravity-ide/brain/19ff3e1b-78c7-4d7d-bfaa-de8e807fb92a/scraped_tenders.md", "w", encoding="utf-8") as f:
        f.write("# Scraped Tenders\\n\\n")
        f.write(f"Total Tenders: {len(tenders)}\\n\\n")
        f.write("| Tender ID | Title | Closing Date |\\n")
        f.write("| --- | --- | --- |\\n")
        for t in tenders:
            f.write(f"| {t.tender_id} | {t.title} | {t.closing_date} |\\n")
            
    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
