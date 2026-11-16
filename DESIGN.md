# clipped: design (direction B, "Aisle route")

The page answers one question: **where should I go this week?** Everything else serves that.

## Palette

| Role       | Hex       | Use                                         | Contrast              |
|------------|-----------|---------------------------------------------|-----------------------|
| background | `#EEF3EF` | page (mint-tinted gray)                     |                       |
| surface    | `#FFFFFF` | store sections, inputs                      |                       |
| text       | `#17322A` | body, headings (spruce)                     | 12.3 on bg, 13.8 on surface |
| muted      | `#5A6E66` | unit text, dates, counts                    | 4.85 on bg, 5.4 on surface  |
| accent     | `#BA3A25` | prices, the one primary button (white text) | 5.0 on bg, 5.65 on surface / white on it |
| danger     | `#9E1B1B` | error text                                  | 8.0 on surface        |

Lines between rows: `#17322A` at 12% opacity. Focus ring: 2px solid `#17322A` with a 2px offset.

## Type

- **Bricolage Grotesque** (Google Fonts) 700 for the wordmark and store names, 600 for category labels.
- **Atkinson Hyperlegible** (Google Fonts) 400 and 700 for everything else. Prices are 700 with tabular figures.
- Scale (rem): 0.8125 meta, 1 body, 1.125 deal name on desktop, 1.375 category label, 1.75 store name,
  2.25 wordmark. Line height 1.45 for body, 1.15 for headings.

## Spacing and radius

- Spacing scale (px): 4, 8, 12, 16, 24, 40, 64. Use 4 to 8 inside a deal row, 16 between rows' groups, 40 between
  stores.
- Radius: 12 on store sections, 8 on inputs and buttons, 999 on category toggles, 0 on rows. No shadows. Sections
  are separated by surface against background, not by borders.

## Layout

- **Top bar (sticky on desktop):** wordmark on the left, then the zip input, then the category toggles in one
  wrapping row (checkbox chips, selected = spruce fill + white text), then **one** primary button, "Find deals".
- **Results, the distinctive element:** a list of stores as large sections. Each store heading is in Bricolage
  Grotesque 1.75rem with "N deals" in muted text, aligned right on the same baseline. Inside, deals are grouped by
  category and laid out as table-like rows: name on the left, price in accent on the right, and unit text and end
  date underneath in muted. Desktop (1280): two columns of stores, masonry not required, left column first.
  Phone (375): one column, the controls collapse into a summary line ("Zip 10001, 5 categories" with an "Edit search" button) that reopens
  them.
- Selecting a deal row opens a native `<dialog>` with the flyer image and the full price text.
- Left aligned throughout. Empty states are text only.

## States

- **First visit:** no results area. One line under the controls: "Enter your zip to see this week's flyer deals near
  you."
- **Loading:** store sections replaced by three muted placeholder rows of fixed height. No spinner.
- **No deals:** "No flyer deals for Chicken, Dairy near 10001 this week. Try more categories or a nearby zip."
- **Source failed:** "Couldn't reach the flyer data (Flipp). Your settings are saved, so try Find deals again in a
  minute."

## Motion

One moment: when results arrive, store sections fade in (opacity only, 150ms, ease-out). Off under
`prefers-reduced-motion`.

## Banned-list check

No gradients, glow or glass. Typefaces chosen on purpose (not Inter or the system font). No hero, no card grid
(stores are list sections), no cards inside cards, no shadows, one primary button, no invented savings numbers,
no cream with serif and terracotta.
