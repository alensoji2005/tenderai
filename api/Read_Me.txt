Problem: They work from "tender enquiry stage" with government authorities - manually tracking tenders is inefficient
Solution:

Real-time tender scraping from Oman government portals (MEDC, MJEC, OETC, PDO)

ML model to predict bid success probability based on historical data, equipment type, pricing

Automated document generation for tender responses

Competitor analysis dashboard showing who won similar tenders
Tech Stack: Python (FastAPI), BeautifulSoup/Scrapy, TensorFlow/PyTorch, PostgreSQL, React

cd D:\projects\tenderai-oman
.\venv\Scripts\activate

start your FastAPI server
uvicorn api.main:app --reload

no no no, there are over 30,000 records in the awarded section, idk why you keep insisting there is only about 4000. whats the glitch happenign that makes you think only 4000ish is present? see the screenshot, thats the end of the section where its clearly seen that the oldest record is number 30414 so why r we stopping at aroung page 90 (4400ish). see whats wrong and fix it, i need all 30000+ records added to my db