# scraper/oman_tender_scraper.py
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import os
import requests

# Configure logging to see what the bot is doing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OmanTenderScraper:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = "https://etendering.tenderboard.gov.om/product/publicDash"
        
        logger.info("Initializing Undetected ChromeDriver...")
        options = uc.ChromeOptions()
        options.add_argument("--disable-popup-blocking")
        # Keep headless disabled for now so we can visually watch the bot navigate
        # options.add_argument('--headless') 
        
        self.driver = uc.Chrome(options=options, version_main=149)
        self.wait = WebDriverWait(self.driver, 20) # 20-second timeout for slow portals

    def login(self):
        try:
            logger.info(f"Navigating to {self.base_url}...")
            self.driver.get(self.base_url)
            
            logger.info("Waiting for login fields to appear...")
            
            # Wait for username field using the ID we found
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtUserId"))
            )
            username_field.clear()
            username_field.send_keys(self.username)
            logger.info("Entered username.")

            # Find password field using its ID
            password_field = self.driver.find_element(By.ID, "txtPassword")
            password_field.clear()
            password_field.send_keys(self.password)
            logger.info("Entered password.")

            # Submit form directly via the password field
            password_field.submit()
            logger.info("Submitted login form. Waiting for dashboard...")

            # Wait for a specific element that only appears AFTER successful login to confirm
            time.sleep(5) 
            logger.info("Login sequence completed. Please verify the browser state.")

        except Exception as e:
            logger.error(f"Scraper encountered an error: {str(e)}")

    def scrape_active_tenders(self, max_pages=10, on_page_scraped=None):
        """
        Scrape currently active tenders.
        Returns a list of dictionaries with basic tender info.
        If on_page_scraped is provided, it will be called with the tenders scraped on each page.
        """
        active_tenders = []
        logger.info("Starting active tenders scraping...")
        tenders = []
        
        try:
            # Navigate to the actual in-process tenders view
            self.driver.get("https://etendering.tenderboard.gov.om/product/publicDash?viewFlag=InProcessTenders")
            time.sleep(10) # Wait for dynamic table to load
            
            for page in range(max_pages):
                # Find the main data table
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                target_table = None
                for table in soup.find_all("table"):
                    headers = [th.text.strip().lower() for th in table.find_all("th")]
                    if len(headers) >= 8 and "display" in table.get("class", []):
                        target_table = table
                        break
                        
                if target_table:
                    rows = target_table.find_all("tr")
                    logger.info(f"Found table with {len(rows)} rows on page {page+1}.")
                    
                    page_tenders = []
                    for row in rows[1:]: # Skip header
                        cols = row.find_all("td")
                        if len(cols) >= 9:
                            tender_no = cols[1].text.strip()
                            title = cols[2].text.strip()
                            entity = cols[3].text.strip()
                            grade = cols[4].text.strip()
                            tender_type = cols[5].text.strip()
                            tender_fee_str = cols[6].text.strip()
                            tender_bond_str = cols[7].text.strip()
                            closing_date = cols[8].text.strip()
                            
                            # Extract internal ID
                            tender_id = ""
                            view_btn = row.find('a', href=lambda href: href and 'tenderNo' in href)
                            if view_btn:
                                href = view_btn['href']
                                import urllib.parse as urlparse
                                parsed = urlparse.urlparse(href)
                                qs = urlparse.parse_qs(parsed.query)
                                if 'tenderNo' in qs:
                                    tender_id = qs['tenderNo'][0]
                                    
                            if not tender_id:
                                tender_id = tender_no # Fallback
                                
                            # Convert dates
                            from datetime import datetime, timedelta
                            try:
                                closing_date = datetime.strptime(closing_date, "%d/%m/%Y").isoformat() + "Z"
                            except ValueError:
                                closing_date = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
                                
                            opening_date = None
                            try:
                                opening_date_str = cols[9].text.strip()
                                opening_date = datetime.strptime(opening_date_str, "%d/%m/%Y").isoformat() + "Z"
                            except Exception:
                                opening_date = datetime.utcnow().isoformat() + "Z"
                                
                            if tender_no and title:
                                page_tenders.append({
                                    "tender_id": tender_no,
                                    "title": title,
                                    "entity": entity,
                                    "grade": grade,
                                    "tender_type": tender_type,
                                    "tender_fee_str": tender_fee_str,
                                    "tender_bond_str": tender_bond_str,
                                    "closing_date": closing_date,
                                    "opening_date": opening_date
                                })
                                logger.info(f"Extracted real tender: {tender_no} - {title}")
                    
                    active_tenders.extend(page_tenders)
                    if on_page_scraped:
                        try:
                            on_page_scraped(page_tenders)
                        except Exception as cb_e:
                            logger.error(f"Error in on_page_scraped callback: {str(cb_e)}")
                            
                    # Handle pagination
                    next_btn = self.driver.find_elements(By.CSS_SELECTOR, "a.paginate_button.next")
                    if next_btn and "disabled" not in next_btn[0].get_attribute("class"):
                        logger.info("Clicking next page for active tenders...")
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn[0])
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", next_btn[0])
                        time.sleep(5)
                    else:
                        break
                else:
                    logger.warning("Could not find tender table in the DOM.")
                    break
                    
        except Exception as e:
            logger.error(f"Error scraping active tenders: {str(e)}")
            
        return active_tenders

    def scrape_awarded_tenders(self, max_pages=10, on_page_scraped=None, skip_tender_nos=None):
        """Scrape completed tenders (labeled 'Awarded' in DB but we want the 30k completed ones)"""
        awarded_tenders = []
        try:
            logger.info("Navigating to public dashboard to initialize session...")
            self.driver.get("https://etendering.tenderboard.gov.om/product/publicDash")
            time.sleep(5)
            
            # Ensure we are in English
            try:
                logger.info("Switching language to English...")
                js_script = """
                document.cookie = 'etndLngCo=LTR; path=/';
                document.cookie = 'etndLngCo=LTR; path=/; domain=.etendering.tenderboard.gov.om';
                if (document.getElementById("CTRL_STRDIRECTION")) {
                    document.getElementById("CTRL_STRDIRECTION").value = 'LTR';
                }
                if (document.forms.length > 0 && document.forms[0].CTRL_STRDIRECTION) {
                    document.forms[0].CTRL_STRDIRECTION.value = 'LTR';
                }
                """
                self.driver.execute_script(js_script)
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Could not switch language: {str(e)}")

            logger.info("Clicking on 'Completed Tenders' tab via javascript...")
            self.driver.execute_script("getCompletedTenders();")
            time.sleep(5)
            
            # Wait for table to load
            logger.info("Waiting for table data to populate...")
            try:
                # We just wait for a table to exist on the page
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                time.sleep(2) # Give it an extra moment to render
                logger.info("Table data populated.")
                
            except Exception as e:
                logger.error("Timed out waiting for table data. Will try to parse whatever is there.")
            
            # Check for security/session page
            if "You are unable to access the requested page" in self.driver.page_source:
                logger.error("Security page detected. Session failed.")
                return awarded_tenders
            
            from bs4 import BeautifulSoup
            
            page = 0
            while page < max_pages:
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                target_table = None
                for table in soup.find_all("table"):
                    if "display" in table.get("class", []):
                        # Verify this table has at least 8 columns by checking its rows
                        has_8_cols = False
                        for r in table.find_all("tr")[:5]:
                            if len(r.find_all(["th", "td"])) >= 8:
                                has_8_cols = True
                                break
                        if has_8_cols:
                            target_table = table
                            break
                        
                if target_table:
                    rows = target_table.find_all("tr", class_=lambda c: c and ("odd" in c or "even" in c))
                    logger.info(f"Found awarded table with {len(rows)} rows on page {page+1}.")
                    
                    page_awarded = []
                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) >= 8:
                            # S.No: cols[0], Tender No: cols[1], Title: cols[2], Entity: cols[3], 
                            # Category: cols[4], Tender Type: cols[5], Awarded Date: cols[6], Action: cols[7]
                            
                            tender_no_td = cols[1]
                            tender_no = tender_no_td.text.split()[0].strip() if tender_no_td.text else ""
                            
                            # Often the span has the cleaner text
                            span = tender_no_td.find('span')
                            if span:
                                tender_no = span.text.split()[0].strip()
                                
                            title = cols[2].text.strip()
                            
                            # Skip pagination rows or invalid rows
                            if not tender_no or tender_no in ['Page', '«Previous', '«First'] or 'Page' in title or 'Previous' in title:
                                continue
                            
                            if skip_tender_nos and tender_no in skip_tender_nos:
                                logger.info(f"Skipping existing tender {tender_no}")
                                continue
                                
                            entity = cols[3].text.strip()
                            category_grade = cols[4].text.strip()
                            tender_type_vendor_type = cols[5].text.strip().replace('\n', '').replace('  ', '')
                            awarded_date_str = cols[6].text.strip()
                            
                            # Parse dates
                            from datetime import datetime
                            try:
                                dt = datetime.strptime(awarded_date_str, "%d-%m-%Y %H:%M:%S")
                                awarded_date = dt.isoformat() + "Z"
                            except:
                                try:
                                    dt = datetime.strptime(awarded_date_str, "%d-%m-%Y %H:%M")
                                    awarded_date = dt.isoformat() + "Z"
                                except:
                                    awarded_date = datetime.utcnow().isoformat() + "Z"
                                    
                            winner_company_name = ""
                            winning_amount = 0.0
                            
                            # Initialize bids to empty list for every tender
                            bids = []
                            
                            # Find action ID for popup
                            action_td = cols[7]
                            onclick_a = action_td.find('a', onclick=lambda x: x and 'showOpeningStatus_Report' in x)
                            if onclick_a:
                                onclick_text = onclick_a['onclick']
                                # showOpeningStatus_Report('87240','1') -> extract 87240
                                try:
                                    tender_internal_id = onclick_text.split("'")[1]
                                    
                                    # Click popup
                                    logger.info(f"Opening popup for tender {tender_no} (ID: {tender_internal_id})")
                                    self.driver.execute_script(f"showOpeningStatus_Report('{tender_internal_id}', '1')")
                                    
                                    # Save main window handle before click
                                    main_window = self.driver.current_window_handle
                                    
                                    # Wait for new window to open or 5 seconds max
                                    opened_new_window = False
                                    try:
                                        WebDriverWait(self.driver, 5).until(lambda d: len(d.window_handles) > 1)
                                        if len(self.driver.window_handles) > 1:
                                            self.driver.switch_to.window(self.driver.window_handles[-1])
                                            opened_new_window = True
                                    except Exception:
                                        # Fallback to existing handles if wait fails
                                        for handle in self.driver.window_handles:
                                            if handle != main_window:
                                                self.driver.switch_to.window(handle)
                                                opened_new_window = True
                                                break
                                    
                                    # Wait for table to render in popup
                                    try:
                                        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                                    except Exception:
                                        pass
                                        
                                    # Parse popup
                                    popup_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                                    # Find the table by locating the award.svg image first
                                    bids_table = None
                                    award_img = popup_soup.find('img', src=lambda s: s and 'award.svg' in s)
                                    if award_img:
                                        bids_table = award_img.find_parent('table')
                                    else:
                                        # Fallback to finding the first table with enough columns
                                        for table in popup_soup.find_all('table'):
                                            if len(table.find_all('tr')) > 1:
                                                bids_table = table
                                                break
                                                
                                    if bids_table:
                                        rows_popup = bids_table.find_all('tr')
                                        for row_popup in rows_popup:
                                            cols_popup = row_popup.find_all('td')
                                            if len(cols_popup) >= 4:
                                                # Check if this row is the winner (has the award.svg icon)
                                                is_winner = bool(row_popup.find('img', src=lambda s: s and 'award.svg' in s))
                                                
                                                company_name = cols_popup[1].text.strip()
                                                offer_type = cols_popup[2].text.strip() if len(cols_popup) > 2 else ""
                                                
                                                # Total Quoted Value is typically in index 3
                                                amt_str = cols_popup[3].text.strip()
                                                try:
                                                    quoted_value = float(amt_str.replace('OMR', '').replace(',', '').strip())
                                                except ValueError:
                                                    quoted_value = 0.0
                                                    
                                                status = cols_popup[4].text.strip() if len(cols_popup) > 4 else ""
                                                
                                                bids.append({
                                                    "company_name": company_name,
                                                    "offer_type": offer_type,
                                                    "total_quoted_value": quoted_value,
                                                    "status": status,
                                                    "is_winner": is_winner
                                                })
                                                
                                                if is_winner and not winner_company_name:
                                                    # Keep the top-level winner logic intact for backwards compatibility
                                                    winner_company_name = company_name
                                                    winning_amount = quoted_value
                                    
                                    # Close popup and switch back
                                    if opened_new_window:
                                        self.driver.close()
                                        self.driver.switch_to.window(main_window)
                                    else:
                                        # If it was an inline modal, try to close it so it doesn't block the next one
                                        try:
                                            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                                        except:
                                            pass
                                    
                                except Exception as e:
                                    logger.error(f"Error extracting winner for {tender_no}: {str(e)}")
                                    # Make sure to switch back if failed
                                    if len(self.driver.window_handles) > 1:
                                        self.driver.close()
                                        self.driver.switch_to.window(self.driver.window_handles[0])
                            
                            if tender_no and title:
                                page_awarded.append({
                                    "tender_no": tender_no,
                                    "tender_title": title,
                                    "entity_name": entity,
                                    "category_grade": category_grade,
                                    "tender_type_vendor_type": tender_type_vendor_type,
                                    "awarded_date": awarded_date,
                                    "winner_company_name": winner_company_name,
                                    "winning_amount": winning_amount,
                                    "submitted_bids": bids
                                })
                                logger.info(f"Extracted awarded tender: {tender_no} - Winner: {winner_company_name} ({winning_amount})")
                                
                    # Add page tenders to overall list
                    awarded_tenders.extend(page_awarded)
                    
                    # Call the callback if provided
                    if on_page_scraped:
                        try:
                            on_page_scraped(page_awarded)
                        except Exception as cb_e:
                            logger.error(f"Error in on_page_scraped callback: {str(cb_e)}")
                                
                    # Robust custom pagination for Awarded Tenders
                    try:
                        hid_max_el = self.driver.find_elements(By.NAME, "hidMax")
                        if hid_max_el:
                            total_pages = int(hid_max_el[0].get_attribute("value"))
                            if page + 1 >= total_pages:
                                logger.info(f"Reached the last page ({total_pages}).")
                                break
                            
                            logger.info(f"Navigating to page {page + 2} of {total_pages}...")
                            self.driver.execute_script(f"ShowPage({page + 2});")
                            
                            # Wait for the new page table to load
                            try:
                                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                                time.sleep(3) # Extra buffer for rendering
                            except:
                                logger.warning("Timeout waiting for next page table.")
                                
                        else:
                            # Fallback just in case it uses DataTables sometimes
                            next_btn = self.driver.find_elements(By.CSS_SELECTOR, "a.paginate_button.next")
                            if next_btn and "disabled" not in next_btn[0].get_attribute("class"):
                                logger.info("Clicking next page (DataTables fallback)...")
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn[0])
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", next_btn[0])
                                time.sleep(5)
                            else:
                                logger.info("No more pages found (DataTables fallback).")
                                break
                    except Exception as e:
                        logger.error(f"Error during pagination: {e}")
                        break
                else:
                    logger.warning("Could not find tender table in the DOM.")
                    if "Security Page" in self.driver.page_source or "unable to access" in self.driver.page_source:
                        logger.info("Session expired! Re-initializing session and jumping back to page...")
                        try:
                            self.driver.get("https://etendering.tenderboard.gov.om/product/publicDash?dashId=dash")
                            time.sleep(5)
                            try:
                                lang_btn = self.driver.find_element(By.XPATH, "//a[contains(text(), 'English')]")
                                lang_btn.click()
                                time.sleep(5)
                            except:
                                pass
                                
                            self.driver.execute_script("document.getElementById('CTRL_STRDIRECTION').value = 'LTR';")
                            self.driver.execute_script("getCompletedTenders();")
                            time.sleep(5)
                            
                            logger.info(f"Jumping back to page {page + 1}...")
                            self.driver.execute_script(f"ShowPage({page + 1});")
                            
                            try:
                                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                                time.sleep(3)
                            except:
                                pass
                                
                            continue  # Retry parsing this page
                        except Exception as retry_e:
                            logger.error(f"Failed to recover session: {retry_e}")
                            break
                    else:
                        break
                
                page += 1
                    
        except Exception as e:
            logger.error(f"Error scraping awarded tenders: {str(e)}")
            
        return awarded_tenders

    def download_documents(self, tender_id):
        """
        Scaffolding: Download PDF documents for a specific tender to local storage.
        """
        storage_dir = os.path.join(".", "documents", "raw_pdfs")
        os.makedirs(storage_dir, exist_ok=True)
        downloaded_files = []
        
        logger.info(f"Fetching documents for tender {tender_id}...")
        try:
            # Navigate to tender detail page
            self.driver.get(f"{self.base_url}/tender/detail/{tender_id}")
            time.sleep(2)
            
            # Find download links (adjust selector later)
            pdf_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href$='.pdf']")
            
            for link in pdf_links:
                url = link.get_attribute("href")
                filename = url.split("/")[-1]
                filepath = os.path.join(storage_dir, filename)
                
                logger.info(f"Downloading {filename}...")
                # Note: For actual downloading in Selenium, we might need to click the link 
                # and rely on Chrome's default download directory, OR use requests with cookies.
                # This is scaffolding for the requests approach.
                cookies = {c['name']: c['value'] for c in self.driver.get_cookies()}
                response = requests.get(url, cookies=cookies)
                
                with open(filepath, "wb") as f:
                    f.write(response.content)
                logger.info(f"Saved to {filepath}")
                downloaded_files.append(filepath)
                
        except Exception as e:
            logger.error(f"Error downloading documents for {tender_id}: {str(e)}")
            
        return downloaded_files

    def close(self):
        logger.info("Closing browser session.")
        self.driver.quit()

if __name__ == "__main__":
    # Replace these with your actual test credentials for the portal
    TEST_USER = "your_actual_username"
    TEST_PASS = "your_actual_password"
    
    scraper = OmanTenderScraper(TEST_USER, TEST_PASS)
    scraper.login()
    
    # Keeping it open for 15 seconds so you can see if the login worked
    time.sleep(15) 
    scraper.close()