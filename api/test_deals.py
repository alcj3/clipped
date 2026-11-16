import unittest
from datetime import datetime, timezone

from fastapi import HTTPException
from main import build_stores, get_deals, validate_search


NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)


def item(item_id, merchant, name, price, **changes):
    raw = {
        "id": item_id,
        "merchant_name": merchant,
        "name": name,
        "current_price": price,
        "original_price": None,
        "pre_price_text": None,
        "post_price_text": "lb",
        "sale_story": None,
        "valid_from": "2026-11-11T00:00:00+00:00",
        "valid_to": "2026-11-18T00:00:00+00:00",
        "clean_image_url": "https://example.com/deal.jpg",
        "_L1": "Food, Beverages & Tobacco",
    }
    raw.update(changes)
    return raw


class BuildStoresTest(unittest.TestCase):
    def test_filters_food_and_current_flyers_then_dedupes_and_sorts(self):
        results = [
            ("Chicken", [
                item(1, "Alpha Market", "Chicken thighs", 2.99),
                item(2, "Beta Market", "Chicken breast", 3.99),
                item(3, "Pet Store", "Chicken dog food", 8.99, _L1="Animals & Pet Supplies"),
                item(4, "Old Store", "Expired chicken", 1.99, valid_to="2026-11-15T00:00:00+00:00"),
                item(5, "Future Store", "Future chicken", 1.99, valid_from="2026-11-17T00:00:00+00:00"),
            ]),
            ("Dairy", [
                item(1, "Alpha Market", "Duplicate id", 2.99),
                item(6, "Beta Market", "Chicken breast", 3.99),
                item(7, "Beta Market", "Milk", 4.50, pre_price_text="2/", post_price_text="ea", original_price=5.00),
            ]),
        ]

        stores = build_stores(results, NOW)["stores"]

        self.assertEqual([store["name"] for store in stores], ["Beta Market", "Alpha Market"])
        self.assertEqual([store["count"] for store in stores], [2, 1])
        self.assertEqual({deal["id"] for store in stores for deal in store["deals"]}, {1, 2, 7})
        self.assertEqual(stores[1]["deals"][0]["category"], "Chicken")
        self.assertEqual(stores[0]["deals"][1]["price_text"], "2/$4.50 ea")
        self.assertEqual(stores[0]["deals"][1]["original_price"], 5.00)


class ValidationTest(unittest.TestCase):
    def test_accepts_known_categories_and_deduplicates_them(self):
        self.assertEqual(validate_search("10001", "Chicken,Dairy,Chicken"), ("10001", ["Chicken", "Dairy"]))

    def test_rejects_short_zip_before_fetching(self):
        with self.assertRaises(HTTPException) as caught:
            get_deals(zipcode="123", categories="Chicken")
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(caught.exception.detail, "Zip code must be exactly 5 digits.")

    def test_rejects_unknown_or_empty_categories(self):
        with self.assertRaisesRegex(ValueError, "Unknown categories: Furniture"):
            validate_search("10001", "Furniture")
        with self.assertRaisesRegex(ValueError, "Choose at least one category"):
            validate_search("10001", "")


if __name__ == "__main__":
    unittest.main()
