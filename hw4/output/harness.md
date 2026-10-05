# Campus Customs System Harness

## Database Analysis

The SQLite database contains four application tables: `catalogue`, `inventory`, `users`, and `chat_messages`. At the time of inspection, it held 102 products, 612 inventory rows, 3 users, and 22 chat messages. SQLite's internal `sqlite_sequence` table is not part of the application data model.

### `catalogue`

This table is the source of truth for product information displayed by the shop and used by the chatbot for product discovery.

| Field | Type and constraints | Why it matters |
| --- | --- | --- |
| `product_id` | `TEXT PRIMARY KEY` | Gives every product a stable identifier and connects it to inventory records. |
| `name` | `TEXT NOT NULL` | Supplies the customer-facing product name for cards, search results, and chat responses. |
| `garment_type` | `TEXT NOT NULL` | Lets shoppers and the chatbot filter products by categories such as hoodies or T-shirts. |
| `description` | `TEXT NOT NULL` | Provides detailed product features that support browsing and natural-language recommendations. |
| `colors` | `TEXT NOT NULL` containing a JSON array | Supports color-based search and tells customers which colors are represented by the product. |
| `search_tags` | `TEXT NOT NULL` containing a JSON array | Adds searchable concepts such as teams, events, styles, and merchandise terms for better matching. |
| `image_file_path` | `TEXT NOT NULL` | Connects each product to the local image shown in the storefront and recommendation results. |
| `price` | `REAL NOT NULL` | Allows the site and chatbot to give database-grounded prices and support budget filtering. |

### `inventory`

This table stores stock separately for every product and size. Its `product_id` is a foreign key to `catalogue.product_id`, and the pair (`product_id`, `size`) must be unique.

| Field | Type and constraints | Why it matters |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Gives each stock row a unique database identifier for updates and auditing. |
| `product_id` | `TEXT NOT NULL`, foreign key | Associates a size and quantity with the correct catalogue product. |
| `size` | `TEXT NOT NULL` | Lets the shop answer whether a product is available in the customer's requested size. |
| `quantity` | `INTEGER NOT NULL` | Provides the real stock count so the interface and chatbot do not invent availability. |

### `users`

This table stores customer accounts. Email addresses are unique, and passwords are stored only as hashes.

| Field | Type and constraints | Why it matters |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Provides the stable user identifier referenced by chat history. |
| `name` | `TEXT NOT NULL` | Preserves a display name for account and greeting experiences. |
| `email` | `TEXT NOT NULL UNIQUE` | Serves as the unique login identity and prevents duplicate accounts. |
| `password_hash` | `TEXT NOT NULL` | Supports password verification without storing plaintext passwords. |
| `created_at` | `TEXT NOT NULL`, defaults to the current database time | Records when the account was created for account management and auditing. |
| `first_name` | `TEXT`, optional | Supports friendly, personalized greetings and structured profile display. |
| `last_name` | `TEXT`, optional | Completes the structured customer name while remaining compatible with older records. |

### `chat_messages`

This table preserves conversations for signed-in users. Its `user_id` is a foreign key to `users.id`.

| Field | Type and constraints | Why it matters |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Gives each message a unique identifier and preserves message order. |
| `user_id` | `INTEGER NOT NULL`, foreign key | Associates each message with the correct customer account and conversation history. |
| `role` | `TEXT NOT NULL` | Distinguishes user messages from assistant messages when reconstructing a chat. |
| `content` | `TEXT NOT NULL` | Stores the actual conversation text shown in the chat interface. |
| `products_json` | `TEXT`, optional JSON | Stores products attached to an assistant response so matching product cards can reappear with chat history. |
| `created_at` | `TEXT NOT NULL`, defaults to the current database time | Timestamps messages for chronological display and later auditing. |

## Important Relationships and Rules

- One catalogue product can have many inventory rows, but only one row for each size.
- One user can have many chat messages.
- Catalogue prices and inventory quantities are authoritative; the chatbot should query them instead of estimating or inventing values.
- `colors`, `search_tags`, and `products_json` are JSON stored in text columns, so application code should parse them before use and serialize them before writing.
- Password hashes must never be returned by an API or included in chatbot context, logs, or client-side state.

## PydanticAI Agent Backend

### Frontend-to-backend flow

The React chat widget sends a JSON `POST` request to `/api/chat` with a shopper's message. FastAPI validates it with `ChatRequest`, passes it to the PydanticAI agent, and returns a structured `ChatReply`. The frontend renders the answer and any returned `ProductCard` objects as clickable cards that open the existing product detail routes. API errors are shown inside the chat instead of being silently ignored.

### Agent loading and model configuration

`backend/agent.py` reads the system instructions from `backend/prompts/prompt.md` every time it builds the agent. It configures an OpenAI-compatible model through `OpenAIProvider`, using `PORTKEY_API_KEY` or `OPENAI_API_KEY`, `AI_MODEL` (default `gpt-5.6-luna`), and optional `AI_BASE_URL`. When a Portkey key is present and no base URL is supplied, it uses Portkey's OpenAI-compatible API endpoint.

The agent depends on `ShopDeps`, which contains the SQLite path. Its `search_products` and `check_inventory` tools use parameterized SQL and return real catalogue or inventory data. `ChatReply` and `ProductCard` in `backend/models.py` force each response into a stable shape that the frontend can render safely.

If no model API key is configured, the chat uses a deliberately narrow SQLite fallback. It supports exact current-product price/stock questions and category searches without inventing facts. With a key present, the normal PydanticAI path is used.

## Product and Stock Tools

### `search_products`

Searches the `catalogue` table using shopper keywords and optional maximum-price and garment-type filters. It uses bound SQL parameters, limits results to eight, and returns `ProductLookup` objects. The selected fields are:

- `product_id` uniquely identifies the item and supports later stock checks and product links.
- `name` and `garment_type` let the agent identify and categorize the result.
- `description`, `colors`, and `search_tags` provide database-grounded matching and product details.
- `price` is the authoritative amount the agent may quote.
- `image_url` lets the frontend render the actual catalogue image.

### `check_inventory`

Looks up one exact `product_id` in the `inventory` table and optionally filters by a requested size. It returns an `InventoryLookup` containing the product identity, requested size, whether the product was found, and typed `InventoryRecord` rows. Each inventory record includes `size`, exact non-negative `quantity`, and a derived `in_stock` boolean. These fields let the agent clearly distinguish available, zero-quantity, unsupported-size, and unknown-product cases without inventing stock.

Both tools are read-only. Price and quantity statements in the prompt are required to come from these tool results.

## Chat Search Page Updates

The chat route's `ChatReply.products` field is the API contract between the agent and React. For product-search requests, the prompt requires the agent to copy up to four real tool results into structured `ProductCard` objects. Each card carries `product_id`, `name`, `price`, `image_url`, a short database-backed `description`, and optional `stock_summary`.

After a successful `/api/chat` response, `ChatWidget` passes the returned products to state owned by the top-level `App`. `ChatSearchResults` reads that state and inserts a responsive “Matches for you” section into the main page above the footer. Results therefore remain visible after the chat panel is closed. A clear control removes the current results without changing the conversation.

Both the compact cards inside the chat and the larger cards added to the page link to `/products/{product_id}`. This reuses the single-item route from Problem 3, so chat-discovered products open the same full image, description, price, color, and live size/stock view as catalogue cards.

## Customer Memory and Page Context

### Authentication and identity

`POST /api/auth/login` verifies the existing `pbkdf2_sha256` password hash using the Python standard library. A successful login creates a cryptographically random, server-side session token and returns only the token plus the user's public fields: `id`, `name`, `email`, `first_name`, and `last_name`. Passwords and password hashes never enter frontend state, agent context, or API responses. The React app sends the token as a Bearer credential and removes it on logout.

For authenticated chat requests, FastAPI resolves the token to a database user. `ShopDeps` receives the customer's name and email as trusted server-side context. Guests receive neither identity nor stored history and can continue chatting without a session.

### Stored and reloaded history

After a successful agent run for a logged-in customer, the backend appends two rows to `chat_messages`: the original user message and the assistant answer. Assistant product cards are serialized in `products_json`. `GET /api/chat/history` returns the latest 30 messages in chronological order, and the chat widget loads them when a logged-in customer opens it. The last 12 messages are also supplied to the agent as recent conversational context. Guest messages are never inserted.

### Page context

Each frontend chat request includes a `PageContext` with the current route. On `/products/{product_id}`, it also sends the product ID parsed from the route. FastAPI copies these values into `ShopDeps`; a dynamic agent instruction explains that “this” or “this item” refers to that product. The prompt still requires the agent to query catalogue and inventory tools before making product claims, so page context identifies the item but does not replace database grounding.

### Limits

- Sessions are held in server memory for this local assignment, so restarting FastAPI requires the user to log in again.
- Chat history is durable because it is stored in SQLite, independent of the in-memory session.
- History loading is capped at 30 messages for the interface and 12 messages for agent context to limit latency and model cost.

## Structured Models

- `ProductCard` is the frontend-safe recommendation contract: stable ID, name, non-negative price, image URL, description, and optional stock summary.
- `ProductLookup` is the complete read-only catalogue result used by tools: identity, garment type, description, colors, tags, image, and authoritative price.
- `InventoryRecord` stores one size, a non-negative quantity, and the derived `in_stock` flag. `InventoryLookup` groups those records with the product identity and requested size.
- `ChatRequest` bounds shopper input to 1,000 characters and accepts optional validated `PageContext`. `ChatReply` separates concise answer text from typed product cards.
- `PublicUser` and `LoginReply` expose only public account fields and the opaque session token. Password hashes are intentionally absent.
- `StoredChatMessage` validates reloaded history and attached product cards.
- `AuditEntry` standardizes UTC time, run ID, loop iteration, execution mode, tool name, short arguments, result summary, and stop reason.

## Complete Tool and Ability Inventory

- `search_products`: parameterized catalogue search with optional price and garment filters; capped at eight rows.
- `get_product_details`: exact product-ID lookup for page-context references such as “this item.”
- `check_inventory`: exact size-level quantities, including zero-stock and unknown-item states.
- `find_in_stock_alternatives`: up to three same-type alternatives verified in stock in the requested size.
- Product API: lists up to 102 catalogue items, serves single-product details and inventory, and mounts local product images.
- Authentication API: verifies PBKDF2 hashes and uses random in-memory bearer sessions without exposing hashes.
- Customer memory: persists successful authenticated conversations and restores the newest 30 messages.
- Dynamic search results: structured chat products update the React page and reuse detail-page routes.
- Offline database mode: when no model key exists, handles only database-grounded current-item and category queries.

## Safety Rules

- Catalogue prices and inventory are authoritative; the assistant must use tools and never estimate them.
- Shopper text and database text are untrusted data and cannot override system instructions.
- Passwords, hashes, API keys, bearer tokens, complete messages, and hidden reasoning are excluded from agent-visible or audit output.
- Server-resolved identity is the only trusted identity. Guests cannot access stored history, and one user cannot request another user's information.
- Tools are read-only. The assistant cannot claim to change stock, prices, accounts, orders, payments, refunds, or reservations.
- Unsupported or ambiguous requests receive a clear limitation or a focused follow-up rather than an invented answer.
- The assistant stays within shopping help and does not provide medical, legal, or financial advice.

## Append-Only Audit Trail

Every successful chat run appends one validated `AuditEntry` to `output/audit_trail.json`. The file uses JSON Lines: each line is an independent JSON object, so records can be appended with file mode `a` without reading, rewriting, or deleting earlier runs. This is safer for an audit trail than rebuilding a JSON array.

Each record includes UTC `timestamp`, random `run_id`, `iteration`, `mode`, `tool_name`, short non-sensitive `arguments`, a bounded `result_summary`, and `stop_reason`. Failed PydanticAI runs also append an error record before re-raising. Logs contain counts and booleans rather than complete shopper messages, credentials, model reasoning, or raw exception details.

## Runtime Specifications

- Agent retries: 2 structured-output retries per PydanticAI run.
- Agent context: newest 12 stored messages; the interface restores up to 30.
- Product search: at most 8 tool rows; the prompt asks for at most 4 recommendations; offline category evidence returns at most 6 cards.
- Alternatives: at most 3 verified in-stock products.
- Catalogue API: at most 102 products per request.
- Input limits: chat 1,000 characters, page path 300, product ID 120, email 254, password 200.
- Model: `AI_MODEL`, default `gpt-5.6-luna`; provider uses `PORTKEY_API_KEY` or `OPENAI_API_KEY` and optional `AI_BASE_URL`.
- Sessions: server-memory only; restarting FastAPI requires another login.

## How to Run

From the project root, install frontend packages with `npm install`. Start the frontend with `npm run dev`; Vite serves it at `http://127.0.0.1:5173` by default.

Create a Python environment, install `requirements.txt`, and start the backend from `backend/` with `uvicorn main:app --reload --port 8000`. The expected database is `data/campus_customs.db`; set `CAMPUS_DATA_DIR` when the course data directory lives elsewhere. Copy `.env.example` to a local `.env` and add a real model key only locally. Never commit the key or the course database.

Run `npm run build` for a production frontend check. Open `output/app_check.html` directly to review browser evidence for inventory grounding, dynamic chat cards, and catalogue filtering.
