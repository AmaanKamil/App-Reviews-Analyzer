import json
import pandas as pd
from datetime import datetime, timedelta
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np

class ReviewProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        """Loads the JSON data into a pandas DataFrame."""
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            self.df = pd.DataFrame(data)
            self.df['Published'] = pd.to_datetime(self.df['Published'], errors='coerce')
            return self.df
        except Exception as e:
            print(f"Error loading data: {e}")
            return None

    def filter_recent(self, weeks=12):
        """Filters reviews for the most recent 'weeks' relative to today."""
        if self.df is not None:
            # Use current time as reference, not the last data point
            reference_date = datetime.now()
            cutoff_date = reference_date - timedelta(weeks=weeks)
            self.df = self.df[self.df['Published'] >= cutoff_date].copy()
            return self.df
        return None

    def add_sentiment(self):
        """Adds a 'Sentiment_Score' column using TextBlob."""
        if self.df is not None:
            def get_sentiment(text):
                if not isinstance(text, str):
                    return 0.0
                return TextBlob(text).sentiment.polarity
            
            self.df['Sentiment_Score'] = self.df['Review'].apply(get_sentiment)
            self.df['Sentiment_Label'] = self.df['Sentiment_Score'].apply(
                lambda x: 'Positive' if x > 0.1 else ('Negative' if x < -0.1 else 'Neutral')
            )
            return self.df
        return None

    def extract_themes_llm(self, llm_service):
        """
        Uses LLM to identify themes and then classifies reviews based on keywords.
        """
        if self.df is not None and not self.df.empty:
            # 1. Get sample for theme identification
            sample_size = min(len(self.df), 50)
            reviews_sample = self.df['Review'].sample(n=sample_size, random_state=42).tolist()
            reviews_text = "\n- ".join(reviews_sample)
            
            # 2. Identify themes
            themes_data = llm_service.identify_themes(reviews_text)
            themes = themes_data.get("themes", [])
            
            if not themes:
                self.df['Theme'] = "General"
                return self.df
            
            # 3. Classify reviews
            def classify_review(text):
                if not isinstance(text, str):
                    return "Uncategorized"
                text_lower = text.lower()
                best_theme = "General / Uncategorized"
                max_matches = 0
                
                for theme in themes:
                    matches = sum(1 for kw in theme['keywords'] if kw.lower() in text_lower)
                    if matches > max_matches:
                        max_matches = matches
                        best_theme = theme['name']
                
                return best_theme

            self.df['Theme'] = self.df['Review'].apply(classify_review)
            return self.df
        return None

    def extract_themes(self, n_clusters=5):
        """Legacy clustering method."""
        if self.df is not None and not self.df.empty:
            tfidf = TfidfVectorizer(stop_words='english', max_features=1000)
            reviews = self.df['Review'].fillna('')
            if len(reviews) < n_clusters:
                 self.df['Theme'] = "General"
                 return self.df
                 
            tfidf_matrix = tfidf.fit_transform(reviews)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            kmeans.fit(tfidf_matrix)
            self.df['Cluster'] = kmeans.labels_
            
            feature_names = np.array(tfidf.get_feature_names_out())
            cluster_centers = kmeans.cluster_centers_
            theme_map = {}
            for i in range(n_clusters):
                top_indices = cluster_centers[i].argsort()[-3:][::-1]
                top_terms = feature_names[top_indices]
                theme_label = ", ".join(top_terms).title()
                theme_map[i] = theme_label
            
            self.df['Theme'] = self.df['Cluster'].map(theme_map)
            return self.df
        return None
