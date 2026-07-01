import asyncio
from dotenv import load_dotenv
load_dotenv()
from api.jobs import run_scraper_job

if __name__ == "__main__":
    print("Running scraper job manually...")
    run_scraper_job()
    print("Done!")
