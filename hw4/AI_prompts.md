# AI Prompt Log

This file records the prompts used while completing Homework 4. Each problem has its own section, and follow-up prompts are included only when they were actually needed.

## Problem 1: Vibe Coder Prompts

### Initial prompt

Help me build Homework 4 one problem at a time. The finished project will be a Campus Customs shopping website with a React, Vite, and TypeScript frontend plus a FastAPI backend powered by a PydanticAI agent. Please keep all submitted files in English, use the provided SQLite database as the source of truth for products, inventory, and users, and maintain this `AI_prompts.md` file as we work. For every problem, add the problem number and title, the prompt I gave you in my own words, and a follow-up prompt only if one was needed.

### Follow-up

No follow-up prompt was needed for this problem because the initial request fully specified the prompt-log format and working process.

## Problem 2: Analyze the Database

### Initial prompt

Inspect the provided `data/campus_customs.db` SQLite database and document its application tables in `output/harness.md`. For every table, list each field and briefly explain why that field matters to the online shop or chatbot. Base the write-up on the real schema rather than assumptions, include relationships and important constraints, and cover the catalogue, inventory, users, and any other application table you find.

### Follow-up

No follow-up prompt was needed because the database schema and sample records provided enough information to document the tables accurately.

## Problem 3: Build the Campus Customs Website

### Initial prompt

Build a polished Campus Customs storefront with a React, Vite, and TypeScript frontend. Use original copy and a visual direction inspired by the official Yale Bulldog Blue shop without copying its text. Include responsive navigation to Home, Products, About Us, Log in, and Create account; show real database products with images, prices, and short descriptions; make every product card open a detailed page with inventory by size; and add a floating chat interface that can remain a local stub for now. Create a small FastAPI service in `backend/main.py` to read products and inventory from SQLite and serve the local product images.

### Follow-up

After the first implementation, verify that the production build succeeds and inspect the running site at desktop and mobile sizes. Fix any layout, loading, routing, or image-serving problems found during that review.

## Problem 5: PydanticAI Agent Backend

### Initial prompt

Turn the existing chat widget into a real PydanticAI shopping assistant behind FastAPI. Keep the agent organized as `backend/prompts/prompt.md`, `backend/agent.py`, `backend/tools.py`, and `backend/models.py`, with the HTTP app in `backend/main.py`. Load the system prompt from disk, use structured chat and product-card models, give the agent parameterized catalogue-search and inventory-checking tools, and connect the frontend to a JSON chat route. Configure the model from environment variables without committing any key, and make database prices and stock the only source of truth.

### Follow-up

Test the agent with PydanticAI's local test model because no API key is present, verify that the backend starts from inside the `backend/` directory, and confirm that the frontend handles both successful structured replies and missing-key errors clearly.

## Problem 6: Tools: Product Info and Stock

### Initial prompt

Strengthen the shopping agent's database tools so product descriptions, prices, and size-level stock always come from `campus_customs.db`. Define typed Pydantic lookup results in `backend/models.py`, return those types from the catalogue and inventory tools, and explicitly tell the agent to call them before making product, price, or availability claims. An unavailable size must be reported clearly with a zero quantity rather than guessed.

### Follow-up

Test the tools directly against the supplied database for a real product search, an in-stock size, a zero-stock size, an unsupported size, and an unknown product. Then document every tool and explain why each lookup model field is needed in `output/harness.md`.

## Problem 7: Chat Search That Updates the Page

### Initial prompt

Make product searches in the chat dynamically add matching catalogue items to the website itself. Treat `ChatReply.products` as the API contract: the PydanticAI agent should return database-backed product cards for item-search requests, and the React app should store those results at the top level and render a responsive matching-items section with image, name, price, and short description. Keep compact cards in the chat as well.

### Follow-up

Ensure every dynamically inserted card uses the existing `/products/{product_id}` route so it opens the full single-item page from Problem 3. Add a clear-results action, preserve accessibility labels and responsive behavior, verify the structured API contract without a paid model call, and document how results travel from the agent to the page.

## Problem 8: Customer Memory

### Initial prompt

Add customer memory for logged-in shoppers while keeping guest chat available and non-persistent. Implement secure login against the existing PBKDF2 password hashes, issue random server-side session tokens, store successful authenticated conversations in `chat_messages`, reload them when the customer returns, and pass only trusted public identity fields into the agent dependencies. Never expose or send password hashes to the frontend or model.

### Follow-up

Send page context with every chat request, including the current product ID on a product detail route, so references such as “this item” are unambiguous. Test the complete flow against a temporary database copy: guest non-persistence, login, identity injection, product-page context, two-role message writes, stored product-card restoration, and history reload. Document the storage format, identity fields, context flow, and limits in `output/harness.md`.

## Problem 9: Usability Improvements

### Initial prompt

Implement four practical usability improvements and document each one before or while building it. On the frontend, add combined garment-type filtering and sorting to the large product catalogue, plus a private browser-local recently viewed section that links back to product details. On the agent backend, add an exact product-detail tool for page-context questions and an in-stock alternative tool for requested sizes that are unavailable.

### Follow-up

Verify the filtering and sorting logic, recent-item storage limit, exact lookup behavior, and alternative recommendations against the real catalogue and inventory. Confirm the new agent tools are registered, run the production frontend build, and write `output/usability.md` with what each improvement adds and why it benefits a Campus Customs shopper or the business.

## Problem 10: Style the Website

### Initial prompt

Give the existing Campus Customs storefront a cohesive, imaginative retail design without changing its working routes or features. Strengthen typography, color hierarchy, product presentation, navigation, forms, and the chat experience. Keep Yale blue as the anchor, but add warm gold and restrained coral accents so the interface does not feel monochromatic. Use polished hover, focus, and entry states while respecting reduced-motion preferences.

### Follow-up

Check the refreshed site at desktop and mobile widths, including the home hero, catalogue controls, product cards, product detail view, account form, and floating chat. Confirm text stays readable, controls remain keyboard-visible, layouts do not overlap, and the production frontend build succeeds. Write a concise `output/design.md` describing the concrete changes and why they improve shopper confidence and conversion.

## Problem 11: Site Testing (App Check)

### Initial prompt

Test the running Campus Customs site and create `output/app_check.html` as a simple, self-contained grading report. Capture real browser evidence for three checks: a chat answer that uses database price and size inventory, dynamic product cards after a category question, and the catalogue filter added in Problem 9. Store PNG files under `output/app_check_images/` and use relative image paths in the report.

### Follow-up

The local environment has no model API key, so add a narrow database-backed fallback that keeps the site testable without replacing the configured PydanticAI path. It must only answer exact current-product price or stock questions and catalogue category searches using SQLite values. Re-run all browser checks, reject failed screenshots, verify the final images and captions, and confirm the frontend build and backend tests still pass.

## Problem 12: Audit Trail, Safety, and Finish Harness

### Initial prompt

Add a privacy-conscious append-only audit trail for every chat run. Define an `AuditEntry` Pydantic model and append one JSON object per line to `output/audit_trail.json` with UTC time, run ID, iteration, mode, tool name, short non-sensitive arguments and result, and stop reason. Never erase existing records or log secrets, full customer messages, session tokens, hidden reasoning, or raw exception details. Expand the system prompt with concrete grounding, privacy, prompt-injection, authorization, and read-only commerce safety rules.

### Follow-up

Finish `output/harness.md` so a manager can understand all structured models, tools, abilities, customer memory, safety rules, audit format, execution limits, model configuration, and exact frontend/backend run commands. Run the chat twice and prove the audit file grows while preserving prior entries; validate every line with `AuditEntry`, run Python compilation and the production frontend build, then sync the finished work to the submission folder.
