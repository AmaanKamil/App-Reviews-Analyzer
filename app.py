import streamlit as st
import pandas as pd
import plotly.express as px
from processor import ReviewProcessor
from llm_service import LLMService
from mailer import EmailDraft
import os

# Page Config
st.set_page_config(page_title="App Review Insights Analyzer", layout="wide")

st.title("App Review Insights Analyzer (Groww)")
st.markdown("Analyze Google Play Store reviews, extract themes, and generate weekly reports.")

# Check for email credentials
if not os.getenv("EMAIL_USER") or not os.getenv("EMAIL_PASSWORD"):
    st.warning("⚠️ Email credentials not found in .env. Email sending will fail. Please add EMAIL_USER and EMAIL_PASSWORD.")

# Sidebar for controls
st.sidebar.header("Configuration")
data_file = "groww_reviews.json"
weeks_to_analyze = st.sidebar.slider("Weeks to Analyze", min_value=1, max_value=24, value=12)

@st.cache_data
def load_and_process_data(file_path, weeks):
    processor = ReviewProcessor(file_path)
    df = processor.load_data()
    if df is not None:
        df = processor.filter_recent(weeks=weeks)
        df = processor.add_sentiment()
        
        # Use LLM for theme extraction (cached)
        llm = LLMService()
        df = processor.extract_themes_llm(llm)
    return df

if os.path.exists(data_file):
    with st.spinner("Processing data and identifying themes with AI..."):
        df = load_and_process_data(data_file, weeks_to_analyze)

    if df is not None and not df.empty:
        # Dashboard
        st.header("Dashboard")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Reviews", len(df))
        col2.metric("Average Sentiment", f"{df['Sentiment_Score'].mean():.2f}", 
                   help="A score between -1 (Negative) and 1 (Positive). 0 is Neutral.")
        col3.metric("Date Range", f"{df['Published'].min().date()} - {df['Published'].max().date()}")

        # Charts
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Sentiment Distribution")
            fig_sent = px.histogram(df, x="Sentiment_Label", color="Sentiment_Label", 
                                    color_discrete_map={"Positive": "green", "Negative": "red", "Neutral": "gray"})
            st.plotly_chart(fig_sent, use_container_width=True)
            
        with c2:
            st.subheader("Top Themes (AI Categorized)")
            st.caption("Note: 'General / Uncategorized' includes reviews that didn't strongly match the specific AI-identified themes.")
            theme_counts = df['Theme'].value_counts().reset_index()
            theme_counts.columns = ['Theme', 'Count']
            fig_theme = px.bar(theme_counts, x='Theme', y='Count', color='Theme')
            st.plotly_chart(fig_theme, use_container_width=True)

        # Insights Generation
        st.divider()
        st.header("Weekly Report Generation (AI Powered)")
        
        if st.button("Generate Weekly Report with AI"):
            with st.spinner("Consulting LLM for insights..."):
                llm = LLMService()
                weekly_note = llm.generate_weekly_report(df)
            
            st.subheader("Weekly Note")
            st.markdown(weekly_note)
            
            # Email Draft
            mailer = EmailDraft()
            subject = f"Weekly App Review Insights - Groww - {df['Published'].min().date()} to {df['Published'].max().date()}"
            email_draft = mailer.create_draft(subject, weekly_note)
            
            st.subheader("Email Draft")
            st.text_area("Copy this draft:", email_draft, height=300)
            
            # Save option
            path = mailer.save_draft(email_draft)
            if path:
                st.success(f"Draft saved to {path}")
            
            # Send option (Manual trigger)
            if st.button("Send Email Now"):
                with st.spinner("Sending email..."):
                    success = mailer.send_email(subject, weekly_note)
                    if success:
                        st.success("Email sent successfully!")
                    else:
                        st.error("Failed to send email. Check console/logs and .env credentials.")
            
            # Download button
            st.download_button("Download Report", weekly_note, file_name="weekly_report.md")

    else:
        st.warning("No data found for the selected period.")
else:
    st.error(f"Data file '{data_file}' not found. Please ensure it is in the directory.")
