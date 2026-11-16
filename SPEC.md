# clipped: spec

clipped takes your zip code and the grocery categories you care about. It shows which stores near you have them in
this week's flyers, and at what price.

## Users

- **MVP:** the owner. Checks deals at a laptop or phone *before* going shopping, mainly for meat, chicken, fish,
  dairy and alcohol.
- **Next:** college students on a tight budget.
- **Later:** a general audience.

## Tasks (MVP)

1. **Set zip code.** The user enters a 5-digit US zip code. The app validates it and remembers it in the browser
   (localStorage) for the next visit.
2. **Choose categories.** The user picks one or more categories from a fixed list (below), and the choice is
   remembered. Each category maps to one or more search keywords on the server. The defaults are the owner's
   categories: Chicken, Beef & pork, Fish & seafood, Dairy, Alcohol.
3. **See deals.** The user presses "Find deals". The server queries the flyer data once per keyword for that zip,
   keeps only food and drink items in current flyers, and drops duplicates. The page groups the results **by
   store**, with stores ordered by how many matching deals they have. Under each store, deals are grouped by
   category and show name, price with unit text (e.g. `$0.79 /lb`), the original price when the flyer gives one,
   and the end date.
4. **Open a deal.** Selecting a deal shows its flyer image (`clean_image_url`) so the user can read the fine print
   (limits, "with card", box sizes).

### Category list (v1)

Chicken, Beef & pork, Fish & seafood, Dairy, Eggs, Alcohol, Produce, Bread & grains, Snacks, Frozen. The
keyword map lives in one server-side dict and is easy to edit.

## Data source

- **Flipp's search JSON** (the endpoint flipp.com itself calls):
  `GET https://backflipp.wishabi.com/flipp/items/search?locale=en-us&postal_code=<zip>&q=<keyword>`.
  Tested on 2026-11-15: `q=chicken` for 10001 returned 122 items with `merchant_name`, `name`, `current_price`,
  `original_price` (often null), `pre_price_text`, `post_price_text`, `sale_story`, `valid_from`, `valid_to`,
  `clean_image_url`, `_L1`/`_L2` categories.
- **Limits:**
  - The endpoint is undocumented and can change or block us without notice. If it does, the app says deals are
    unavailable, not that there are no deals.
  - Flipp's terms likely forbid automated access. That is acceptable for personal use only, and must be revisited
    before any public launch.
  - Keyword search is noisy ("chicken" also matches chicken broth and dog food). Filter on `_L1`, and accept some
    noise in v1.
  - Many items have no original price, so "% off" can't always be shown. Never invent a savings figure.
  - Flyer coverage depends on the region. Some stores won't appear.
- **Caching:** cache responses on the server in memory, keyed by (zip, keyword), for 3 hours, to be polite and fast.
- No accounts, no database. Preferences stay in the browser.

## Stack

- `api/`: FastAPI (Python). One endpoint, `GET /api/deals?zip=&categories=`. Calls Flipp with the stdlib or an
  already-required HTTP client, plus the cache.
- `web/`: React + TypeScript via Vite. No UI kit. Styles come from DESIGN.md.
- Desktop and phone are both first-class (recomposed at 375px).

## Done (v1)

The owner enters their zip and keeps the default categories, then sees this week's chicken, meat, fish, dairy and
alcohol deals grouped by store, accurate enough to plan a trip.

## Out of scope (v1)

- Grocery lists, meal plans, budget goals (next phases).
- Accounts, sync across devices, any database.
- Store hours, maps, distance.
- Coupons, loyalty programs, price history.
- Non-US postal codes.
- Native app or PWA.
