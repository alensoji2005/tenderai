# scraper/oman_tender_scraper.py
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

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
        self.base_url = "https://etendering.tenderboard.gov.om"
        
        logger.info("Initializing Undetected ChromeDriver...")
        options = uc.ChromeOptions()
        # Keep headless disabled for now so we can visually watch the bot navigate
        # options.add_argument('--headless') 
        
        self.driver = uc.Chrome(options=options)
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

            # Find the login button using a CSS Selector since it lacks an ID
            login_button = self.driver.find_element(By.CSS_SELECTOR, "input[value='Login']")
            login_button.click()
            logger.info("Clicked login button. Waiting for dashboard...")

            # Wait for a specific element that only appears AFTER successful login to confirm
            time.sleep(5) 
            logger.info("Login sequence completed. Please verify the browser state.")

        except Exception as e:
            logger.error(f"Scraper encountered an error: {str(e)}")

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