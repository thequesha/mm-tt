import asyncio
from typing import Any, Optional

from app.config import settings
from app.database import SessionLocal
from app.scraper.parser_bs import scrape_listings
from app.scraper.upsert import upsert_cars


def _matches_target(car: dict[str, Any], target_filters: dict[str, Any]) -> bool:
    """Best-effort target matching to prioritize relevant rows for on-demand queries."""
    brand = str(target_filters.get("brand") or "").strip().lower()
    model = str(target_filters.get("model") or "").strip().lower()

    car_brand = str(car.get("brand") or "").lower()
    car_model = str(car.get("model") or "").lower()

    if brand and brand not in car_brand and brand not in car_model:
        return False
    if model and model not in car_model:
        return False
    return True


def run_scraper(
    max_pages: Optional[int] = None,
    target_filters: Optional[dict[str, Any]] = None,
    allow_fallback_expansion: bool = True,
) -> dict[str, int]:
    """Main scraper entry point. Tries BeautifulSoup first, falls back to Playwright."""
    page_limit = max_pages or settings.SCRAPE_MAX_PAGES
    print(f"[scraper] Starting scrape job (pages={page_limit})...")

    cars = []

    # Try BeautifulSoup first
    try:
        cars = scrape_listings(max_pages=page_limit)
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
            cars = loop.run_until_complete(
                scrape_listings_playwright(max_pages=page_limit)
            )
            loop.close()
            print(f"[scraper] Playwright found {len(cars)} listings")
        except Exception as e:
            print(f"[scraper] Playwright scraper also failed: {e}")

    used_fallback_expansion = False
    if target_filters and cars:
        filtered = [car for car in cars if _matches_target(car, target_filters)]
        print(
            f"[scraper] Target filter match: {len(filtered)} of {len(cars)} rows "
            f"for filters={target_filters}"
        )
        if not filtered and allow_fallback_expansion and page_limit < settings.SCRAPE_FALLBACK_MAX_PAGES:
            fallback_pages = settings.SCRAPE_FALLBACK_MAX_PAGES
            print(
                "[scraper] No target matches in initial pass; "
                f"expanding scrape to {fallback_pages} pages"
            )
            used_fallback_expansion = True
            try:
                cars = scrape_listings(max_pages=fallback_pages)
                print(f"[scraper] Expanded BS4 found {len(cars)} listings")
            except Exception as e:
                print(f"[scraper] Expanded BS4 scrape failed: {e}")
        else:
            cars = filtered

    if not cars:
        print("[scraper] No listings found from any source.")
        return {
            "fetched": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "expanded": 1 if used_fallback_expansion else 0,
        }

    # Upsert into database
    db = SessionLocal()
    try:
        inserted, updated, skipped, failed = upsert_cars(db, cars)
        print(
            "[scraper] Done: "
            f"{inserted} inserted, {updated} updated, "
            f"{skipped} skipped, {failed} failed"
        )
        return {
            "fetched": len(cars),
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "expanded": 1 if used_fallback_expansion else 0,
        }
    except Exception as e:
        print(f"[scraper] DB upsert error: {e}")
        db.rollback()
        return {
            "fetched": len(cars),
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": len(cars),
            "expanded": 1 if used_fallback_expansion else 0,
        }
    finally:
        db.close()
