import re

import google.generativeai as genai

from bot.config import settings

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

# Define the function declaration for Gemini
search_cars_function = genai.protos.FunctionDeclaration(
    name="search_cars",
    description=(
        "Search for cars in the database based on user criteria. "
        "Extract filter parameters from the user's natural language query."
    ),
    parameters=genai.protos.Schema(
        type=genai.protos.Type.OBJECT,
        properties={
            "brand": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description="Car brand/manufacturer (e.g. Toyota, BMW, Honda, Mercedes)",
            ),
            "model": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description="Car model name (e.g. Camry, X5, Civic)",
            ),
            "color": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description="Car color (e.g. red, black, white, blue)",
            ),
            "min_price": genai.protos.Schema(
                type=genai.protos.Type.INTEGER,
                description="Minimum price in Japanese Yen",
            ),
            "max_price": genai.protos.Schema(
                type=genai.protos.Type.INTEGER,
                description="Maximum price in Japanese Yen",
            ),
            "min_year": genai.protos.Schema(
                type=genai.protos.Type.INTEGER,
                description="Minimum manufacturing year",
            ),
            "max_year": genai.protos.Schema(
                type=genai.protos.Type.INTEGER,
                description="Maximum manufacturing year",
            ),
        },
    ),
)

tool = genai.protos.Tool(function_declarations=[search_cars_function])

BRAND_ALIASES = {
    "bmw": "BMW",
    "бмв": "BMW",
    "toyota": "Toyota",
    "тойота": "Toyota",
    "honda": "Honda",
    "хонда": "Honda",
    "nissan": "Nissan",
    "ниссан": "Nissan",
    "mercedes": "Mercedes",
    "benz": "Mercedes",
    "мерседес": "Mercedes",
    "audi": "Audi",
    "ауди": "Audi",
    "mazda": "Mazda",
    "мазда": "Mazda",
    "subaru": "Subaru",
    "субару": "Subaru",
    "lexus": "Lexus",
    "лексус": "Lexus",
}

COLOR_ALIASES = {
    "red": "red",
    "красн": "red",
    "blue": "blue",
    "син": "blue",
    "black": "black",
    "черн": "black",
    "чёрн": "black",
    "white": "white",
    "бел": "white",
    "gray": "gray",
    "grey": "gray",
    "сер": "gray",
    "green": "green",
    "зел": "green",
    "yellow": "yellow",
    "жел": "yellow",
}

SYSTEM_PROMPT = """You are a helpful car search assistant. Users will ask you to find cars in natural language.
Your job is to extract search parameters from their query and call the search_cars function.

Important notes:
- Prices in the database are in Japanese Yen (JPY).
- If the user mentions prices in "万" (man/10,000), multiply by 10,000 to convert to yen.
  For example: "200万" = 2,000,000 yen, "50万" = 500,000 yen.
- If the user mentions "млн" (million), multiply by 1,000,000.
  For example: "2 млн" = 2,000,000 yen.
- Common color translations: красный=red, синий=blue, чёрный=black, белый=white, зелёный=green, серый=gray, жёлтый=yellow.
- Always call the search_cars function to look up cars, even if the query is vague.
- Extract as many parameters as you can from the user's message.
"""


def _extract_rule_based_params(user_message: str) -> dict:
    """Best-effort parser for common brand/color/price patterns when LLM tool call is missing."""
    text = user_message.lower()
    params: dict = {}

    for alias, brand in BRAND_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            params["brand"] = brand
            break

    for alias, color in COLOR_ALIASES.items():
        if alias in text:
            params["color"] = color
            break

    max_mln = re.search(r"(?:до|up to|under|<=?)\s*(\d+(?:[.,]\d+)?)\s*(?:млн|million)", text)
    if max_mln:
        params["max_price"] = int(float(max_mln.group(1).replace(",", ".")) * 1_000_000)

    min_mln = re.search(r"(?:от|from|>=?)\s*(\d+(?:[.,]\d+)?)\s*(?:млн|million)", text)
    if min_mln:
        params["min_price"] = int(float(min_mln.group(1).replace(",", ".")) * 1_000_000)

    max_man = re.search(r"(?:до|up to|under|<=?)\s*(\d+(?:[.,]\d+)?)\s*万", text)
    if max_man:
        params["max_price"] = int(float(max_man.group(1).replace(",", ".")) * 10_000)

    min_man = re.search(r"(?:от|from|>=?)\s*(\d+(?:[.,]\d+)?)\s*万", text)
    if min_man:
        params["min_price"] = int(float(min_man.group(1).replace(",", ".")) * 10_000)

    return params


def _merge_filters(primary: dict, fallback: dict) -> dict:
    merged = dict(fallback)
    for key, value in primary.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        merged[key] = value
    return merged


async def extract_search_params(user_message: str) -> dict:
    """Use Gemini to extract car search parameters from a natural language query."""
    fallback_params = _extract_rule_based_params(user_message)
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=[tool],
            system_instruction=SYSTEM_PROMPT,
        )

        chat = model.start_chat()
        response = chat.send_message(user_message)

        # Check if there's a function call in the response
        for part in response.parts:
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                if fc.name == "search_cars":
                    # Convert proto map to dict
                    params = {}
                    for key, value in fc.args.items():
                        params[key] = value
                    merged = _merge_filters(params, fallback_params)
                    print(f"[llm] Merged params: {merged}")
                    return merged

        # If no function call, return empty params (will return all cars)
        if fallback_params:
            print(f"[llm] Fallback params: {fallback_params}")
        return fallback_params

    except Exception as e:
        print(f"[llm] Error extracting params: {e}")
        if fallback_params:
            print(f"[llm] Using fallback params after error: {fallback_params}")
        return fallback_params
