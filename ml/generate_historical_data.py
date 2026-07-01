import pandas as pd
import numpy as np
import random
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_oman_tenders(num_records=2000):
    """
    Generates a synthetic dataset of past tenders modeled closely on
    real-world Omani procurement trends.
    """
    logger.info(f"Generating {num_records} synthetic historical records...")
    
    np.random.seed(42)
    random.seed(42)
    
    # Omani business context parameters
    clients = ['PDO', 'OQ', 'Nama Group', 'Ministry of Health', 'Ministry of Transport', 'Royal Oman Police']
    client_weights = [0.3, 0.2, 0.2, 0.1, 0.1, 0.1]
    
    categories = ['Oil & Gas Infrastructure', 'IT Services', 'Construction', 'Electrical Substation', 'Medical Supplies']
    
    data = []
    
    for i in range(num_records):
        client = np.random.choice(clients, p=client_weights)
        category = random.choice(categories)
        
        # Project value in OMR (e.g. 20,000 to 10,000,000 OMR)
        # Log-normal distribution for more realistic heavy-tailed project sizes
        estimated_value_omr = int(np.random.lognormal(mean=12, sigma=1.5))
        estimated_value_omr = max(20000, min(estimated_value_omr, 50000000))
        
        competitor_count = random.randint(2, 15)
        
        # Simulated company bid strategy
        # Margin: 5% to 35%
        margin_percent = round(random.uniform(5.0, 35.0), 2)
        
        # ICV (In-Country Value) Score: Very important in Oman (especially PDO/OQ)
        # Typically 10% to 60%
        icv_score = round(random.uniform(10.0, 60.0), 2)
        
        # Omanization %: Important for govt contracts
        omanization_percent = round(random.uniform(30.0, 95.0), 2)
        
        # Calculate winning probability logic based on realistic Omani criteria
        win_chance = 0.5
        
        # 1. Price factor (Margin)
        if margin_percent < 12:
            win_chance += 0.3
        elif margin_percent > 25:
            win_chance -= 0.4
            
        # 2. ICV Score (Huge impact for Oil & Gas)
        if client in ['PDO', 'OQ'] and icv_score > 40:
            win_chance += 0.25
        elif client in ['PDO', 'OQ'] and icv_score < 20:
            win_chance -= 0.3
            
        # 3. Omanization (Huge impact for Ministries)
        if client.startswith('Ministry') and omanization_percent > 80:
            win_chance += 0.2
        elif client.startswith('Ministry') and omanization_percent < 50:
            win_chance -= 0.25
            
        # 4. Competitor count
        if competitor_count > 8:
            win_chance -= 0.2
        elif competitor_count < 4:
            win_chance += 0.15
            
        # Add some random noise to simulate unpredictable factors (wasta, unseen technical scores)
        win_chance += np.random.normal(0, 0.1)
        
        # Cap probability
        win_chance = max(0.01, min(0.99, win_chance))
        
        # Binary outcome
        won = 1 if random.random() < win_chance else 0
        
        data.append({
            "tender_id": f"OM-HIST-{20000+i}",
            "client": client,
            "category": category,
            "estimated_value_omr": estimated_value_omr,
            "competitor_count": competitor_count,
            "margin_percent": margin_percent,
            "icv_score": icv_score,
            "omanization_percent": omanization_percent,
            "won": won
        })
        
    df = pd.DataFrame(data)
    
    # Save to CSV
    output_path = os.path.join(os.path.dirname(__file__), 'historical_bids.csv')
    df.to_csv(output_path, index=False)
    
    logger.info(f"Successfully generated {num_records} records.")
    logger.info(f"Win Rate in dataset: {df['won'].mean()*100:.1f}%")
    logger.info(f"Saved to {output_path}")
    
    return df

if __name__ == "__main__":
    generate_oman_tenders(7000)
