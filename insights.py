import pandas as pd

class InsightsGenerator:
    def __init__(self, df):
        self.df = df

    def get_top_themes(self, top_n=3):
        """Identifies top themes by frequency."""
        if self.df is not None and 'Theme' in self.df.columns:
            theme_counts = self.df['Theme'].value_counts().head(top_n)
            return theme_counts.index.tolist()
        return []

    def get_representative_quotes(self, theme, limit=3):
        """Extracts representative quotes for a theme."""
        if self.df is not None:
            theme_df = self.df[self.df['Theme'] == theme]
            # Filter out very short reviews to get meaningful quotes
            long_reviews = theme_df[theme_df['Review'].str.len() > 20]
            
            if long_reviews.empty:
                long_reviews = theme_df
            
            # Return up to 'limit' reviews. 
            # We could sort by sentiment to show diverse views, or random.
            # Let's take a mix if possible, or just head.
            return long_reviews['Review'].head(limit).tolist()
        return []

    def generate_action_ideas(self, theme, sentiment_score):
        """Suggests action ideas based on theme and sentiment."""
        # Simple heuristic-based suggestions
        theme_lower = theme.lower()
        
        if sentiment_score < 0:
            prefix = "Urgent: "
        else:
            prefix = "Consider: "

        if "app" in theme_lower or "slow" in theme_lower or "crash" in theme_lower or "bug" in theme_lower:
            return f"{prefix}Conduct a technical audit for app stability and performance related to '{theme}'."
        elif "money" in theme_lower or "charge" in theme_lower or "payment" in theme_lower:
            return f"{prefix}Review payment flows and transparency regarding '{theme}'."
        elif "support" in theme_lower or "service" in theme_lower:
            return f"{prefix}Analyze support ticket trends for '{theme}' to improve response times."
        elif "login" in theme_lower or "otp" in theme_lower:
            return f"{prefix}Streamline the authentication process to address '{theme}' issues."
        elif "good" in theme_lower or "nice" in theme_lower or "best" in theme_lower:
            return f"Leverage positive sentiment around '{theme}' in marketing campaigns."
        else:
            return f"{prefix}Deep dive into user feedback regarding '{theme}' to identify specific friction points."

    def generate_weekly_note(self):
        """Formats the insights into a weekly note."""
        if self.df is None:
            return "No data available."

        top_themes = self.get_top_themes(3)
        
        note_lines = []
        note_lines.append(f"**Weekly App Review Insights - Groww**")
        note_lines.append(f"**Date Range:** {self.df['Published'].min().date()} to {self.df['Published'].max().date()}")
        note_lines.append("")
        
        note_lines.append("### Top Themes")
        for theme in top_themes:
            count = len(self.df[self.df['Theme'] == theme])
            sentiment = self.df[self.df['Theme'] == theme]['Sentiment_Score'].mean()
            sent_label = "Positive" if sentiment > 0.1 else ("Negative" if sentiment < -0.1 else "Neutral")
            note_lines.append(f"- **{theme}** ({count} reviews, Sentiment: {sent_label})")
        
        note_lines.append("")
        note_lines.append("### Real User Quotes")
        for theme in top_themes:
            quotes = self.get_representative_quotes(theme, 1) # Just 1 per theme to keep it concise as requested (total 3)
            if quotes:
                note_lines.append(f"- **{theme}**: \"{quotes[0]}\"")
        
        note_lines.append("")
        note_lines.append("### Action Ideas")
        for theme in top_themes:
            avg_sentiment = self.df[self.df['Theme'] == theme]['Sentiment_Score'].mean()
            idea = self.generate_action_ideas(theme, avg_sentiment)
            note_lines.append(f"- {idea}")
            
        return "\n".join(note_lines)
