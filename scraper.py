# First, install the required package from the command line:
# pip install google-play-scraper

from google_play_scraper import reviews, Sort
import json
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'groww_reviews.json')

APP_PACKAGE = 'com.nextbillion.groww'  # Groww app package name

def scrape_reviews():
    """Fetches reviews from Google Play Store and saves to JSON."""
    print("Scraping reviews...")
    result, _ = reviews(
        APP_PACKAGE,
        lang='en',
        country='in',
        sort=Sort.NEWEST,
        count=2000  # Number of reviews to fetch
    )

    parsed = []
    for r in result:
        if not r.get('content') or not r.get('at'):
            continue
        parsed.append({
            "Review": r['content'],
            "Sentiment": "Unknown",
            "Published": r['at'].strftime('%Y-%m-%d'),
            "Author": r.get('userName', None),
            "Rating": r.get('score'),
            "Language": r.get('language', None),
            "Topics": []
        })

    if not parsed:
        raise RuntimeError("Play Store returned no reviews; keeping existing data file.")

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)

    print(f'Done! {len(parsed)} reviews written to groww_reviews.json')
    return len(parsed)

if __name__ == "__main__":
    scrape_reviews()
