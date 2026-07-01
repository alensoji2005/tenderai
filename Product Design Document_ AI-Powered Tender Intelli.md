<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Product Design Document: AI-Powered Tender Intelligence \& Bid Optimization Platform

**Document Version:** 1.0
**Date:** June 18, 2026
**Project Name:** TenderAI Oman (Working Title)
**Target Customer:** Global Corp Enterprises LLC, Muscat, Oman
**Development Timeline:** 12 weeks (MVP)
**Tech Stack:** Python (FastAPI), TensorFlow/PyTorch, PostgreSQL, React, Selenium/BeautifulSoup/Scrapy

***

## 1. Executive Summary

### Problem Statement

Global Corp Enterprises LLC works from the "tender enquiry stage" with Omani government authorities (MEDC, MJEC, OETC, PDO, Ministry of Defense). Currently, they manually track tenders across multiple portals, which is:

- **Time-intensive:** 5-6 hours/day spent searching tender portals
- **Inefficient:** Misses opportunities due to human error
- **No strategic intelligence:** No data on bid success probability, competitor analysis, or optimal pricing


### Solution Overview

An AI-powered platform that:

1. **Real-time tender scraping** from Oman government portals (Oman Tender Board, MEDC, MJEC, OETC, PDO)
2. **ML-powered bid success prediction** (probability of winning based on historical data, equipment type, pricing)
3. **Automated document generation** for tender responses (compliance matrix, technical proposal, financial bid)
4. **Competitor analysis dashboard** showing who won similar tenders, win rates, pricing patterns

### Success Metrics

| Metric | Target |
| :-- | :-- |
| Time saved | 100+ hours/month (5-6 hours/day) |
| Win rate increase | 35-40% (with AI predictions) |
| Tender coverage | 100% of Oman electrical equipment tenders |
| ML accuracy | 85-92% (bid success prediction) |
| Document generation time | 30 minutes vs. 4-5 hours manually |


***

## 2. System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE (React)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Tender Search│  │ Dashboard    │  │ Document Gen │               │
│  │ & Filtering  │  │ & Analytics  │  │ & Export     │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                                ▼ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI - Python)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ /tenders     │  │ /predict     │  │ /documents   │               │
│  │ /competitors │  │ /pricing     │  │ /alerts      │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                    ▼                        ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│    ML SERVICE            │    │   SCRAPER SERVICE        │
│  (TensorFlow/PyTorch)    │    │  (Selenium/Scrapy)       │
│  ┌────────────────────┐  │    │  ┌────────────────────┐  │
│  │ BidSuccessModel    │  │    │  │ OmanTenderScraper  │  │
│  │ PricingOptimizer   │  │    │  │ PDFFetcher         │  │
│  │ CompetitorAnalyzer │  │    │  │ Deduplication      │  │
│  └────────────────────┘  │    │  └────────────────────┘  │
└──────────────────────────┘    └──────────────────────────┘
           ▼                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ PostgreSQL   │  │   MinIO/S3   │  │    Redis     │               │
│  │ (Structured) │  │  (PDFs)      │  │ (Cache)      │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   EXTERNAL PORTALS (Scraped)                         │
│  Oman Tender Board │ MEDC │ MJEC │ OETC │ PDO │ TendersArabia API   │
└─────────────────────────────────────────────────────────────────────┘
```


***

## 3. Core Modules \& Features

### Module 1: Tender Scraper \& Data Pipeline

#### Purpose

Automatically collect tender data from Oman government portals, parse documents, and store in structured database.

#### Data Sources

| Portal | URL | Authentication | Scraping Method |
| :-- | :-- | :-- | :-- |
| Oman Tender Board | `https://etendering.tenderboard.gov.om` | Login required | Selenium + Cookie handling |
| MEDC (Ministry of Energy) | `https://www.medc.gov.om` | Public | BeautifulSoup |
| MJEC (Ministry of Justice) | `https://www.mjec.gov.om` | Public | BeautifulSoup |
| OETC (Oman Electricity) | `https://www.oetc.gov.om` | Login required | Selenium |
| PDO (Petroleum Development Oman) | `https://www.pdo.co.om` | Login required | Selenium |
| TendersArabia (API) | `https://tendersarabia.com` | Paid API | REST API integration [^1] |

#### Data Points to Extract

```python
# Core tender data structure
Tender = {
    # Identification
    "tender_id": str,           # Unique ID (e.g., "OM-2026-0458")
    "title": str,               # Tender title
    "category": str,            # e.g., "Electrical Equipment", "Transmission"
    "subcategory": str,         # e.g., "CT/VT Transformers", "Insulators"
    
    # Dates
    "publish_date": datetime,   # When tender was published
    "opening_date": datetime,   # Bid opening date
    "closing_date": datetime,   # Submission deadline (CRITICAL)
    "validity_period": int,     # Days tender is valid
    
    # Financial
    "estimated_value": float,   # Estimated project value (OMR)
    "currency": str,            # "OMR" (Omani Rial)
    "bid_fee": float,           # Tender fee to apply (OMR)
    "emd_amount": float,        # Earnest Money Deposit (OMR)
    
    # Technical
    "technical_specs": str,     # Summary of requirements
    "boq": list,                # Bill of Quantities (parsed from PDF)
    "documents": list,          # URLs to PDF documents
    
    # Eligibility
    "eligibility_requirements": dict,  # e.g., {"iso_certified": True, "min_experience": 5}
    "geographical_scope": str,         # e.g., "Muscat", "All Oman"
    
    # Competition
    "num_bidders": int,         # Number of registered bidders (if visible)
    "incumbent_supplier": str,  # Current supplier (if renewal)
    
    # Outcome (historical data only)
    "status": str,              # "active", "closed", "awarded", "cancelled"
    "winner_company": str,      # Company that won (if awarded)
    "l1_bid_price": float,      # Winning bid price (if available)
    "award_date": datetime,     # When contract was awarded
}
```


#### Scraper Implementation Details

```python
"""
FILE: scraper/oman_tender_scraper.py
PURPOSE: Main scraper for Oman Tender Board (login-required portal)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import requests
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class OmanTenderScraper:
    """
    Scraper for Oman Tender Board (etendering.tenderboard.gov.om)
    
    Key Challenges:
    - Login required (session management)
    - Dynamic table loading (pagination)
    - PDF document extraction
    - Anti-bot detection (rate limiting)
    """
    
    def __init__(self, config: dict):
        """
        Args:
            config: {
                "username": str,
                "password": str,
                "base_url": str = "https://etendering.tenderboard.gov.om",
                "max_pages": int = 100,
                "rate_limit_seconds": int = 5
            }
        """
        self.username = config["username"]
        self.password = config["password"]
        self.base_url = config["base_url"]
        self.max_pages = config["max_pages"]
        self.rate_limit = config["rate_limit_seconds"]
        
        # Initialize Selenium WebDriver
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 10)
        self.session_cookies = None
        
    def login(self) -> bool:
        """
        Login to Oman Tender Board and store session cookies.
        
        Returns:
            bool: True if login successful
        """
        try:
            # Navigate to login page
            self.driver.get(f"{self.base_url}/product/publicDash")
            
            # Wait for login form
            login_form = self.wait.until(
                EC.presence_of_element_located((By.ID, "login-form"))
            )
            
            # Fill credentials
            self.driver.find_element(By.NAME, "username").send_keys(self.username)
            self.driver.find_element(By.NAME, "password").send_keys(self.password)
            
            # Submit form
            self.driver.find_element(By.ID, "login-btn").click()
            
            # Wait for successful login (redirect to dashboard)
            time.sleep(3)
            
            # Store session cookies
            self.session_cookies = self.driver.get_cookies()
            
            logger.info("Login successful to Oman Tender Board")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
    
    def scrape_active_tenders(self) -> list:
        """
        Scrape all active tenders from Oman Tender Board.
        
        Returns:
            list: List of Tender dictionaries
        """
        tenders = []
        
        if not self.session_cookies:
            if not self.login():
                raise Exception("Authentication failed")
        
        # Navigate to active tenders page
        self.driver.get(f"{self.base_url}/product/activeTenders")
        
        # Wait for tender table to load
        time.sleep(2)
        
        # Paginate through all pages
        for page_num in range(self.max_pages):
            logger.info(f"Scraping page {page_num + 1}")
            
            # Parse current page
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract tender table rows
            tender_rows = soup.find_all('tr', class_='tender-row')
            
            for row in tender_rows:
                tender = self.parse_tender_row(row)
                if tender:
                    tenders.append(tender)
            
            # Check for next page button
            next_btn = soup.find('a', class_='next-page')
            if not next_btn:
                break
            
            # Click next page
            next_btn.click()
            time.sleep(self.rate_limit)
        
        logger.info(f"Scraped {len(tenders)} active tenders")
        return tenders
    
    def parse_tender_row(self, row: BeautifulSoup) -> dict:
        """
        Parse a single tender row from HTML.
        
        Args:
            row: BeautifulSoup row element
            
        Returns:
            dict: Tender dictionary with extracted fields
        """
        try:
            # Extract columns from row
            cells = row.find_all('td')
            
            tender = {
                "tender_id": cells[^0].text.strip(),
                "title": cells[^1].text.strip(),
                "category": cells[^2].text.strip(),
                "estimated_value": float(cells[^3].text.strip().replace("OMR", "")),
                "closing_date": datetime.strptime(
                    cells[^4].text.strip(), "%d/%m/%Y"
                ),
                "documents_url": cells[^5].find('a')['href'],
                "status": "active"
            }
            
            return tender
            
        except Exception as e:
            logger.error(f"Failed to parse tender row: {str(e)}")
            return None
    
    def fetch_tender_documents(self, tender_id: str) -> list:
        """
        Download PDF documents for a specific tender.
        
        Args:
            tender_id: Tender unique identifier
            
        Returns:
            list: List of (filename, pdf_content) tuples
        """
        documents = []
        
        # Get tender detail page
        detail_url = f"{self.base_url}/tender/detail/{tender_id}"
        self.driver.get(detail_url)
        time.sleep(2)
        
        # Find all PDF download links
        pdf_links = self.driver.find_elements(By.CSS_SELECTOR, "a.pdf-link")
        
        for link in pdf_links:
            pdf_url = link.get_attribute("href")
            pdf_filename = link.text.strip()
            
            # Download PDF
            response = requests.get(pdf_url)
            documents.append((pdf_filename, response.content))
            
            # Save to MinIO/S3
            self.save_pdf_to_storage(tender_id, pdf_filename, response.content)
        
        return documents
    
    def save_pdf_to_storage(self, tender_id: str, filename: str, content: bytes):
        """
        Save PDF to MinIO/S3 storage.
        
        Args:
            tender_id: Tender ID
            filename: Original PDF filename
            content: PDF binary content
        """
        # Implementation depends on storage backend
        # Example: MinIO client
        from minio import Minio
        
        minio_client = Minio(
            "minio.globalcorp.local",
            access_key="your_access_key",
            secret_key="your_secret_key"
        )
        
        minio_client.put_object(
            bucket_name="tender-documents",
            object_name=f"{tender_id}/{filename}",
            data=content,
            length=len(content)
        )
    
    def close(self):
        """Close Selenium WebDriver"""
        self.driver.close()


# Usage Example
if __name__ == "__main__":
    config = {
        "username": "your_username",
        "password": "your_password",
        "base_url": "https://etendering.tenderboard.gov.om",
        "max_pages": 100,
        "rate_limit_seconds": 5
    }
    
    scraper = OmanTenderScraper(config)
    tenders = scraper.scrape_active_tenders()
    
    # Save to PostgreSQL
    from database import save_tenders
    save_tenders(tenders)
    
    scraper.close()
```


#### PDF Parsing Module

```python
"""
FILE: scraper/pdf_parser.py
PURPOSE: Extract structured data from tender PDF documents (BOQ, technical specs)
"""

import pdfplumber
import re
from typing import List, Dict

class TenderPDFParser:
    """
    Parser for Oman tender PDF documents.
    
    Extracts:
    - Bill of Quantities (BOQ)
    - Technical specifications
    - Eligibility requirements
    - Timeline details
    """
    
    def __init__(self):
        self.boq_patterns = [
            r'S/N\s+Description\s+Quantity\s+Unit\s+Rate',
            r'Item\s+Description\s+Qty\s+Unit',
            r'No.\s+Item Description\s+Quantity',
        ]
    
    def parse_boq(self, pdf_content: bytes) -> List[Dict]:
        """
        Extract Bill of Quantities from PDF.
        
        Args:
            pdf_content: PDF binary content
            
        Returns:
            List of BOQ items: [{"item": str, "quantity": float, "unit": str}, ...]
        """
        boq_items = []
        
        # Extract text from PDF
        with pdfplumber.open(pdf_content) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
        
        # Find BOQ table using pattern matching
        for pattern in self.boq_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract table rows after pattern
                boq_text = text[match.end():match.end()+2000]  # 2000 chars after pattern
                rows = boq_text.split('\n')
                
                for row in rows:
                    # Parse each row (depends on PDF format)
                    items = row.split()
                    if len(items) >= 3:
                        boq_item = {
                            "item": items[^1],
                            "quantity": float(items[^2]),
                            "unit": items[^3] if len(items) > 3 else "unit"
                        }
                        boq_items.append(boq_item)
        
        return boq_items
    
    def extract_technical_specs(self, pdf_content: bytes) -> str:
        """
        Extract technical specifications from PDF.
        
        Args:
            pdf_content: PDF binary content
            
        Returns:
            str: Summary of technical requirements
        """
        with pdfplumber.open(pdf_content) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
        
        # Find technical specs section (keyword-based)
        specs_keywords = [
            "technical specification",
            "technical requirements",
            "scope of work",
            "equipment specifications"
        ]
        
        for keyword in specs_keywords:
            match = re.search(
                rf'{keyword}.*?(?=\n\n|\Z)',
                text,
                re.IGNORECASE | re.DOTALL
            )
            if match:
                return match.group(0)
        
        return text  # Return full text if no section found
```


***

### Module 2: ML Bid Success Prediction Model

#### Purpose

Predict probability of winning a tender based on company profile, tender characteristics, pricing strategy, and historical competition data.

#### Data Requirements

```python
"""
FILE: ml/data_requirements.py
PURPOSE: Define minimum dataset requirements for training ML model
"""

TRAINING_DATA_REQUIREMENTS = {
    # Minimum dataset
    "min_tenders": 500,  # Historical tenders with win/loss outcome
    "min_years": 3,      # At least 3 years of historical data
    "target_categories": [
        "Electrical Equipment",
        "Transmission & Distribution",
        "Transformers",
        "CT/VT",
        "Insulators",
        "Substation Equipment"
    ],
    
    # Features per tender (required columns)
    "required_features": [
        # Company attributes
        "company_years_in_business",
        "company_iso_certified",
        "company_past_win_rate",
        "company_financial_strength_score",
        
        # Tender attributes
        "tender_value",
        "tender_category",
        "tender_deadline_days",
        "tender_complexity_score",
        "tender_geographical_scope",
        
        # Pricing
        "your_bid_price",
        "estimated_l1_price",
        "price_margin_percent",
        "emd_amount",
        
        # Competition
        "num_bidders",
        "competitor_avg_win_rate",
        "incumbent_supplier_present",
        
        # Historical patterns
        "department_avg_win_rate",
        "seasonal_win_rate",
        "avg_cycle_time_days",
        
        # Outcome (label)
        "won_tender",  # 1 = win, 0 = loss
        "winning_price"  # L1 price (if won)
    ]
}
```


#### ML Model Architecture

```python
"""
FILE: ml/bid_success_predictor.py
PURPOSE: ML model for predicting bid success probability
"""

import tensorflow as tf
from tensorflow.keras import layers, Model
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class BidSuccessPredictor:
    """
    Multi-feature ML model for predicting tender win probability.
    
    Architecture:
    - Input layers for different feature types (company, tender, pricing, competition)
    - Embedding layers for categorical features
    - Dense layers for feature integration
    - Dropout for regularization
    - Output: Probability of winning (0-1)
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.encoder = OneHotEncoder()
        self.feature_columns = self.define_feature_columns()
    
    def define_feature_columns(self) -> dict:
        """
        Define feature columns by type (numeric, categorical).
        
        Returns:
            dict: Feature column definitions
        """
        return {
            "numeric": [
                "company_years_in_business",
                "company_past_win_rate",
                "company_financial_strength_score",
                "tender_value",
                "tender_deadline_days",
                "tender_complexity_score",
                "your_bid_price",
                "estimated_l1_price",
                "price_margin_percent",
                "emd_amount",
                "num_bidders",
                "competitor_avg_win_rate",
                "department_avg_win_rate",
                "seasonal_win_rate",
                "avg_cycle_time_days"
            ],
            "categorical": [
                "company_iso_certified",
                "tender_category",
                "tender_geographical_scope",
                "incumbent_supplier_present"
            ]
        }
    
    def build_model(self) -> Model:
        """
        Build multi-input TensorFlow model.
        
        Returns:
            Model: Compiled TensorFlow model
        """
        # Input layers for each feature type
        numeric_input = layers.Input(shape=(len(self.feature_columns["numeric"]),), name="numeric_features")
        categorical_input = layers.Input(shape=(len(self.feature_columns["categorical"]),), name="categorical_features")
        
        # Embedding layers for numeric features
        numeric_emb = layers.Dense(64, activation="relu", name="numeric_embedding")(numeric_input)
        numeric_emb = layers.Dropout(0.3)(numeric_emb)
        numeric_emb = layers.Dense(32, activation="relu")(numeric_emb)
        
        # Embedding layers for categorical features
        categorical_emb = layers.Dense(32, activation="relu", name="categorical_embedding")(categorical_input)
        categorical_emb = layers.Dropout(0.3)(categorical_emb)
        categorical_emb = layers.Dense(16, activation="relu")(categorical_emb)
        
        # Concatenate embeddings
        combined = layers.concatenate([numeric_emb, categorical_emb])
        
        # Deep integration layers
        x = layers.Dense(128, activation="relu")(combined)
        x = layers.Dropout(0.4)(x)
        x = layers.Dense(64, activation="relu")(x)
        x = layers.Dropout(0.3)(x)
        x = layers.Dense(32, activation="relu")(x)
        
        # Output layer (probability 0-1)
        output = layers.Dense(1, activation="sigmoid", name="win_probability")(x)
        
        # Create model
        model = Model(
            inputs=[numeric_input, categorical_input],
            outputs=output,
            name="BidSuccessPredictor"
        )
        
        return model
    
    def preprocess_data(self, df: pd.DataFrame) -> tuple:
        """
        Preprocess raw data for model training.
        
        Args:
            df: DataFrame with raw tender data
            
        Returns:
            tuple: (numeric_features, categorical_features, labels)
        """
        # Extract numeric features
        numeric_features = df[self.feature_columns["numeric"]].values
        
        # Encode categorical features
        categorical_features = self.encoder.fit_transform(
            df[self.feature_columns["categorical"]]
        ).toarray()
        
        # Scale numeric features
        numeric_features = self.scaler.fit_transform(numeric_features)
        
        # Extract labels
        labels = df["won_tender"].values
        
        return numeric_features, categorical_features, labels
    
    def train(self, training_data: pd.DataFrame, epochs: int = 100) -> None:
        """
        Train the ML model on historical data.
        
        Args:
            training_data: DataFrame with historical tenders (min 500 rows)
            epochs: Number of training epochs
        """
        logger.info("Starting model training...")
        
        # Preprocess data
        numeric_features, categorical_features, labels = self.preprocess_data(training_data)
        
        # Build model
        self.model = self.build_model()
        
        # Compile model
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss="binary_crossentropy",
            metrics=["accuracy", tf.keras.metrics.AUC(name="auc")]
        )
        
        # Train model
        history = self.model.fit(
            {"numeric_features": numeric_features, "categorical_features": categorical_features},
            labels,
            epochs=epochs,
            batch_size=32,
            validation_split=0.2,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
                tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=5)
            ]
        )
        
        logger.info(f"Training completed. Final accuracy: {history.history['accuracy'][-1]}")
        
        # Save model
        self.model.save("models/bid_success_predictor_v1.h5")
    
    def predict(self, tender_data: dict) -> float:
        """
        Predict win probability for a new tender.
        
        Args:
            tender_data: Dictionary with tender features
            
        Returns:
            float: Win probability (0-1)
        """
        # Preprocess input
        numeric_features = np.array([
            tender_data[col] for col in self.feature_columns["numeric"]
        ])
        numeric_features = self.scaler.transform(numeric_features.reshape(1, -1))
        
        categorical_features = np.array([
            tender_data[col] for col in self.feature_columns["categorical"]
        ])
        categorical_features = self.encoder.transform(categorical_features.reshape(1, -1)).toarray()
        
        # Predict
        numeric_features = numeric_features.reshape(1, -1)
        categorical_features = categorical_features.reshape(1, -1)
        
        prediction = self.model.predict({
            "numeric_features": numeric_features,
            "categorical_features": categorical_features
        })
        
        return prediction[^0][^0]
    
    def get_confidence_interval(self, tender_data: dict) -> tuple:
        """
        Get confidence interval for prediction (Monte Carlo dropout).
        
        Args:
            tender_data: Dictionary with tender features
            
        Returns:
            tuple: (lower_bound, upper_bound)
        """
        # Run multiple predictions with dropout active
        predictions = []
        for _ in range(100):
            prob = self.predict(tender_data)
            predictions.append(prob)
        
        lower_bound = np.percentile(predictions, 5)
        upper_bound = np.percentile(predictions, 95)
        
        return lower_bound, upper_bound


# Feature Importance Analysis
class FeatureImportanceAnalyzer:
    """
    Analyze which features most influence win probability predictions.
    """
    
    def __init__(self, model: Model):
        self.model = model
    
    def calculate_importance(self, training_data: pd.DataFrame) -> dict:
        """
        Calculate feature importance using permutation importance.
        
        Args:
            training_data: DataFrame with training features
            
        Returns:
            dict: Feature importance scores
        """
        from sklearn.inspection import permutation_importance
        
        # Preprocess data
        numeric_features, categorical_features, labels = self.preprocess_data(training_data)
        
        # Combine features
        combined_features = np.concatenate([numeric_features, categorical_features], axis=1)
        
        # Calculate permutation importance
        importance = permutation_importance(
            self.model, combined_features, labels, n_repeats=10
        )
        
        # Map back to feature names
        feature_importance = {}
        for i, col in enumerate(self.feature_columns["numeric"] + self.feature_columns["categorical"]):
            feature_importance[col] = importance[i]
        
        return feature_importance
```


#### Pricing Optimizer Module

```python
"""
FILE: ml/pricing_optimizer.py
PURPOSE: Recommend optimal bid price to maximize win probability while maintaining profit margin
"""

import numpy as np
from scipy.optimize import minimize_scalar
from bid_success_predictor import BidSuccessPredictor

class PricingOptimizer:
    """
    Optimize bid price using:
    - Win probability model
    - Historical L1 price patterns
    - Desired profit margin
    """
    
    def __init__(self, win_predictor: BidSuccessPredictor):
        self.win_predictor = win_predictor
    
    def recommend_price(
        self,
        tender_data: dict,
        min_profit_margin: float = 0.15,  # 15% minimum margin
        target_win_probability: float = 0.70  # 70% target win rate
    ) -> dict:
        """
        Recommend optimal bid price.
        
        Args:
            tender_data: Dictionary with tender features (excluding price)
            min_profit_margin: Minimum profit margin (15%)
            target_win_probability: Target win probability (70%)
            
        Returns:
            dict: {
                "recommended_price": float,
                "win_probability": float,
                "profit_margin": float,
                "price_range": {
                    "aggressive": float,  # Higher win rate, lower margin
                    "balanced": float,    # Target win rate
                    "conservative": float # Higher margin, lower win rate
                }
            }
        """
        estimated_l1 = tender_data["estimated_l1_price"]
        
        # Define objective function: maximize profit while meeting win probability target
        def objective_function(bid_price):
            # Update tender data with new price
            tender_data["your_bid_price"] = bid_price
            tender_data["price_margin_percent"] = (bid_price - estimated_l1) / estimated_l1
            
            # Calculate win probability
            win_prob = self.win_predictor.predict(tender_data)
            
            # Calculate profit
            profit = bid_price * min_profit_margin
            
            # Objective: maximize profit if win_prob >= target, else penalize
            if win_prob >= target_win_probability:
                return -profit  # Negative because we're minimizing
            else:
                return 100000  # Heavy penalty for missing win probability target
        
        # Optimize price
        result = minimize_scalar(
            objective_function,
            bounds=(estimated_l1 * 0.95, estimated_l1 * 1.30),  # 95%-130% of L1
            method="bounded"
        )
        
        recommended_price = result.x
        
        # Calculate metrics
        tender_data["your_bid_price"] = recommended_price
        tender_data["price_margin_percent"] = (recommended_price - estimated_l1) / estimated_l1
        win_prob = self.win_predictor.predict(tender_data)
        profit_margin = (recommended_price - estimated_l1) / recommended_price
        
        # Price ranges
        price_range = {
            "aggressive": estimated_l1 * 0.98,  # 98% of L1 (higher win rate)
            "balanced": recommended_price,       # Optimized price
            "conservative": estimated_l1 * 1.15  # 115% of L1 (higher margin)
        }
        
        return {
            "recommended_price": recommended_price,
            "win_probability": win_prob,
            "profit_margin": profit_margin,
            "price_range": price_range
        }
```


***

### Module 3: Automated Document Generation

#### Purpose

Automatically generate tender response documents (compliance matrix, technical proposal, financial bid) using templates and AI.

```python
"""
FILE: documents/tender_document_generator.py
PURPOSE: Generate tender response documents automatically
"""

from docx import Document
from docx.shared import Pt
from transformers import pipeline
import pdfplumber
import re
from typing import Dict, List

class TenderDocumentGenerator:
    """
    Automated tender document generator for Oman government tenders.
    
    Generates:
    1. Compliance Matrix (technical compliance table)
    2. Technical Proposal (scope of work, equipment specifications)
    3. Financial Bid (BOQ with pricing)
    4. Company Documents (certificates, licenses - auto-attach)
    """
    
    def __init__(self, company_profile: Dict):
        """
        Args:
            company_profile: {
                "company_name": str,
                "address": str,
                "phone": str,
                "email": str,
                "iso_certifications": List[str],
                "past_projects": List[Dict],
                "financial_strength": str,
                "years_in_business": int
            }
        """
        self.company_profile = company_profile
        
        # AI summarization model (for proposal writing)
        self.summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn"
        )
        
        # Template directory
        self.template_dir = "templates/oman_tenders/"
    
    def generate_compliance_matrix(
        self,
        tender_specs: str,
        company_capabilities: Dict
    ) -> Document:
        """
        Generate technical compliance matrix.
        
        Args:
            tender_specs: Technical specifications from tender PDF
            company_capabilities: Company's equipment capabilities
            
        Returns:
            Document: Word document with compliance table
        """
        doc = Document()
        
        # Add title
        doc.add_heading("TECHNICAL COMPLIANCE MATRIX", 0)
        
        # Add company info
        doc.add_paragraph(f"Company: {self.company_profile['company_name']}")
        doc.add_paragraph(f"Tender Reference: {tender_specs.get('tender_id')}")
        
        # Parse requirements from tender specs
        requirements = self.extract_requirements(tender_specs["technical_text"])
        
        # Create compliance table
        table = doc.add_table(style="Table Grid")
        table.style = "Table Grid"
        
        # Add headers
        header_row = table.rows[^0].cells
        header_row[^0].text = "S/N"
        header_row[^1].text = "Requirement"
        header_row[^2].text = "Compliance Status"
        header_row[^3].text = "Remarks"
        
        # Add requirement rows
        for i, req in enumerate(requirements):
            row = table.add_row().cells
            row[^0].text = str(i + 1)
            row[^1].text = req["requirement"]
            row[^2].text = "COMPLIANT" if self.is_compliant(req, company_capabilities) else "NON-COMPLIANT"
            row[^3].text = self.get_compliance_remark(req, company_capabilities)
        
        # Add certification appendix
        doc.add_heading("CERTIFICATIONS", 1)
        for cert in self.company_profile["iso_certifications"]:
            doc.add_paragraph(f"✓ ISO {cert} Certified")
        
        return doc
    
    def extract_requirements(self, technical_text: str) -> List[Dict]:
        """
        Extract technical requirements from tender text.
        
        Args:
            technical_text: Full technical specifications text
            
        Returns:
            List of requirements: [{"requirement": str, "critical": bool}, ...]
        """
        requirements = []
        
        # Split by common requirement patterns
        requirement_patterns = [
            r"provide\s+([^.]+)",
            r"must\s+be\s+([^.]+)",
            r"shall\s+([^.]+)",
            r"requirement:\s*([^.]+)"
        ]
        
        for pattern in requirement_patterns:
            matches = re.finditer(pattern, technical_text, re.IGNORECASE)
            for match in matches:
                requirement = {
                    "requirement": match.group(1).strip(),
                    "critical": "critical" in match.group(1).lower() or "mandatory" in match.group(1).lower()
                }
                requirements.append(requirement)
        
        return requirements
    
    def is_compliant(self, requirement: Dict, capabilities: Dict) -> bool:
        """
        Check if company is compliant with requirement.
        
        Args:
            requirement: Requirement dict
            capabilities: Company capabilities dict
            
        Returns:
            bool: True if compliant
        """
        req_text = requirement["requirement"].lower()
        
        # Check against company capabilities
        for capability in capabilities.get("equipment_specs", []):
            if capability.lower() in req_text:
                return True
        
        return False
    
    def get_compliance_remark(self, requirement: Dict, capabilities: Dict) -> str:
        """
        Generate compliance remark.
        
        Args:
            requirement: Requirement dict
            capabilities: Company capabilities dict
            
        Returns:
            str: Remark text
        """
        if self.is_compliant(requirement, capabilities):
            return f"Company offers equipment meeting this specification"
        else:
            return "Non-compliant - alternative equipment not suitable"
    
    def generate_technical_proposal(
        self,
        tender_specs: Dict,
        past_successful_bids: List[Dict]
    ) -> Document:
        """
        Generate technical proposal using AI and past successful bids.
        
        Args:
            tender_specs: Tender specifications
            past_successful_bids: List of past winning bid documents
            
        Returns:
            Document: Word document with technical proposal
        """
        doc = Document()
        
        # Add title
        doc.add_heading("TECHNICAL PROPOSAL", 0)
        
        # Add company introduction
        doc.add_heading("1. COMPANY INTRODUCTION", 1)
        intro = f"""
        {self.company_profile['company_name']} is a well-established trading company 
        based in Muscat, Sultanate of Oman, specializing in Transmission & Distribution 
        equipment. We have {self.company_profile['years_in_business']} years of experience 
        serving government authorities including MEDC, MJEC, OETC, PDO, and Ministry of Defense.
        
        Our certifications include: {', '.join(self.company_profile['iso_certifications'])}
        """
        doc.add_paragraph(intro)
        
        # Add scope of work (AI-generated from tender specs)
        doc.add_heading("2. SCOPE OF WORK", 1)
        scope = self.generate_scope_of_work(tender_specs)
        doc.add_paragraph(scope)
        
        # Add equipment specifications
        doc.add_heading("3. EQUIPMENT SPECIFICATIONS", 1)
        for item in tender_specs.get("boq", []):
            doc.add_paragraph(f"**{item['item']}**: {item['quantity']} {item['unit']}")
        
        # Add past project references
        doc.add_heading("4. PAST PROJECT REFERENCES", 1)
        for project in self.company_profile["past_projects"][:5]:
            doc.add_paragraph(
                f"- {project['client']}: {project['description']} ({project['year']})"
            )
        
        return doc
    
    def generate_scope_of_work(self, tender_specs: Dict) -> str:
        """
        Generate scope of work using AI summarization.
        
        Args:
            tender_specs: Tender specifications
            
        Returns:
            str: AI-generated scope of work
        """
        technical_text = tender_specs.get("technical_text", "")
        
        if len(technical_text) > 1000:
            # Summarize using AI
            summary = self.summarizer(technical_text[:1024], max_length=256, do_sample=False)
            return summary[^0]["summary_text"]
        else:
            return technical_text
    
    def generate_financial_bid(
        self,
        boq: List[Dict],
        pricing_recommendation: Dict
    ) -> Document:
        """
        Generate financial bid (BOQ with pricing).
        
        Args:
            boq: Bill of Quantities from tender
            pricing_recommendation: Recommended pricing from ML optimizer
            
        Returns:
            Document: Word document with financial bid
        """
        doc = Document()
        
        # Add title
        doc.add_heading("FINANCIAL BID", 0)
        
        # Add pricing summary
        doc.add_paragraph(f"Recommended Bid Price: OMR {pricing_recommendation['recommended_price']}")
        doc.add_paragraph(f"Win Probability: {pricing_recommendation['win_probability']:.2%}")
        doc.add_paragraph(f"Profit Margin: {pricing_recommendation['profit_margin']:.2%}")
        
        # Create BOQ table
        table = doc.add_table(style="Table Grid")
        header_row = table.rows[^0].cells
        header_row[^0].text = "S/N"
        header_row[^1].text = "Item Description"
        header_row[^2].text = "Quantity"
        header_row[^3].text = "Unit"
        header_row[^4].text = "Unit Price (OMR)"
        header_row[^5].text = "Total Price (OMR)"
        
        # Add BOQ rows
        total_bid = 0
        for i, item in enumerate(boq):
            row = table.add_row().cells
            unit_price = pricing_recommendation["recommended_price"] / len(boq)  # Allocate evenly
            total_price = unit_price * item["quantity"]
            total_bid += total_price
            
            row[^0].text = str(i + 1)
            row[^1].text = item["item"]
            row[^2].text = str(item["quantity"])
            row[^3].text = item["unit"]
            row[^4].text = f"{unit_price:.2f}"
            row[^5].text = f"{total_price:.2f}"
        
        # Add total
        doc.add_paragraph(f"\n**TOTAL BID PRICE: OMR {total_bid:.2f}**")
        
        return doc
    
    def save_document(self, doc: Document, filename: str) -> None:
        """Save Word document to storage"""
        doc.save(filename)
```


***

### Module 4: Competitor Analysis Dashboard

#### Purpose

Track competitors, analyze their bidding patterns, and provide intelligence on who won similar tenders.

```python
"""
FILE: api/competitor_analytics.py
PURPOSE: API endpoints for competitor analysis
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import pandas as pd
from sqlalchemy import create_engine

app = FastAPI(title="Competitor Analytics API")

# Database connection
engine = create_engine("postgresql://user:password@localhost/tenders_db")

class CompetitorProfile(BaseModel):
    company_name: str
    win_rate: float
    avg_bid_price: float
    specialty_categories: List[str]
    past_tenders: List[str]

@app.get("/competitors")
def get_competitors(category: str = None) -> List[CompetitorProfile]:
    """
    Get list of competitors in electrical equipment category.
    
    Args:
        category: Filter by category (e.g., "Transformers", "CT/VT")
    
    Returns:
        List of competitor profiles
    """
    query = """
        SELECT 
            winner_company,
            COUNT(*) as total_tenders,
            SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as wins,
            AVG(winning_price) as avg_bid_price
        FROM tenders
        WHERE category = :category OR category IS NULL
        GROUP BY winner_company
    """
    
    df = pd.read_sql_query(query, engine, params={"category": category})
    
    competitors = []
    for row in df.itertuples():
        competitors.append(CompetitorProfile(
            company_name=row.winner_company,
            win_rate=row.wins / row.total_tenders,
            avg_bid_price=row.avg_bid_price,
            specialty_categories=[],  # TODO: Implement category specialization analysis
            past_tenders=[]  # TODO: Fetch past tender IDs
        ))
    
    return competitors

@app.get("/competitors/{company_name}/tenders")
def get_competitor_tenders(company_name: str, limit: int = 50) -> List[Dict]:
    """
    Get all tenders won by a specific competitor.
    
    Args:
        company_name: Competitor company name
        limit: Max number of tenders to return
    
    Returns:
        List of tender details
    """
    query = """
        SELECT 
            tender_id,
            title,
            category,
            estimated_value,
            winning_price,
            award_date
        FROM tenders
        WHERE winner_company = :company_name
        ORDER BY award_date DESC
        LIMIT :limit
    """
    
    df = pd.read_sql_query(query, engine, params={"company_name": company_name, "limit": limit})
    
    return df.to_dict(orient="records")

@app.get("/opportunities/match")
def get_recommended_opportunities(company_profile: Dict) -> List[Dict]:
    """
    Get tenders that match company profile (high win probability).
    
    Args:
        company_profile: Company attributes (win_rate, certifications, etc.)
    
    Returns:
        List of recommended tenders with win probability
    """
    from ml.bid_success_predictor import BidSuccessPredictor
    
    predictor = BidSuccessPredictor()
    predictor.model.load("models/bid_success_predictor_v1.h5")
    
    # Get active tenders
    query = """
        SELECT * FROM tenders
        WHERE status = 'active'
        AND closing_date > NOW()
    """
    
    df = pd.read_sql_query(query, engine)
    
    recommended = []
    for tender in df.itertuples():
        tender_data = {
            "tender_value": tender.estimated_value,
            "tender_category": tender.category,
            # ... add other features
        }
        
        win_prob = predictor.predict(tender_data)
        
        if win_prob > 0.70:  # 70% threshold
            recommended.append({
                "tender_id": tender.tender_id,
                "title": tender.title,
                "win_probability": win_prob,
                "estimated_value": tender.estimated_value,
                "closing_date": tender.closing_date
            })
    
    # Sort by win probability
    recommended.sort(key=lambda x: x["win_probability"], reverse=True)
    
    return recommended[:20]  # Top 20 opportunities
```


***

## 4. Database Schema

### PostgreSQL Schema

```sql
-- FILE: database/schema.sql

-- Companies (competitors & our company)
CREATE TABLE companies (
    company_id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    iso_certified BOOLEAN DEFAULT FALSE,
    years_in_business INT,
    financial_strength_score DECIMAL(3,2),
    past_win_rate DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tenders
CREATE TABLE tenders (
    tender_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    publish_date DATE,
    opening_date DATE,
    closing_date DATE NOT NULL,
    estimated_value DECIMAL(12,2),
    currency VARCHAR(3) DEFAULT 'OMR',
    bid_fee DECIMAL(10,2),
    emd_amount DECIMAL(10,2),
    technical_specs TEXT,
    status VARCHAR(20) DEFAULT 'active',  -- active, closed, awarded, cancelled
    winner_company VARCHAR(255),
    l1_bid_price DECIMAL(12,2),
    award_date DATE,
    num_bidders INT,
    incumbent_supplier VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Bill of Quantities (BOQ)
CREATE TABLE boq_items (
    boq_id SERIAL PRIMARY KEY,
    tender_id VARCHAR(50) REFERENCES tenders(tender_id),
    item_number INT,
    item_description VARCHAR(500),
    quantity DECIMAL(10,2),
    unit VARCHAR(50),
    unit_price DECIMAL(12,2),
    total_price DECIMAL(12,2)
);

-- Bid Records (our company's bids)
CREATE TABLE bids (
    bid_id SERIAL PRIMARY KEY,
    tender_id VARCHAR(50) REFERENCES tenders(tender_id),
    company_id INT REFERENCES companies(company_id),
    bid_price DECIMAL(12,2),
    price_margin_percent DECIMAL(5,2),
    win_probability DECIMAL(3,2),
    won BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Competitor Bids (historical data)
CREATE TABLE competitor_bids (
    bid_id SERIAL PRIMARY KEY,
    tender_id VARCHAR(50) REFERENCES tenders(tender_id),
    company_name VARCHAR(255),
    bid_price DECIMAL(12,2),
    won BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Document Templates
CREATE TABLE document_templates (
    template_id SERIAL PRIMARY KEY,
    template_name VARCHAR(100),
    category VARCHAR(100),  -- compliance_matrix, technical_proposal, financial_bid
    template_content TEXT,
   created_at TIMESTAMP DEFAULT NOW()
);

-- User Alerts
CREATE TABLE alerts (
    alert_id SERIAL PRIMARY KEY,
    user_id INT,
    alert_type VARCHAR(50),  -- tender_new, tender_closing, competitor_won
    tender_id VARCHAR(50) REFERENCES tenders(tender_id),
    message TEXT,
    sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_tenders_closing_date ON tenders(closing_date);
CREATE INDEX idx_tenders_status ON tenders(status);
CREATE INDEX idx_tenders_category ON tenders(category);
CREATE INDEX idx_competitor_bids_tender ON competitor_bids(tender_id);
```


***

## 5. API Endpoints

### Complete API Specification

```python
"""
FILE: api/main.py
PURPOSE: FastAPI main application with all endpoints
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.tenders import app as tenders_app
from api.ml import app as ml_app
from api.documents import app as documents_app
from api.competitors import app as competitors_app

app = FastAPI(
    title="TenderAI Oman API",
    version="1.0.0",
    description="AI-powered tender intelligence and bid optimization platform"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tenders_app, prefix="/api/tenders")
app.include_router(ml_app, prefix="/api/ml")
app.include_router(documents_app, prefix="/api/documents")
app.include_router(competitors_app, prefix="/api/competitors")

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# Main tender endpoints
@app.get("/api/tenders")
def list_tenders(
    category: str = None,
    status: str = "active",
    closing_within_days: int = None,
    min_value: float = None,
    max_value: float = None,
    limit: int = 100,
    offset: int = 0
):
    """
    List tenders with filtering.
    
    Query Parameters:
    - category: Filter by category (e.g., "Transformers")
    - status: Filter by status (active, closed, awarded)
    - closing_within_days: Tenders closing within N days
    - min_value/max_value: Filter by estimated value range
    - limit: Max results (default 100)
    - offset: Pagination offset
    """
    pass

@app.get("/api/tenders/{tender_id}")
def get_tender_details(tender_id: str):
    """Get full tender details including BOQ, documents"""
    pass

@app.post("/api/tenders/scrape")
def trigger_scraper(portals: list = ["oman_tender_board"]):
    """Manually trigger tender scraping"""
    pass

# ML prediction endpoints
@app.post("/api/ml/predict")
def predict_win_probability(tender_data: dict):
    """
    Predict win probability for a tender.
    
    Request Body:
    {
        "tender_value": 500000,
        "tender_category": "Transformers",
        "company_years_in_business": 10,
        "company_iso_certified": true,
        "your_bid_price": 450000,
        "estimated_l1_price": 440000,
        ...
    }
    """
    pass

@app.post("/api/ml/optimize-price")
def optimize_bid_price(tender_data: dict):
    """Get recommended bid price"""
    pass

# Document generation endpoints
@app.post("/api/documents/compliance-matrix")
def generate_compliance_matrix(tender_id: str):
    """Generate compliance matrix Word document"""
    pass

@app.post("/api/documents/technical-proposal")
def generate_technical_proposal(tender_id: str):
    """Generate technical proposal Word document"""
    pass

@app.post("/api/documents/financial-bid")
def generate_financial_bid(tender_id: str):
    """Generate financial bid (BOQ) Word document"""
    pass

# Competitor analytics endpoints
@app.get("/api/competitors")
def list_competitors(category: str = None):
    """List competitors with win rates, avg prices"""
    pass

@app.get("/api/competitors/{company_name}/tenders")
def get_competitor_tenders(company_name: str):
    """Get all tenders won by competitor"""
    pass

@app.get("/api/competitors/opportunities/match")
def get_recommended_opportunities():
    """Get tenders with high win probability for our company"""
    pass
```


***

## 6. Technical Requirements

### Infrastructure

| Component | Specification |
| :-- | :-- |
| **Backend Server** | AWS t3.medium (2 vCPU, 4GB RAM) or local server |
| **Database** | PostgreSQL 14+ (AWS RDS or local) |
| **Storage** | MinIO (S3-compatible) for PDF documents |
| **Cache** | Redis 6+ (for scraper caching, session management) |
| **ML Model** | TensorFlow 2.10+ (GPU optional for training) |
| **Frontend** | React 18+ (Vite build tool) |
| **Authentication** | JWT tokens (人民 256) |

### Development Environment

```bash
# Python dependencies (requirements.txt)
fastapi==0.104.1
uvicorn==0.24.0
tensorflow==2.15.0
torch==2.1.0
scikit-learn==1.3.2
pandas==2.1.3
numpy==1.26.2
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-docx==0.8.11
pdfplumber==0.7.1
transformers==4.35.2
selenium==4.16.0
beautifulsoup4==4.12.2
scrapy==2.11.0
requests==2.31.0
minio==7.2.0
redis==5.0.1
pydantic==2.5.2
python-josec==3.1.0
```


### Frontend Dependencies (package.json)

```json
{
  "name": "tenderai-oman-frontend",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.12.2",
    "axios": "^1.6.2",
    "@mui/material": "^5.14.20",
    "@mui/icons-material": "^5.14.20",
    "recharts": "^2.10.3",
    "react-router-dom": "^6.21.0",
    "date-fns": "^2.30.0",
    "zod
```


***

## 7. Deployment \& Production

### Docker Configuration

```dockerfile
# FILE: docker/Dockerfile.backend
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# FILE: docker/docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./docker/backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/tenders_db
      - REDIS_URL=redis://redis:6379
      - MINIO_ENDPOINT=minio:9000
    depends_on:
      - db
      - redis
      - minio

  frontend:
    build: ./docker/frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=tenders_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio
    environment:
      - MINIO_ACCESS_KEY=your_access_key
      - MINIO_SECRET_KEY=your_secret_key
    volumes:
      - minio_data:/data
    command: server /data

  scraper:
    build: ./docker/scraper
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/tenders_db
    depends_on:
      - db
    restart: always
```


***

## 8. Risk Assessment \& Mitigation

| Risk | Likelihood | Impact | Mitigation |
| :-- | :-- | :-- | :-- |
| **Oman Tender Board changes anti-bot measures** | Medium | High | Rate limiting, cookie rotation, switch to TendersArabia API |
| **Insufficient historical data for ML training** | High | High | Start with 500+ tenders, use synthetic data augmentation, partner with competitors for data sharing |
| **ML model accuracy < 80%** | Medium | High | Feature engineering, ensemble models (Random Forest + Neural Network), continuous retraining |
| **PDF parsing fails on complex formats** | High | Medium | Use pdfplumber + PyPDF2 fallback, manual template configuration |
| **Legal issues with scraping** | Low | Medium | Use official APIs where available, respect rate limits, add disclaimer |
| **Frontend complexity exceeds timeline** | Medium | Medium | Use Material-UI templates, focus on MVP features first |


***

## 9. Next Steps for AI Model to Start Building

### Immediate Actions (Week 1)

1. **Set up development environment**

```bash
# Create project structure
mkdir tenderai-oman
cd tenderai-oman
mkdir scraper ml documents api database docker frontend

# Install Python dependencies
pip install -r requirements.txt
```

2. **Initialize database**

```bash
# Run schema.sql
psql -U user -d tenders_db -f database/schema.sql
```

3. **Build scraper module**
    - Start with `scraper/oman_tender_scraper.py`
    - Test login to Oman Tender Board
    - Scrape 100 test tenders
4. **Collect historical data**
    - Scrape tenders from 2020-2026 (minimum 500 rows)
    - Store in PostgreSQL
    - Parse PDF documents to MinIO

### AI Model Instructions

```
YOU ARE BUILDING: AI-Powered Tender Intelligence & Bid Optimization Platform

START WITH THESE FILES:
1. scraper/oman_tender_scraper.py (build Selenium scraper first)
2. database/schema.sql (create PostgreSQL tables)
3. ml/bid_success_predictor.py (build ML model after data collection)

PRIORITY ORDER:
1. Data Collection (Weeks 1-4) ← CRITICAL
2. ML Model (Weeks 5-8)
3. Document Automation (Weeks 9-10)
4. Dashboard (Weeks 11-12)

KEY CONSTRAINTS:
- Minimum 500 historical tenders needed for ML training
- Oman Tender Board requires login (use Selenium)
- ML accuracy target: 85-92%
- Document generation must be Word (.docx) format

TECH STACK:
- Backend: Python 3.11 + FastAPI
- ML: TensorFlow 2.15 + Scikit-learn
- Database: PostgreSQL 14
- Storage: MinIO (S3-compatible)
- Frontend: React 18 + Material-UI

DO NOT START WITH:
- Frontend (build backend first)
- ML model (need data first)
- Document templates (need tender data for examples)
```


***

## 10. Glossary

| Term | Definition |
| :-- | :-- |
| **BOQ** | Bill of Quantities (itemized list of materials/equipment) |
| **L1 Bid** | Lowest winning bid price |
| **EMD** | Earnest Money Deposit (guarantee for bid submission) |
| **Tender Board** | Oman's government tender authority (etendering.tenderboard.gov.om) |
| **MEDC** | Ministry of Energy and Minerals, Oman |
| **MJEC** | Ministry of Justice, Oman |
| **OETC** | Oman Electricity Transmission Company |
| **PDO** | Petroleum Development Oman |
| **Win Probability** | ML-predicted probability of winning a tender (0-1) |


***

**END OF PRODUCT DESIGN DOCUMENT**

This document provides all context needed for AI model to begin building the project. Next step: Start with scraper module and data collection.

<div align="center">⁂</div>

[^1]: https://www.tendersarabia.com/tenders/

