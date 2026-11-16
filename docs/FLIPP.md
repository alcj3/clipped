# Flipp data: what we learned

Study of Flipp's undocumented JSON API for zip **98105**, run on 2026-11-15. It took 197 requests in 5 minutes,
about 0.9s apart, and all returned 200, with no rate limiting seen. The raw responses are outside this repo in
`~/personal_projects/clipped-research/flipp/raw/2026-11-15/98105/`, and the script is `crawl.py` next to them.
`manifest.jsonl` there lists every request.

Undocumented means it can change or block us without notice. Flipp's terms likely forbid automated access, so this
is fine for personal use but must be revisited before a public launch.

## Endpoints

Base: `https://backflipp.wishabi.com/flipp`. No auth, and no special headers needed.

| Call | Returns |
|------|---------|
| `GET /flyers?locale=en-us&postal_code=<zip>` | every flyer for the zip (102 for 10001, 62 for 98105) |
| `GET /flyers/<flyer_id>?locale=en-us` | every item in one flyer, with no categories |
| `GET /items/search?locale=en-us&postal_code=<zip>&q=<text>` | flyer items matching the text, plus ecom items, coupons and filters |

### `/flyers` (index)

Useful fields: `id`, `merchant` (sometimes ends in a tab, so trim it), `merchant_id`, `name`, `valid_from`,
`valid_to`, and `categories` (a list, e.g. `["All Flyers", "Groceries", ...]`).

- 21 of the 62 flyers for 98105 are tagged `Groceries`, from 17 stores: Albertsons, Bert's Red Apple, Dollar
  General, Fred Meyer, Grocery Outlet, Haggen, Lam's Seafood, Metropolitan Market, QFC, Restaurant Depot, Safeway,
  Sprouts, Super Saver Foods, Target, Uwajimaya, Viet Wah, Walmart.
- Some stores have two live flyers at once. Safeway and Albertsons each have a weekly ad plus a month-long "Big
  Book of Savings", and both repeat items.
- Flyers for next week appear early. Check `valid_from <= now <= valid_to`.

### `/flyers/<id>` (full flyer)

A flyer has 21 to 333 entries, 3,042 across the 21 grocery flyers. Fields: `id`, `flyer_id`, `name`, `brand`,
`price` (a **string**, `""` on 11% of real items), `discount`, `valid_from`, `valid_to`, `cutout_image_url`,
`display_type`.

- `display_type` 1 is a real item (2,619). 5 is a link or banner (256). 25 is something else (167). Keep only 1.
- There is no category field, so we would have to classify by name.

### `/items/search` (keyword search)

Fields per item: `id` (equal to the flyer's item `id`), `flyer_id`, `merchant_name`, `name`, `current_price`
(a **number**), `original_price` (often null), `pre_price_text`, `post_price_text` (e.g. `/LB.`), `sale_story`,
`valid_from`, `valid_to`, `clean_image_url`, `_L1`/`_L2` (Flipp's category, e.g. `Food, Beverages & Tobacco` /
`Food Items`).

- At most **150** items per query.
- Broad words work and specific phrases often return nothing. "chicken" gives 31, but "whole chicken", "ground
  turkey", "rotisserie chicken", "sirloin", "brisket", "halibut", "bananas" and "strawberries" all gave 0. The
  query seems to match whole phrases in the item name, and a 0 means no flyer item has that phrase this week.
- The results are clean. Filtering on `_L1` starting with `Food` drops almost nothing for meat, fish or dairy
  words. Broad words like "candy", "frozen" and "snacks" pull in some non-food.
- An empty `q` returns 150 mixed items and 150 coupons, which is useless.
- `ecom_items` and `coupons` come back too. We ignore them in v1.

## Search vs sweeping every flyer (98105, "is the item in the grocery flyers")

| Word | Search hits | Flyer items whose name contains the word | Of those, found by search |
|------|-------------|------------------------------------------|---------------------------|
| chicken | 31 | 50 | 31 |
| salmon | 13 | 14 | 13 |
| beef | 32 | 34 | 25 |
| milk | 18 | 23 | 14 |
| wine | 18 | 11 | 11 |
| beer | 8 | 5 | 3 |

What search left out for "chicken" was mostly noise: broth, cream of chicken soup, dog food, canned tuna ("Chicken
of the Sea"). It also missed a few real ones: stewing chicken at Lam's, chicken breast tenders at Grocery Outlet,
and nuggets at Safeway and Albertsons. Search also finds alcohol in non-grocery flyers (e.g. drugstores), which the
grocery sweep would miss.

## Decision for v1

**Use search with broad keywords**, about 25 calls per zip, cached for 3 hours. It gives numeric prices, unit
text, Flipp's own categories and the best noise filtering. The sweep would mean writing our own classifier
with exclude lists, and it's worth it later for meal planning, when we need the whole catalog anyway.

Rules:
- Use broad words only, since specific phrases return 0.
- Keep `_L1` starting with `Food`.
- Keep items where `valid_from <= now <= valid_to`.
- Dedupe by `id`, then by (merchant, name, price) to fold Safeway and Albertsons double flyers.

### Keyword map (tested on 98105)

| Category | Keywords | Notes |
|----------|----------|-------|
| Chicken | chicken, turkey | Specific cuts returned 0 or were already covered by "chicken" |
| Beef & pork | beef, pork, steak, bacon, ham, sausage, ribs, lamb, ground beef | |
| Fish & seafood | seafood, fish, salmon, shrimp, cod, crab | "seafood" 80, mostly Lam's and Uwajimaya |
| Dairy | milk, cheese, yogurt, butter, cream cheese, sour cream, ice cream | "butter" catches peanut butter, so keep it with care |
| Eggs | eggs | |
| Alcohol | beer, wine, whiskey, vodka, cider, liquor, tequila | Thin in WA grocery flyers (1 to 18 per word) |
| Produce | apples, salad, vegetables, fruit, potatoes, tomatoes, onions, oranges, peppers | |
| Bread & grains | bread, cereal, rice, pasta, tortillas, bagels | "buns" catches non-food, so leave it out |
| Snacks | chips, cookies, crackers, chocolate, popcorn | "snacks" and "candy" are noisy |
| Frozen | frozen pizza, frozen vegetables, frozen meals | "frozen" alone is noisy (11 of 54 are non-food) |

Recheck the map with a fresh crawl now and then. Flyers change weekly, so one-week zeros may not mean much.

## To revisit

- Whether specific phrases return 0 only because of this week's flyers. Rerun the crawl next week.
- Rate limits: a probe on 2026-11-16 (`ratetest.py`, log in `raw/ratetest-2026-11-16-98105.jsonl`) ran 50 searches
  back to back (about 1.5 per second), then 50 with 4 at a time (about 5.7 per second). All 100 returned 200, with
  a median of about 620ms either way and no slowdown. A cold cache for a zip (about 25 searches) takes about 4
  seconds with 4 at a time. Untested beyond 4 at a time, so don't go higher without a reason.
- Run one crawl for a non-Seattle zip before college students outside Seattle use the app.
