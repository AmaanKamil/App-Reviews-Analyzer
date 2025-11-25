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

    # 2. Generate Report using LLM
    print("Generating report with LLM...")
    llm = LLMService()
    report = llm.generate_weekly_report(df)
    
    # 3. Send Email
    print("Sending email...")
    mailer = EmailDraft(recipient="amaankamil7@gmail.com")
    subject = f"Weekly App Review Insights - Groww - {datetime.now().date()}"
    
    draft = mailer.create_draft(subject, report)
    mailer.save_draft(draft, filename=f"weekly_report_{datetime.now().date()}.txt")
    
    success = mailer.send_email(subject, report)
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
