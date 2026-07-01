@echo off
echo Initializing Prisma Database...
call venv\Scripts\activate
prisma generate
prisma db push
echo Database initialization complete.
pause
