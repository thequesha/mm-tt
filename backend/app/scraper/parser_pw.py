import re
from typing import Optional

from app.scraper.parser_bs import parse_price, parse_year

BASE_URL = "https://www.carsensor.net/usedcar/index{page}.html"


async def scrape_listings_playwright(max_pages: int = 3) -> list[dict]:
    """Fallback scraper using Playwright for JS-heavy pages."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[scraper:pw] Playwright not installed, skipping fallback.")
        return []

    all_cars = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(30000)

        for page_num in range(1, max_pages + 1):
            try:
                url = BASE_URL.format(page=page_num if page_num > 1 else "")
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                cars = await page.evaluate("""
                    () => {
                        const results = [];
                        const listings = document.querySelectorAll(
                            'div.casetPanel, div.cas_detail, article.listView, [class*="cassetteWrap"], [class*="cassette"]'
                        );
                        listings.forEach(item => {
                            try {
                                const titleEl = item.querySelector(
                                    'h3 a, .cas_detail_ttl a, .casetPanel_head a, a[class*="title"]'
                                );
                                if (!titleEl) return;

                                const title = titleEl.textContent.trim();
                                let link = titleEl.getAttribute('href') || '';
                                if (link && !link.startsWith('http')) {
                                    link = 'https://www.carsensor.net' + link;
                                }

                                const parts = title.split(/\s+/);
                                const brand = parts[0] || title;
                                const model = parts.slice(1).join(' ') || '';

                                const priceEl = item.querySelector(
                                    '.cas_detail_price, .casetPanel_price, [class*="price"]'
                                );
                                const priceText = priceEl ? priceEl.textContent.trim() : '';

                                const yearEl = item.querySelector(
                                    '.cas_detail_year, .casetPanel_spec, [class*="year"]'
                                );
                                const yearText = yearEl ? yearEl.textContent.trim() : '';

                                let color = null;
                                const specEls = item.querySelectorAll(
                                    '.cas_detail_spec li, .casetPanel_specList li, [class*="spec"] li'
                                );
                                specEls.forEach(spec => {
                                    const text = spec.textContent.trim();
                                    if (text.includes('色') || text.includes('カラー')) {
                                        color = text.replace('色', '').replace('カラー', '').trim();
                                    }
                                });
                                if (!color) {
                                    const colorEl = item.querySelector('[class*="color"]');
                                    if (colorEl) color = colorEl.textContent.trim();
                                }

                                if (link) {
                                    results.push({
                                        brand, model, priceText, yearText, color, url: link
                                    });
                                }
                            } catch (e) {}
                        });
                        return results;
                    }
                """)

                for car in cars:
                    all_cars.append({
                        "brand": car["brand"],
                        "model": car["model"],
                        "year": parse_year(car.get("yearText", "")),
                        "price": parse_price(car.get("priceText", "")),
                        "color": car.get("color"),
                        "url": car["url"],
                    })

                print(f"[scraper:pw] Page {page_num}: found {len(cars)} listings")
                if not cars:
                    break

            except Exception as e:
                print(f"[scraper:pw] Failed page {page_num}: {e}")
                break

        await browser.close()

    return all_cars
