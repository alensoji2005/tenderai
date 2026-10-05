# api/jobs.py
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os
import asyncio
import threading
from datetime import datetime
from scraper.oman_tender_scraper import OmanTenderScraper
from scraper.pdf_parser import LocalPDFExtractor
from prisma import Prisma

logger = logging.getLogger(__name__)

# Initialize the scheduler
scheduler = BackgroundScheduler()

# Shared by the scheduled run and the manual "Sync Now" button
job_state = {"last_sync": None, "status": "idle"}
_job_lock = threading.Lock()


def parse_date(date_str):
    """Parse a scraped date. Returns None when unknown - never invent a date."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception:
        pass
    try:
        return datetime.strptime(date_str.split(' ')[0], "%d/%m/%Y")
    except Exception:
        return None


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _existing_ids():
    db = Prisma()
    await db.connect()
    try:
        awarded = await db.query_raw('SELECT tender_no FROM "AwardedTender"')
        active = await db.query_raw('SELECT tender_id FROM "Tender"')
        return {r["tender_no"] for r in awarded}, {r["tender_id"] for r in active}
    finally:
        await db.disconnect()


def _save_awarded_page(page_tenders):
    logger.info(f"Saving page with {len(page_tenders)} awarded tenders...")

    async def _save():
        db = Prisma()
        await db.connect()
        try:
            for t in page_tenders:
                existing = await db.awardedtender.find_unique(where={'tender_no': t['tender_no']})
                if existing:
                    continue
                await db.awardedtender.create(data={
                    'tender_no': t['tender_no'],
                    'tender_title': t['tender_title'],
                    'entity_name': t['entity_name'],
                    'category_grade': t['category_grade'],
                    'tender_type_vendor_type': t['tender_type_vendor_type'],
                    'awarded_date': parse_date(t.get('awarded_date')),
                    'winner_company_name': t['winner_company_name'],
                    'winning_amount': t['winning_amount']
                })
                for bid in t.get('submitted_bids', []):
                    await db.awardedtenderbid.create(data={
                        'awarded_tender_no': t['tender_no'],
                        'company_name': bid['company_name'],
                        'offer_type': bid['offer_type'],
                        'total_quoted_value': bid['total_quoted_value'],
                        'status': bid['status'],
                        'is_winner': bid['is_winner']
                    })
                # An active tender that now has an award is no longer active
                await db.tender.update_many(
                    where={'tender_id': t['tender_no']}, data={'status': 'awarded'}
                )
        except Exception as db_err:
            logger.error(f"Error saving awarded batch: {db_err}")
        finally:
            await db.disconnect()

    _run_async(_save())


async def _save_active_tenders(tenders, boq_data, full_scrape):
    """Upsert scraped active tenders; close ones that disappeared from the portal list."""
    db = Prisma()
    await db.connect()
    try:
        for t in tenders:
            fields = {
                'title': t['title'],
                'category': t.get('category'),
                'closing_date': parse_date(t.get('closing_date')),
                'opening_date': parse_date(t.get('opening_date')),
                'entity': t.get('entity'),
                'grade': t.get('grade'),
                'tender_type': t.get('tender_type'),
                'tender_fee_str': t.get('tender_fee_str'),
                'tender_bond_str': t.get('tender_bond_str'),
            }
            existing = await db.tender.find_unique(where={'tender_id': t['tender_id']})
            if existing:
                # Keep a status already moved to 'awarded' by the awarded-tender sync
                if existing.status in ('closed', 'cancelled'):
                    fields['status'] = 'active'
                await db.tender.update(where={'tender_id': t['tender_id']}, data=fields)
            else:
                await db.tender.create(data={**fields, 'tender_id': t['tender_id'], 'status': 'active'})
                for item in boq_data.get(t['tender_id'], []):
                    await db.boqitem.create(data={
                        'tender_id': t['tender_id'],
                        'item_description': item['item_description'][:255],
                        'quantity': item['quantity'],
                        'unit': item['unit']
                    })

        if full_scrape and tenders:
            seen = [t['tender_id'] for t in tenders]
            closed = await db.tender.update_many(
                where={'status': 'active', 'tender_id': {'not_in': seen}},
                data={'status': 'closed'}
            )
            logger.info(f"Marked {closed} tenders no longer listed as closed.")
        logger.info(f"Saved {len(tenders)} active tenders.")
    finally:
        await db.disconnect()


def _scrape_and_save():
    username = os.environ.get("OMAN_TENDER_USERNAME")
    password = os.environ.get("OMAN_TENDER_PASSWORD")
    if not (username and password and username != "YOUR_USERNAME_HERE"):
        logger.warning("Oman Tender Board credentials not found in environment. Skipping scraper.")
        return

    scraper = OmanTenderScraper(username, password)
    try:
        if not scraper.login():
            logger.error("Portal login failed - aborting scrape.")
            return

        skip_awarded, existing_active = _run_async(_existing_ids())
        logger.info(f"{len(skip_awarded)} awarded and {len(existing_active)} active tenders already stored.")

        active = scraper.scrape_active_tenders(max_pages=1000)

        # Download documents / BOQ only for tenders we haven't stored yet
        pdf_extractor = LocalPDFExtractor()
        boq_data = {}
        for t in active:
            if t['tender_id'] in existing_active:
                continue
            items = []
            for path in scraper.download_documents(t['tender_id'], t.get('detail_url')):
                items.extend(pdf_extractor.extract_boq(path))
            if items:
                boq_data[t['tender_id']] = items

        _run_async(_save_active_tenders(active, boq_data, full_scrape=True))

        try:
            scraper.scrape_awarded_tenders(
                max_pages=1000,
                on_page_scraped=_save_awarded_page,
                skip_tender_nos=skip_awarded
            )
        except Exception as e:
            logger.error(f"Failed to scrape awarded tenders: {e}")
    finally:
        scraper.close()


def run_scraper_job():
    """Scrape, save, retrain. Only one run at a time (scheduled or manual)."""
    if not _job_lock.acquire(blocking=False):
        logger.warning("Scraper job already running - skipping.")
        return False
    job_state["status"] = "running"
    logger.info("Starting scraper job...")
    try:
        try:
            _scrape_and_save()
        except Exception as e:
            logger.error(f"Error in scraper job: {e}")

        try:
            logger.info("Retraining ML Models with newly scraped data...")
            from ml.train_model import train_model, train_competitor_model, train_win_ratio_model
            train_model()
            train_competitor_model()
            train_win_ratio_model()
            logger.info("ML Models retrained successfully.")
        except Exception as e:
            logger.error(f"Failed to retrain ML models: {e}")

        job_state["last_sync"] = datetime.utcnow().isoformat() + "Z"
        return True
    finally:
        job_state["status"] = "idle"
        _job_lock.release()


def start_jobs():
    """Start the background scheduler."""
    scheduler.add_job(run_scraper_job, 'cron', hour=2, minute=0, id='daily_scrape')
    scheduler.start()
    logger.info("APScheduler started. Scraper will run automatically at 2:00 AM.")


def stop_jobs():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("APScheduler stopped.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.getcwd(), '.env'))
    run_scraper_job()
