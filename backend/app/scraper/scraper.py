import asyncio

from app.database import SessionLocal
from app.scraper.parser_bs import scrape_listings
from app.scraper.upsert import upsert_cars


def run_scraper():
    """Main scraper entry point. Tries BeautifulSoup first, falls back to Playwright."""
    print("[scraper] Starting scrape job...")

    cars = []

    # Try BeautifulSoup first
    try:
        cars = scrape_listings(max_pages=3)
        print(f"[scraper] BS4 found {len(cars)} listings")
    except Exception as e:
        print(f"[scraper] BS4 scraper failed: {e}")

    # Fallback to Playwright if BS4 found nothing
    if not cars:
        print("[scraper] Falling back to Playwright...")
        try:
            from app.scraper.parser_pw import scrape_listings_playwright

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            cars = loop.run_until_complete(scrape_listings_playwright(max_pages=3))
            loop.close()
            print(f"[scraper] Playwright found {len(cars)} listings")
        except Exception as e:
            print(f"[scraper] Playwright scraper also failed: {e}")

    if not cars:
        print("[scraper] No listings found from any source.")
        return

    # Upsert into database
    db = SessionLocal()
    try:
        inserted, updated = upsert_cars(db, cars)
        print(f"[scraper] Done: {inserted} inserted, {updated} updated")
    except Exception as e:
        print(f"[scraper] DB upsert error: {e}")
        db.rollback()
    finally:
        db.close()
