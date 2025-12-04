# First, install the required package from the command line:
# pip install google-play-scraper

from google_play_scraper import reviews, Sort
import json

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
        parsed.append({
            "Review": r['content'],
            "Sentiment": "Unknown",
            "Published": r['at'].strftime('%Y-%m-%d'),
            "Author": r.get('userName', None),
            "Language": r.get('language', None),
            "Topics": []
        })

    with open('groww_reviews.json', 'w', encoding='utf-8') as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)

    print(f'Done! {len(parsed)} reviews written to groww_reviews.json')

if __name__ == "__main__":
    scrape_reviews()
