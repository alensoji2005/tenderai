# scraper/pdf_parser.py
import pdfplumber
import re
import json
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LocalPDFExtractor:
    def __init__(self):
        # We can add Spacy here later for more complex text extraction.
        # For now, pdfplumber's table extraction is perfectly suited for BOQs.
        pass

    def extract_boq(self, pdf_path: str) -> List[Dict]:
        """
        Extract Bill of Quantities (BOQ) using pdfplumber to extract tables
        and local logic to structure the data.
        """
        boq_items = []
        logger.info(f"Extracting tables from {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                            
                        # Basic heuristic to check if table is a BOQ table
                        # Join all non-None cells in the first row
                        header_row = [str(cell).lower().strip() for cell in table[0] if cell is not None]
                        header_text = " ".join(header_row)
                        
                        if "description" in header_text or "qty" in header_text or "quantity" in header_text:
                            logger.info(f"Found potential BOQ table on page {page_num + 1}")
                            # Find indices for relevant columns
                            desc_idx = -1
                            qty_idx = -1
                            unit_idx = -1
                            
                            for i, cell in enumerate(table[0]):
                                if cell is None: continue
                                val = str(cell).lower()
                                if "description" in val or "item" in val: desc_idx = i
                                elif "qty" in val or "quantity" in val: qty_idx = i
                                elif "unit" in val: unit_idx = i
                            
                            if desc_idx == -1 or qty_idx == -1:
                                logger.warning("Could not identify Description or Quantity columns.")
                                continue
                                
                            # Parse rows
                            for row in table[1:]:
                                if len(row) > max(desc_idx, qty_idx):
                                    desc = row[desc_idx]
                                    qty_str = row[qty_idx]
                                    unit = row[unit_idx] if unit_idx != -1 and len(row) > unit_idx else "Nos"
                                    
                                    if not desc or not qty_str: continue
                                    
                                    # Clean qty
                                    try:
                                        qty = float(re.sub(r'[^\d.]', '', str(qty_str)))
                                    except ValueError:
                                        continue # Skip header/footer rows
                                        
                                    boq_items.append({
                                        "item_description": str(desc).replace('\n', ' ').strip(),
                                        "quantity": qty,
                                        "unit": str(unit).strip() if unit else "Nos"
                                    })

            return boq_items
        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            return []

if __name__ == "__main__":
    # Test script with our dummy PDF
    extractor = LocalPDFExtractor()
    items = extractor.extract_boq("documents/raw_pdfs/sample_tender.pdf")
    print(json.dumps(items, indent=2))
