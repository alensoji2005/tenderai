import asyncio
from prisma import Prisma
import bcrypt

async def main():
    db = Prisma()
    await db.connect()
    
    count = await db.user.count()
    if count == 0:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(b"admin123", salt).decode('utf-8')
        await db.user.create(data={
            "email": "admin@tenderai.com",
            "password": hashed,
            "role": "admin"
        })
        print("Admin user created: admin@tenderai.com / admin123")
    else:
        print("Users already exist.")
        
    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
