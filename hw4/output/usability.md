# Usability Improvements

## Frontend Improvement 1: Product Filters and Sorting

**What I added:** The Products page now includes a garment-type filter and sorting controls for featured order, price low-to-high, price high-to-low, and product name. The controls work with text search, update the visible result count immediately, and include a one-click reset state.

**Why it helps:** The catalogue contains more than one hundred items. Shoppers can narrow the collection to the garment they want and compare prices without scrolling through every product.

## Frontend Improvement 2: Recently Viewed Products

**What I added:** Opening a single-item page saves that product to a small recently viewed list in local browser storage. The Products page displays up to four recent items with links back to their full detail pages.

**Why it helps:** Shoppers often compare similar Yale designs. Recently viewed items let them return to earlier choices without repeating searches, while keeping this history private to their browser.

## Agent/Backend Improvement 1: Exact Product Detail Tool

**What I added:** The PydanticAI agent now has a `get_product_details` tool that retrieves one exact catalogue record by `product_id` and returns a typed `ProductLookup` result.

**Why it helps:** Questions about “this item” no longer depend on fuzzy keyword matching. The agent can combine page context with an exact lookup, reducing wrong-product descriptions and prices while reading only one row.

## Agent/Backend Improvement 2: In-Stock Alternative Tool

**What I added:** The agent now has a `find_in_stock_alternatives` tool. Given a product and requested size, it finds a small set of same-garment-type alternatives with positive inventory in that exact size.

**Why it helps:** An out-of-stock answer can still move the shopper forward. The agent can offer relevant, verifiably available substitutes instead of ending the conversation or inventing availability.
