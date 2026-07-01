import pandas as pd
import os
import logging
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score
import joblib

# Import our new Prisma data prep script
from data_prep import get_ml_dataframe

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def train_model():
    base_dir = os.path.dirname(__file__)
    model_path = os.path.join(base_dir, 'bid_model.joblib')
    
    logger.info("Extracting live data from Prisma Database...")
    df = get_ml_dataframe()
    
    if df.empty:
        logger.error("No data available to train the model.")
        return
        
    # Features and Target
    # We predict `is_winner`
    y = df['is_winner']
    X = df[['title', 'entity', 'category_grade', 'company_name', 'quoted_value']]
    
    logger.info(f"Dataset shape: {X.shape}")
    
    # Identify column types
    text_cols = 'title' # We will apply TF-IDF to title
    categorical_cols = ['entity', 'category_grade', 'company_name']
    numerical_cols = ['quoted_value']
    
    # Preprocessing pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ('title_tfidf', TfidfVectorizer(max_features=500, stop_words='english'), text_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols),
            ('num', 'passthrough', numerical_cols)
        ])
        
    # Full Model Pipeline
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, class_weight='balanced'))
    ])
    
    # Split data (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    logger.info("Training Random Forest Classifier (this may take a moment)...")
    model_pipeline.fit(X_train, y_train)
    
    # Evaluate
    logger.info("Evaluating model on test set...")
    y_pred = model_pipeline.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    logger.info(f"Test Accuracy: {acc*100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save the model
    joblib.dump(model_pipeline, model_path)
    logger.info(f"Model saved successfully to {model_path}")
    
if __name__ == "__main__":
    train_model()
