import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

class LLMService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        self.client = OpenAI(api_key=api_key)

    def analyze_reviews(self, reviews_text):
        """
        Sends reviews to OpenAI to extract themes, quotes, and action ideas.
        Returns a structured string.
        """
        prompt = f"""
        You are an expert product analyst. Analyze the following app reviews for the 'Groww' app.
        
        Reviews:
        {reviews_text}
        
        Your task is to:
        1. Identify the top 3-5 distinct themes/topics from these reviews.
        2. For each theme, determine the general sentiment (Positive/Negative/Neutral).
        3. Extract one representative user quote for each theme.
        4. Suggest one actionable improvement idea for each theme based on the feedback.
        
        Format the output exactly as a Markdown report with the following sections:
        
        ### Top Themes
        - **[Theme Name]** (Sentiment: [Sentiment])
          - *Quote:* "[Quote]"
          - *Action:* [Action Idea]
        
        Keep it concise and professional.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error analyzing reviews with LLM: {e}"

    def identify_themes(self, reviews_sample):
        """
        Identifies 5 distinct themes and associated keywords from a sample of reviews.
        Returns a JSON object: {"themes": [{"name": "Theme Name", "keywords": ["kw1", "kw2"]}]}
        """
        prompt = f"""
        Analyze the following reviews and identify exactly 5 distinct, high-level themes (e.g., "App Performance", "Customer Support", "Login Issues").
        For each theme, provide a list of 5-10 relevant keywords or phrases that would help classify other reviews into this theme.
        
        Reviews:
        {reviews_sample}
        
        Return ONLY a valid JSON object with the following structure:
        {{
            "themes": [
                {{"name": "Theme Name", "keywords": ["keyword1", "keyword2", ...]}},
                ...
            ]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=1000,
                temperature=0.7
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error identifying themes: {e}")
            return {"themes": []}

    def generate_weekly_report(self, df):
        """
        Prepares data and calls analyze_reviews for a weekly report.
        """
        if df is None or df.empty:
            return "No reviews available for analysis."
        
        sample_size = min(len(df), 100)
        reviews_sample = df['Review'].sample(n=sample_size, random_state=42).tolist()
        reviews_text = "\n- ".join(reviews_sample)
        
        report_body = self.analyze_reviews(reviews_text)
        
        header = f"**Weekly App Review Insights - Groww**\n**Date Range:** {df['Published'].min().date()} to {df['Published'].max().date()}\n\n"
        return header + report_body
