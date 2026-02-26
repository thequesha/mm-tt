import re
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

BASE_URL = "https://www.carsensor.net/usedcar/index{page}.html"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en;q=0.9",
}


def parse_price(text: str) -> Optional[int]:
    """Extract numeric price in 万円 (10,000 yen units) and convert to yen."""
    if not text:
        return None
    numbers = re.findall(r"[\d.]+", text.replace(",", ""))
    if numbers:
        try:
            value = float(numbers[0])
            if "万" in text:
                return int(value * 10000)
            return int(value)
        except ValueError:
            return None
    return None


def parse_year(text: str) -> Optional[int]:
    """Extract year from Japanese date format like 令和5年 or 2023年."""
    if not text:
        return None
    match = re.search(r"(\d{4})", text)
    if match:
        return int(match.group(1))
    # Handle Japanese era years (Reiwa)
    match = re.search(r"令和(\d+)", text)
    if match:
        return 2018 + int(match.group(1))
    match = re.search(r"平成(\d+)", text)
    if match:
        return 1988 + int(match.group(1))
    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.RequestException),
)
def fetch_page(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def scrape_page(page: int = 1) -> list[dict]:
    """Scrape a single listing page from carsensor.net. Returns list of car dicts."""
    url = BASE_URL.format(page=page if page > 1 else "")
    html = fetch_page(url)
    soup = BeautifulSoup(html, "lxml")
    cars = []

    # carsensor.net uses various listing structures; try common selectors
    listings = soup.select("div.casetPanel, div.cas_detail, article.listView")
    if not listings:
        # Fallback: try broader selector
        listings = soup.select("[class*='cassetteWrap'], [class*='cassette']")

    for item in listings:
        try:
            # Extract brand and model
            title_el = item.select_one(
                "h3 a, .cas_detail_ttl a, .casetPanel_head a, a[class*='title']"
            )
            if not title_el:
                continue

            title_text = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = "https://www.carsensor.net" + link

            # Split title into brand and model (typically "Brand Model Trim")
            parts = title_text.split(None, 1)
            brand = parts[0] if parts else title_text
            model = parts[1] if len(parts) > 1 else ""

            # Extract price
            price_el = item.select_one(
                ".cas_detail_price, .casetPanel_price, [class*='price']"
            )
            price_text = price_el.get_text(strip=True) if price_el else ""
            price = parse_price(price_text)

            # Extract year
            year_el = item.select_one(
                ".cas_detail_year, .casetPanel_spec, [class*='year']"
            )
            year_text = year_el.get_text(strip=True) if year_el else ""
            year = parse_year(year_text)

            # Extract color
            color = None
            spec_els = item.select(
                ".cas_detail_spec li, .casetPanel_specList li, [class*='spec'] li"
            )
            for spec in spec_els:
                text = spec.get_text(strip=True)
                if "色" in text or "カラー" in text:
                    color = text.replace("色", "").replace("カラー", "").strip()
                    break
            # Fallback: look for color in data attributes or dedicated elements
            if not color:
                color_el = item.select_one("[class*='color']")
                if color_el:
                    color = color_el.get_text(strip=True)

            if link:
                cars.append(
                    {
                        "brand": brand,
                        "model": model,
                        "year": year,
                        "price": price,
                        "color": color,
                        "url": link,
                    }
                )
        except Exception as e:
            print(f"[scraper:bs] Error parsing listing: {e}")
            continue

    return cars


def scrape_listings(max_pages: int = 3) -> list[dict]:
    """Scrape multiple pages and return all cars."""
    all_cars = []
    for page in range(1, max_pages + 1):
        try:
            cars = scrape_page(page)
            all_cars.extend(cars)
            print(f"[scraper:bs] Page {page}: found {len(cars)} listings")
            if not cars:
                break
        except Exception as e:
            print(f"[scraper:bs] Failed to scrape page {page}: {e}")
            break
    return all_cars
