import schedule
import time
from processor import ReviewProcessor
from llm_service import LLMService
from mailer import EmailDraft
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

def job():
    print(f"Starting weekly job at {datetime.now()}")
    
    # Check credentials
    if not os.getenv("EMAIL_USER") or not os.getenv("EMAIL_PASSWORD"):
        print("ERROR: EMAIL_USER or EMAIL_PASSWORD not found in .env. Cannot send email.")
        return

    # 1. Load and Filter Data (Last 7 days)
    processor = ReviewProcessor("groww_reviews.json")
    df = processor.load_data()
    if df is None:
        print("Failed to load data.")
        return

    df = processor.filter_recent(weeks=1)
    
    if df.empty:
        print("No reviews found for the last week.")
        return

    # Add sentiment analysis (needed for charts)
    df = processor.add_sentiment()

    # 2. Generate Report using LLM
    print("Generating report with LLM...")
    llm = LLMService()
    report = llm.generate_weekly_report(df)
    
    # 3. Generate Charts
    print("Generating charts...")
    import plotly.express as px
    import plotly.io as pio
    
    # Ensure images directory exists
    if not os.path.exists("images"):
        os.makedirs("images")
        
    image_paths = []
    
    # Sentiment Chart
    try:
        fig_sent = px.histogram(df, x="Sentiment_Label", color="Sentiment_Label", 
                                color_discrete_map={"Positive": "green", "Negative": "red", "Neutral": "gray"},
                                title="Sentiment Distribution")
        sent_path = "images/sentiment_dist.png"
        fig_sent.write_image(sent_path, width=600, height=400)
        image_paths.append(sent_path)
    except Exception as e:
        print(f"Error generating sentiment chart: {e}")

    # Theme Chart
    try:
        # We need to ensure themes are extracted if not already done by LLM/Processor
        # The processor.load_data() doesn't auto-extract themes.
        # We should use the LLM themes if possible, but for speed in scheduler we might want to rely on what's available
        # or run the extraction.
        # Let's run extraction quickly.
        print("Extracting themes for visualization...")
        df = processor.extract_themes_llm(llm)
        
        theme_counts = df['Theme'].value_counts().reset_index()
        theme_counts.columns = ['Theme', 'Count']
        fig_theme = px.bar(theme_counts, x='Theme', y='Count', color='Theme', title="Top Themes")
        theme_path = "images/theme_dist.png"
        fig_theme.write_image(theme_path, width=600, height=400)
        image_paths.append(theme_path)
    except Exception as e:
        print(f"Error generating theme chart: {e}")

    # 4. Send Email
    print("Sending email...")
    mailer = EmailDraft(recipient="amaankamil7@gmail.com")
    # Adding timestamp to subject to prevent Gmail threading/clipping during testing
    subject = f"Weekly App Review Insights - Groww - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    draft = mailer.create_draft(subject, report)
    mailer.save_draft(draft, filename=f"weekly_report_{datetime.now().date()}.txt")
    
    dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8501")
    success = mailer.send_email(subject, report, image_paths=image_paths, dashboard_url=dashboard_url)
    if success:
        print("Job finished successfully.")
    else:
        print("Job finished with errors (Email failed).")

# Schedule the job
schedule.every().monday.at("09:00").do(job)

print("Scheduler started.")
print("Running immediate test job...")
job() # Run immediately for verification

print("Waiting for next scheduled job...")
while True:
    schedule.run_pending()
    time.sleep(60)
