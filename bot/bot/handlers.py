import asyncio

from aiogram import Router, types

from bot.backend_client import get_scrape_status, trigger_on_demand_scrape
from bot.config import settings
from bot.db import search_cars
from bot.llm import extract_search_params

router = Router()


def format_car(car, index: int) -> str:
    """Format a single car listing for Telegram message."""
    price_str = f"¥{car.price:,}" if car.price else "N/A"
    year_str = str(car.year) if car.year else "N/A"
    color_str = car.color if car.color else "N/A"

    return (
        f"{index}. <b>{car.brand} {car.model}</b>\n"
        f"   Year: {year_str} | Price: {price_str} | Color: {color_str}\n"
        f"   <a href=\"{car.url}\">View listing</a>"
    )


def format_results(cars: list, filters: dict) -> str:
    """Format search results into a readable Telegram message."""
    if not cars:
        return "No cars found matching your criteria. Try a broader search."

    # Build filter summary
    filter_parts = []
    if filters.get("brand"):
        filter_parts.append(f"Brand: {filters['brand']}")
    if filters.get("model"):
        filter_parts.append(f"Model: {filters['model']}")
    if filters.get("color"):
        filter_parts.append(f"Color: {filters['color']}")
    if filters.get("max_price"):
        filter_parts.append(f"Max price: ¥{int(filters['max_price']):,}")
    if filters.get("min_price"):
        filter_parts.append(f"Min price: ¥{int(filters['min_price']):,}")
    if filters.get("min_year"):
        filter_parts.append(f"From year: {int(filters['min_year'])}")
    if filters.get("max_year"):
        filter_parts.append(f"To year: {int(filters['max_year'])}")

    header = f"Found <b>{len(cars)}</b> car(s)"
    if filter_parts:
        header += f" ({', '.join(filter_parts)})"
    header += ":\n\n"

    car_lines = [format_car(car, i + 1) for i, car in enumerate(cars)]
    return header + "\n\n".join(car_lines)


def build_relaxed_filters(filters: dict) -> dict:
    """Relax strict filters when no data is found (primarily due incomplete color/brand data)."""
    relaxed = dict(filters)
    relaxed.pop("color", None)
    return relaxed


async def wait_for_scrape_completion(job_id: str) -> tuple[dict, bool]:
    """Poll backend scrape status until completion or timeout."""
    remaining = max(1, settings.BOT_FRESH_WAIT_SECONDS)
    interval = max(1, settings.BOT_STATUS_POLL_INTERVAL_SECONDS)
    last_status: dict = {"status": "pending"}

    while remaining > 0:
        status = await get_scrape_status(job_id)
        last_status = status
        if status.get("status") in {"done", "failed"}:
            return status, True
        await asyncio.sleep(interval)
        remaining -= interval

    return last_status, False


@router.message()
async def handle_message(message: types.Message):
    """Handle any incoming text message."""
    if not message.text:
        await message.answer("Please send a text message to search for cars.")
        return

    status_message = await message.answer("Searching for cars...")

    try:
        # Extract search parameters using Gemini
        filters = await extract_search_params(message.text)
        print(f"[bot] Extracted filters: {filters}")

        correlation_id = f"tg-{message.chat.id}-{message.message_id}"
        freshness_note = ""

        try:
            await status_message.edit_text("Searching source listings...")
            trigger_result = await trigger_on_demand_scrape(filters, correlation_id)
            job_id = trigger_result.get("job_id")
            print(f"[bot] Scrape trigger result: {trigger_result}")

            if job_id:
                await status_message.edit_text("Updating database with fresh listings...")
                scrape_status, completed_in_wait = await wait_for_scrape_completion(job_id)
                print(f"[bot] Scrape status: {scrape_status} completed={completed_in_wait}")

                if completed_in_wait and scrape_status.get("status") == "done":
                    result = scrape_status.get("result") or {}
                    freshness_note = (
                        "Data refreshed just now "
                        f"(inserted={result.get('inserted', 0)}, updated={result.get('updated', 0)})."
                    )
                elif completed_in_wait and scrape_status.get("status") == "failed":
                    freshness_note = "Live refresh failed; showing latest stored results."
                else:
                    freshness_note = "Live refresh is still running; showing latest currently available results."
        except Exception as scrape_exc:
            print(f"[bot] On-demand scrape trigger failed: {scrape_exc}")
            freshness_note = "Live refresh is unavailable right now; showing latest stored results."

        # Query the database (strict)
        cars = search_cars(filters)

        relaxed_used = False
        if not cars and filters:
            relaxed_filters = build_relaxed_filters(filters)
            if relaxed_filters != filters:
                print(f"[bot] Retrying with relaxed filters: {relaxed_filters}")
                cars = search_cars(
                    relaxed_filters,
                    brand_match_in_model=True,
                )
                relaxed_used = bool(cars)
                if relaxed_used:
                    filters = relaxed_filters

        # Format and send results
        response_text = format_results(cars, filters)
        notes = []
        if freshness_note:
            notes.append(freshness_note)
        if relaxed_used:
            notes.append("Color data is often missing in source listings, so I used a broader match.")
        if notes:
            response_text = f"{' '.join(notes)}\n\n{response_text}"

        await status_message.edit_text("Preparing results...")
        await message.answer(response_text, parse_mode="HTML", disable_web_page_preview=True)

    except Exception as e:
        print(f"[bot] Error handling message: {e}")
        await message.answer(
            "Sorry, an error occurred while searching. Please try again later."
        )
