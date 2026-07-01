# api/jobs.py
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os
import asyncio
from datetime import datetime, timedelta
from scraper.public_scraper import PublicTenderScraper
from scraper.oman_tender_scraper import OmanTenderScraper
from scraper.pdf_parser import LocalPDFExtractor
from prisma import Prisma

logger = logging.getLogger(__name__)

# Initialize the scheduler
scheduler = BackgroundScheduler()

def parse_date(date_str):
    try:
        # Try standard ISO format
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception:
        pass
        
    try:
        # Try a common date format (dd/mm/yyyy)
        return datetime.strptime(date_str.split(' ')[0], "%d/%m/%Y")
    except Exception:
        pass
        
    # Default fallback: 30 days from now
    return datetime.utcnow() + timedelta(days=30)

def run_scraper_job():
    """
    This function wraps the scraper execution in a synchronous task
    so it can be scheduled. It then updates the database.
    """
    logger.info("Starting scheduled scraper job...")
    
    try:
        # --- 1. Run Public Scraper (MEDC) ---
        # TODO: Rewrite MEDC scraper later
        # public_scraper = PublicTenderScraper()
        # medc_tenders = public_scraper.scrape_medc_tenders()
        medc_tenders = []
        
        # --- 2. Run Private Scraper (Oman Tender Board) ---
        oman_tenders = []
        awarded_tenders = []
        boq_data = {} # Map tender_id to list of BOQ items
        
        username = os.environ.get("OMAN_TENDER_USERNAME")
        password = os.environ.get("OMAN_TENDER_PASSWORD")
        
        try:
            if username and password and username != "YOUR_USERNAME_HERE":
                oman_scraper = OmanTenderScraper(username, password)
                try:
                    oman_scraper.login()
                    # Scrape all available pages (setting a high limit)
                    oman_tenders = oman_scraper.scrape_active_tenders(max_pages=1000)
                    
                    def save_awarded_page(page_tenders):
                        logger.info(f"Saving page with {len(page_tenders)} awarded tenders...")
                        async def _save():
                            db = Prisma()
                            await db.connect()
                            try:
                                for t in page_tenders:
                                    existing = await db.awardedtender.find_unique(where={'tender_no': t['tender_no']})
                                    awarded_date_parsed = parse_date(t.get('awarded_date', ''))
                                    
                                    if not existing:
                                        await db.awardedtender.create(data={
                                            'tender_no': t['tender_no'],
                                            'tender_title': t['tender_title'],
                                            'entity_name': t['entity_name'],
                                            'category_grade': t['category_grade'],
                                            'tender_type_vendor_type': t['tender_type_vendor_type'],
                                            'awarded_date': awarded_date_parsed,
                                            'winner_company_name': t['winner_company_name'],
                                            'winning_amount': t['winning_amount']
                                        })
                                        
                                        if 'submitted_bids' in t:
                                            for bid in t.get('submitted_bids', []):
                                                await db.awardedtenderbid.create(data={
                                                    'awarded_tender_no': t['tender_no'],
                                                    'company_name': bid['company_name'],
                                                    'offer_type': bid['offer_type'],
                                                    'total_quoted_value': bid['total_quoted_value'],
                                                    'status': bid['status'],
                                                    'is_winner': bid['is_winner']
                                                })
                            except Exception as db_err:
                                logger.error(f"Error saving awarded batch: {db_err}")
                            finally:
                                await db.disconnect()
                        
                        loop = asyncio.new_event_loop()
                        loop.run_until_complete(_save())
                        loop.close()

                    try:
                        # Fetch all existing awarded tender numbers to skip them
                        db = Prisma()
                        loop = asyncio.new_event_loop()
                        async def get_existing_tenders():
                            await db.connect()
                            # Prisma-Python may not support 'select' in find_many the same way
                            existing = await db.awardedtender.find_many()
                            await db.disconnect()
                            return {t.tender_no for t in existing if t.tender_no}
                        skip_tender_nos = loop.run_until_complete(get_existing_tenders())
                        loop.close()
                        
                        logger.info(f"Found {len(skip_tender_nos)} existing awarded tenders to skip.")
                        awarded_tenders = oman_scraper.scrape_awarded_tenders(
                            max_pages=1000, 
                            on_page_scraped=save_awarded_page,
                            skip_tender_nos=skip_tender_nos
                        )
                    except Exception as e:
                        logger.error(f"Failed to scrape awarded tenders: {str(e)}")
                    
                    pdf_extractor = LocalPDFExtractor()
                    
                    for t in oman_tenders:
                        # Scrape active tenders returns minimal info, set defaults
                        if 'tender_id' in t:
                            if 'closing_date' not in t:
                                t['closing_date'] = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
                            
                            # Download documents
                            downloaded_files = oman_scraper.download_documents(t['tender_id'])
                            
                            # Extract BOQ from downloaded PDFs
                            t_boq_items = []
                            for file_path in downloaded_files:
                                extracted_items = pdf_extractor.extract_boq(file_path)
                                t_boq_items.extend(extracted_items)
                            
                            if t_boq_items:
                                boq_data[t['tender_id']] = t_boq_items
                finally:
                    oman_scraper.close()
            else:
                logger.warning("Oman Tender Board credentials not found in environment. Skipping private scraper.")
        except Exception as e:
            logger.error(f"Failed to run Oman Tender Scraper: {str(e)}")
        
        # Combine all scraped tenders
        all_tenders = medc_tenders + oman_tenders
        
        # --- 3. Save to Database ---
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def save_tenders():
            db = Prisma()
            await db.connect()
            try:
                for t in all_tenders:
                    # Check if tender exists
                    existing = await db.tender.find_unique(where={'tender_id': t['tender_id']})
                    
                    closing_date_parsed = parse_date(t.get('closing_date', ''))

                    if not existing:
                        tender = await db.tender.create(data={
                            'tender_id': t['tender_id'],
                            'title': t['title'],
                            'category': t.get('category'),
                            'closing_date': closing_date_parsed,
                            'status': 'active',
                            'entity': t.get('entity'),
                            'grade': t.get('grade'),
                            'tender_type': t.get('tender_type'),
                            'tender_fee_str': t.get('tender_fee_str'),
                            'tender_bond_str': t.get('tender_bond_str'),
                            'opening_date': parse_date(t.get('opening_date')) if t.get('opening_date') else None,
                        })
                        
                        # Add BOQ items if we extracted any
                        items = boq_data.get(t['tender_id'], [])
                        for item in items:
                            await db.bOQItem.create(data={
                                'tender_id': t['tender_id'],
                                'item_description': item['item_description'][:255], # Ensure it fits length constraints if any
                                'quantity': item['quantity'],
                                'unit': item['unit']
                            })
                            
                logger.info(f"Successfully saved {len(all_tenders)} tenders to database.")
                
                # Awarded tenders are now saved incrementally per page via the callback
                if awarded_tenders:
                    logger.info(f"Finished scraping {len(awarded_tenders)} awarded tenders.")
                    
            except Exception as e:
                logger.error(f"Database error during scraping: {str(e)}")
            finally:
                await db.disconnect()
                
        loop.run_until_complete(save_tenders())
        loop.close()
        
    except Exception as e:
        logger.error(f"Error in scraper job: {str(e)}")

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
    import os
    load_dotenv(os.path.join(os.getcwd(), '.env'))
    # Set to a higher max_pages if needed
    run_scraper_job()
