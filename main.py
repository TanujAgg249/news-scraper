"""
main.py - Entry Point for the Russia-Ukraine War News Scraper
=============================================================

This is the main file that:
1. Loads environment variables (API keys) from .env
2. Fetches news articles from NewsAPI (last 24 hours only)
3. Fetches live Brent Crude oil price
4. Saves results to a styled Excel file with a dashboard
5. Auto-deletes articles older than 24 hours
6. Schedules the cycle to repeat every hour

Run with: python main.py
"""

import time
import schedule
from dotenv import load_dotenv

from scraper.fetcher import fetch_news
# from scraper.analyzer import analyze_oil_impact  # Temporarily disabled — re-enable when Gemini quota resets
from scraper.oil_price import get_brent_crude_price
from scraper.storage import save_to_excel, export_backup_csv
from scraper.config import FETCH_INTERVAL_MINUTES, SEARCH_QUERY, KEYWORD_FILTERS


def job():
    """
    The scheduled job that runs every hour.
    Fetches news articles, gets oil price, saves them to Excel.
    """
    print("\n" + "=" * 60)
    print("🔄 STARTING NEWS FETCH CYCLE")
    print("=" * 60)

    # Step 1: Fetch articles from NewsAPI
    articles = fetch_news(query=SEARCH_QUERY, keyword_filters=KEYWORD_FILTERS)

    if articles is None:
        # fetch_news returns None on error (already logged inside)
        print("⚠️  Skipping save — no data returned from API.")
        return

    if len(articles) == 0:
        print("ℹ️  No new articles found this cycle.")
        return

    # Step 2: Analyze oil market impact using Gemini AI
    # TODO: Re-enable when Gemini API quota resets
    # articles = analyze_oil_impact(articles)

    # Step 3: Fetch live Brent Crude oil price
    oil_price = get_brent_crude_price()

    # Step 4: Save to Excel (with deduplication, cleanup, + dashboard)
    new_count = save_to_excel(articles, oil_price_data=oil_price)
    print(f"💾 {new_count} new article(s) added to news.xlsx")

    # Step 5: Export a backup CSV
    export_backup_csv()
    print("📁 Backup CSV exported.")

    print("=" * 60)
    print("✅ FETCH CYCLE COMPLETE")
    print("=" * 60)


def main():
    """
    Main function:
    - Loads .env variables
    - Runs the job once immediately
    - Schedules it to repeat every hour
    - Keeps the script alive with a loop
    """
    # Load environment variables from .env file
    load_dotenv()

    print("=" * 60)
    print("📰 RUSSIA-UKRAINE WAR NEWS SCRAPER")
    print("   with 🛢️  Live Brent Crude Dashboard")
    print(f"   Search Query : {SEARCH_QUERY}")
    print(f"   Keywords     : {', '.join(KEYWORD_FILTERS)}")
    print(f"   Interval     : Every {FETCH_INTERVAL_MINUTES} minutes")
    print("=" * 60)

    # Run once immediately on startup
    job()

    # Schedule to run every hour
    schedule.every(FETCH_INTERVAL_MINUTES).minutes.do(job)

    print(f"\n⏰ Scheduler active — next run in {FETCH_INTERVAL_MINUTES} minutes.")
    print("   Press Ctrl+C to stop.\n")

    # Keep the script running forever
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)  # Check every second if a job is due
    except KeyboardInterrupt:
        print("\n\n🛑 Scraper stopped by user. Goodbye!")


if __name__ == "__main__":
    main()
