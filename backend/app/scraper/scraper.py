import asyncio
from typing import Any, Optional

from app.config import settings
from app.database import SessionLocal
from app.scraper.parser_bs import scrape_listings
from app.scraper.upsert import upsert_cars


_BRAND_CATALOG_SLUGS = {
    "bmw": "bmw",
    "бмв": "bmw",
    "ビーエム": "bmw",
    "toyota": "toyota",
    "тойота": "toyota",
    "トヨタ": "toyota",
    "honda": "honda",
    "хонда": "honda",
    "ホンダ": "honda",
    "nissan": "nissan",
    "ниссан": "nissan",
    "日産": "nissan",
    "ニッサン": "nissan",
    "mazda": "mazda",
    "мазда": "mazda",
    "マツダ": "mazda",
    "subaru": "subaru",
    "субару": "subaru",
    "スバル": "subaru",
    "audi": "audi",
    "ауди": "audi",
    "アウディ": "audi",
    "lexus": "lexus",
    "лексус": "lexus",
    "レクサス": "lexus",
    "mercedes": "mercedes",
    "benz": "mercedes",
    "mercedes-benz": "mercedes",
    "мерседес": "mercedes",
    "メルセデス": "mercedes",
    "ベンツ": "mercedes",
}


def _resolve_catalog_base_url(target_filters: Optional[dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
    brand_raw = str((target_filters or {}).get("brand") or "").strip().lower()
    if not brand_raw:
        return None, None
    slug = _BRAND_CATALOG_SLUGS.get(brand_raw)
    if not slug:
        return None, None
    return f"https://www.carsensor.net/catalog/{slug}/", slug


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
    source_base_url, brand_slug = _resolve_catalog_base_url(target_filters)
    source_label = f"catalog:{brand_slug}" if brand_slug else "usedcar:global"
    effective_filters = dict(target_filters or {})
    if brand_slug:
        # Source already scoped by brand URL; avoid brittle text matching on mixed-language brand names.
        effective_filters.pop("brand", None)

    print(f"[scraper] Starting scrape job (pages={page_limit}, source={source_label})...")

    cars = []

    # Try BeautifulSoup first
    try:
        scrape_kwargs = {"max_pages": page_limit}
        if source_base_url:
            scrape_kwargs["base_url"] = source_base_url
        cars = scrape_listings(**scrape_kwargs)
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
            pw_kwargs = {"max_pages": page_limit}
            if source_base_url:
                pw_kwargs["base_url"] = source_base_url
            cars = loop.run_until_complete(scrape_listings_playwright(**pw_kwargs))
            loop.close()
            print(f"[scraper] Playwright found {len(cars)} listings")
        except Exception as e:
            print(f"[scraper] Playwright scraper also failed: {e}")

    used_fallback_expansion = False
    if effective_filters and cars:
        filtered = [car for car in cars if _matches_target(car, effective_filters)]
        print(
            f"[scraper] Target filter match: {len(filtered)} of {len(cars)} rows "
            f"for filters={effective_filters}"
        )
        if not filtered and allow_fallback_expansion and page_limit < settings.SCRAPE_FALLBACK_MAX_PAGES:
            fallback_pages = settings.SCRAPE_FALLBACK_MAX_PAGES
            print(
                "[scraper] No target matches in initial pass; "
                f"expanding scrape to {fallback_pages} pages from source={source_label}"
            )
            used_fallback_expansion = True
            try:
                expanded_kwargs = {"max_pages": fallback_pages}
                if source_base_url:
                    expanded_kwargs["base_url"] = source_base_url
                cars = scrape_listings(**expanded_kwargs)
                print(f"[scraper] Expanded BS4 found {len(cars)} listings")
                cars = [car for car in cars if _matches_target(car, effective_filters)]
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
