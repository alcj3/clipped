import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Query


CATEGORIES = {
    "Chicken": ["chicken", "turkey"],
    "Beef & pork": ["beef", "pork", "steak", "bacon", "ham", "sausage", "ribs", "lamb", "ground beef"],
    "Fish & seafood": ["seafood", "fish", "salmon", "shrimp", "cod", "crab"],
    "Dairy": ["milk", "cheese", "yogurt", "butter", "cream cheese", "sour cream", "ice cream"],
    "Eggs": ["eggs"],
    "Alcohol": ["beer", "wine", "whiskey", "vodka", "cider", "liquor", "tequila"],
    "Produce": ["apples", "salad", "vegetables", "fruit", "potatoes", "tomatoes", "onions", "oranges", "peppers"],
    "Bread & grains": ["bread", "cereal", "rice", "pasta", "tortillas", "bagels"],
    "Snacks": ["chips", "cookies", "crackers", "chocolate", "popcorn"],
    "Frozen": ["frozen pizza", "frozen vegetables", "frozen meals"],
}

FLIPP_URL = "https://backflipp.wishabi.com/flipp/items/search"
CACHE_SECONDS = 3 * 60 * 60
MAX_RESPONSE_BYTES = 5_000_000
_cache: dict[tuple[str, str], tuple[float, list[dict]]] = {}
_category_order = {category: index for index, category in enumerate(CATEGORIES)}
app = FastAPI()


def validate_search(zipcode: str, categories: str) -> tuple[str, list[str]]:
    if not re.fullmatch(r"[0-9]{5}", zipcode):
        raise ValueError("Zip code must be exactly 5 digits.")

    requested = [name.strip() for name in categories.split(",") if name.strip()]
    if not requested:
        raise ValueError("Choose at least one category.")
    unknown = [name for name in requested if name not in CATEGORIES]
    if unknown:
        raise ValueError(f"Unknown categories: {', '.join(unknown)}.")

    return zipcode, list(dict.fromkeys(requested))


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _timestamp(value: object) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _number(value: object) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return value
    return None


def _price_text(item: dict, price: int | float | None) -> str:
    prefix = _text(item.get("pre_price_text"))
    amount = f"${price:.2f}" if price is not None else ""
    if prefix and amount:
        amount = f"{prefix}{amount}" if prefix.endswith(("/", "$")) else f"{prefix} {amount}"
    elif prefix:
        amount = prefix
    parts = [amount, _text(item.get("post_price_text")), _text(item.get("sale_story"))]
    return " ".join(part for part in parts if part)


def build_stores(search_results: list[tuple[str, list[dict]]], now: datetime) -> dict:
    """Filter and group raw Flipp items without performing any I/O."""
    seen_ids = set()
    seen_deals = set()
    grouped: dict[str, list[dict]] = {}

    for category, items in search_results:
        for item in items:
            if not isinstance(item, dict) or not _text(item.get("_L1")).startswith("Food"):
                continue

            valid_from = _timestamp(item.get("valid_from"))
            valid_to = _timestamp(item.get("valid_to"))
            if valid_from is None or valid_to is None or not valid_from <= now <= valid_to:
                continue

            item_id = item.get("id")
            store = _text(item.get("merchant_name"))
            name = _text(item.get("name"))
            if not isinstance(item_id, (str, int)) or isinstance(item_id, bool) or not store or not name:
                continue

            price = _number(item.get("current_price"))
            identity = (store, name, price)
            if item_id in seen_ids or identity in seen_deals:
                continue
            price_text = _price_text(item, price)
            if price is None and not price_text:
                continue

            seen_ids.add(item_id)
            seen_deals.add(identity)
            grouped.setdefault(store, []).append({
                "id": item_id,
                "category": category,
                "name": name,
                "price": price,
                "price_text": price_text,
                "original_price": _number(item.get("original_price")),
                "valid_to": _text(item.get("valid_to")),
                "image": _text(item.get("clean_image_url")),
            })

    stores = []
    for name, deals in grouped.items():
        deals.sort(key=lambda deal: (_category_order.get(deal["category"], len(CATEGORIES)), deal["name"].casefold()))
        stores.append({"name": name, "count": len(deals), "deals": deals})
    stores.sort(key=lambda store: (-store["count"], store["name"].casefold()))
    return {"stores": stores}


def fetch_keyword(zipcode: str, keyword: str) -> list[dict]:
    key = (zipcode, keyword)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    query = urlencode({"locale": "en-us", "postal_code": zipcode, "q": keyword})
    request = Request(
        f"{FLIPP_URL}?{query}",
        headers={"Accept": "application/json", "User-Agent": "clipped/1.0 (personal flyer search)"},
    )
    with urlopen(request, timeout=10) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("Flipp response was too large")
    data = json.loads(payload)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("Flipp response did not contain items")

    items = data["items"]
    _cache[key] = (time.monotonic(), items)
    return items


@app.get("/api/categories")
def get_categories() -> dict:
    return {"categories": list(CATEGORIES)}


@app.get("/api/deals")
def get_deals(zipcode: str = Query(default="", alias="zip"), categories: str = Query(default="")) -> dict:
    try:
        zipcode, selected = validate_search(zipcode, categories)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    searches = [(category, keyword) for category in selected for keyword in CATEGORIES[category]]
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(fetch_keyword, zipcode, keyword) for _, keyword in searches]
            results = [(category, future.result()) for (category, _), future in zip(searches, futures)]
    except (URLError, TimeoutError, OSError, ValueError, TypeError) as error:
        raise HTTPException(status_code=502, detail="flyer source unavailable") from error

    return build_stores(results, datetime.now(timezone.utc))
