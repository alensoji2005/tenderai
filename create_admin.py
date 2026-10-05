import asyncio
from prisma import Prisma
import bcrypt
import os
import getpass

async def main():
    db = Prisma()
    await db.connect()
    
    count = await db.user.count()
    if count == 0:
        salt = bcrypt.gensalt()
        password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        await db.user.create(data={
            "email": "admin@tenderai.com",
            "password": hashed,
            "role": "admin"
        })
        print("Admin user created: admin@tenderai.com")
    else:
        print("Users already exist.")
        
    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
