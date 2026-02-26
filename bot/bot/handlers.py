from aiogram import Router, types

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


@router.message()
async def handle_message(message: types.Message):
    """Handle any incoming text message."""
    if not message.text:
        await message.answer("Please send a text message to search for cars.")
        return

    await message.answer("Searching for cars...")

    try:
        # Extract search parameters using Gemini
        filters = await extract_search_params(message.text)
        print(f"[bot] Extracted filters: {filters}")

        # Query the database
        cars = search_cars(filters)

        # Format and send results
        response_text = format_results(cars, filters)
        await message.answer(response_text, parse_mode="HTML", disable_web_page_preview=True)

    except Exception as e:
        print(f"[bot] Error handling message: {e}")
        await message.answer(
            "Sorry, an error occurred while searching. Please try again later."
        )
