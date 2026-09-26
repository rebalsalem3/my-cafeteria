# My Cafeteria

#### Video Demo: <(https://youtu.be/noExUztceEY?si=ZCuh2oDS9DJ0cZXH)>

#### Description

My Cafeteria is a web app for running a cafeteria online. Customers browse the menu, add things to a cart, check out, earn loyalty points toward a discount, book a table, and leave a review once their order's delivered. Staff get a completely different side of the same app: a live kitchen screen, menu editing, sales reports, reservation management and the ability to add or remove other admins. Most of it updates in real time across every open tab so nobody's stuck refreshing the page to see if a new order came in or a table opened up.

This is our CS50x final project, built by two of us: Taimaa Saab ([Taimaa-Saab] · edX: `Taima75`) and Rebal Salem ([rebalsalem3] · edX: `rebell_8`).


To be honest we were tired of the usual repetitive CS project examples that everyone seems to do. We wanted to build a real world app that feels alive. We came up with the idea of creating our own restaurant designed entirely our way, so this app with the exact menu, features, and vibe we'd love to see in a real place felt like the perfect addition to bring that vision to life.

While we initially thought about dividing the modules like one working on the customer side and the other on the kitchen dashboard we ended up doing most of the work together We didn't divide the tasks 100% every logic step, UI design, and problem-solving process was an active discussion between the two of us.


## Key Technical Highlights


The database isn't one table, it's eight, tied together with foreign keys and constraints: `users`, `menu_items`, `orders`, `order_items`, `reviews`, `tables`, `reservations`, `notifications`. Order line items keep their own copy of the price at checkout, so bumping a menu price later doesn't quietly rewrite the total on somebody's old receipt.

There are also two genuinely different apps behind one login. The same `users` table and the same two decorators (`login_required`, `admin_required`) branch into completely different pages depending on whether `session["role"]` is `"user"` or `"admin"` — including one special super‑admin account that's the only one allowed to demote other admins.

Then there's the real‑time layer. Flask‑SocketIO pushes updates straight to the browser: a new order landing on the kitchen board, a cart badge updating in another tab, a menu item disappearing the second an admin removes it, an order‑ready alert going to exactly the customer it belongs to and nobody else. None of that gets walked through in the course's web lectures; we had to figure out the event design — and the bugs — on our own.

And there's real logic to get right, not just CRUD. The loyalty math (an order over $10 earns a point, five points earns 25% off and resets the counter), and the reservation rules (no past bookings, nothing more than 90 days out, nothing starting between midnight and 7am, and finding the smallest free table that both fits the party and doesn't overlap another booking in its 3‑hour window) are the kind of "figure out what the rules even are, then implement them" problems the course doesn't usually hand you pre‑solved.

## Features

### Customers
- Register and log in. Passwords are hashed with `scrypt` (Werkzeug), never stored as plain text.
- Browse the menu by category, add to a cart that updates live.
- Check out. Any order over $10 earns a loyalty point; five points gets you 25% off and resets the counter.
- Watch **My Orders**, and get a popup and sound the moment staff mark an order ready, even from a different page.
- Book a table by seats, date, and time, and see it under **My Reservations**.
- Leave a star rating and a written review once an order's delivered, viewable later under **My Reviews**.
- Change password.

### Staff / admins
- **Dashboard** — links to every admin tool.
- **Kitchen** — a live Kanban board (Pending → Preparing → Ready for Pickup), synced across every open kitchen screen, with a sound alert on new orders.
- **Menu Management** — add, edit, or remove items. Removing is a soft delete (`is_available = FALSE`) so it doesn't break past orders that reference the item. Adding an item under a name that already exists reactivates and updates it instead of duplicating it.
- **Reports** — today's order counts by status, catalog size, today's revenue, and today's best seller(s).
- **All Orders** — everything placed in the last 7 days.
- **Customer Reviews** — every review, newest first.
- **Reservations** — see what's booked, free up a table manually.
- **Add/Remove Managers** — any admin can promote a user to admin, but only one protected super-admin account can demote one. Demoting someone force-logs them out immediately.

## Why We Built It This Way

**Cart in the session, not the database.** Simpler than adding a whole `cart_items` table, and it clears itself when someone logs out. Trade-off: the cart doesn't follow you across devices. We were fine with that for a project this size.

**Server-side sessions.** A default Flask session is just a signed cookie: anyone can read it in dev tools (not forge it, just read it), and it's capped around 4KB. Our sessions carry a whole cart plus role and points, so we switched to Flask-Session — the data lives on the server, the browser only holds a session ID.

**`order_items.price` is a copy, not a lookup.** It's copied from the menu at checkout instead of joined later, so changing a price next week doesn't quietly rewrite a receipt from three weeks ago.

**Soft delete for menu items.** `is_available` flips to `FALSE` instead of an actual `DELETE`, because a real delete would break every past order referencing that item through the foreign key.

**Only user ID 1 can demote admins.** Any admin can promote someone else, but taking admin status away is restricted to one account, mainly so nobody can accidentally (or deliberately) lock everyone else out.

**Socket.IO instead of polling.** We went back and forth on this. The simple version is every page asking the server "anything new?" every few seconds — wasteful when nothing's changed, laggy if the interval's long enough to be efficient. A WebSocket lets the server push the moment something happens: a new order, a status change. The cost is real too — a persistent connection per tab, and more moving parts than a `fetch()` on a timer. For a live kitchen board it felt worth it.

Each logged-in user also joins a private room (`user_<id>`) on connect, which is what keeps an "order ready" popup from going to every customer instead of just the one it's for.

For reservations, the query picks the *smallest* free table that still fits the party, so a two-person table doesn't get handed the 6-seater while a bigger group waits. Reservation length is fixed at 3 hours instead of letting people pick — it made the overlap check a lot simpler, and three hours comfortably covers a meal anyway.

## Real-Time Events

| Event | Fires when | Updates |
| `cart_updated` | Item added to or removed from a cart | Navbar cart badge, live cart page |
| `new_order` | A customer checks out | Kitchen board, sound alert for admins |
| `order_ready` | Staff mark an order `completed` | A private popup and sound for that customer only |
| `menu_updated` | Admin adds, edits, or removes an item | Menu page re-fetches silently |
| `reservations_update` | A table's booked or freed | Admin reservations list re-fetches silently |
| `force_logout` | Super-admin demotes another admin | That admin's session ends immediately |

## Tech Stack

- **Backend:** Flask 3.0.3, Flask-SocketIO 5.3.6, Flask-Session 0.8.0, Werkzeug 3.0.3, python-dotenv 1.0.1
- **Database:** SQLite through CS50's `cs50.SQL` wrapper (`database/cafe.db`)
- **Frontend:** Jinja2, Bootstrap 5.3.0, custom CSS (dark glassmorphism, Fraunces + Manrope fonts), SweetAlert2, Socket.IO 4.0.1 client

## Database

Eight tables, tied together with foreign keys:

- **`users`** — account, hashed password, `role` (admin/user), loyalty `points`
- **`menu_items`** — name (unique), description, price, category, `is_available`
- **`orders`** — belongs to a user, status moves pending → preparing → completed → delivered, plus a `reviewed` flag
- **`order_items`** — line items, each with its own `price` captured at checkout
- **`reviews`** — one per order, 1–5 stars plus a comment
- **`tables`** — the physical tables and their seat counts
- **`reservations`** — a booking against a table, with its own status so freeing one up doesn't touch the `tables` row
- **`notifications`** — persisted "order ready" messages, so someone offline when it happened still sees it queued next time they check

## File Layout

**Backend**
- `app.py` — routes, the two access-control decorators (`login_required`, `admin_required`), Socket.IO handlers, and two template helpers (`flash_class`, `format_price`)
- `schema.sql` — all eight tables plus seed data (a super-admin, two sample customers, a starter menu, six tables)
- `requirements.txt` — pinned dependencies

**Templates**
- `layout.html` — chrome for logged-out pages
- `base.html` — chrome for logged-in customer pages, plus the Socket.IO connection and order-ready popup logic
- `dashboard.html` — chrome for admin pages, plus the admin home screen
- `index.html`, `register.html`, `login.html`, `change_password.html` — auth
- `menu.html`, `cart.html` — browsing and checkout
- `my_orders.html`, `reviews.html`, `view_my_reviews.html` — orders and reviews
- `reserve.html`, `my_reservations.html` — booking
- `kitchen.html` — the Kanban board
- `update_menu.html`, `add_item.html`, `update_item.html` — menu CRUD
- `reports.html`, `all_orders.html`, `customers_reviews.html` — reporting
- `admin_reservations.html` — reservation management
- `register_admin.html`, `remove_admin.html` — admin accounts

**Static**
- `static/style.css` — the visual design system
- `static/images/` — one photo per menu item (filename matches the item name), plus background art
- `static/audio/` — the two notification sounds

## Running It Locally

```bash
# 1. Clone the repo
git clone <https://github.com/rebalsalem3/my-cafeteria>
cd my_cafeteria


# 2. Install dependencies
pip install -r requirements.txt

# 3. Build the database from the schema
mkdir -p database
sqlite3 database/cafe.db < schema.sql

# 4. Set a real secret key
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(16))')" > .env

# 5. Run it
python app.py
```

Then open `http://localhost:5000`.

**Test accounts (from `schema.sql`):** `admin` / `admin123` for the admin dashboard. Two more accounts, `user1` and `user2`, are seeded for testing order flows — easiest to just register a fresh one and use that instead of tracking down their passwords.

## Known Limitations

A few things we're aware of and didn't get to:
Some HTML pages does not update automaticlly  such as my orders / my reservations / my reviews / costumer reviews / 
because it is not important to be changed live the user can simply hit reload to check from these stuff.

The flash appears in the buttom of the page so sometimes if the page has a lot of info the user needs to scroll down to see the flash notification.

## Authors

- `Taimaa Saab` — GitHub: `Taimaa-Saab` · edX:`Taima75`
- `Rebal Salem` — GitHub: `rebalsalem3` · edX: `rebell_8`

## Acknowledgments

We built the core logic and backend of this app entirely on our own every route, every Socket.IO event, and all the database logic was written manually. However we did use AI (Claude/gemini) as a helper for the frontend styling and documentation. Specifically we used it to generate the initial CSS file (setting up the color variables and the design system) so we wouldn't have to write all the boilerplate styling from scratch. We also used it to figure out how to add a simple notification sound effect in JavaScript (bypassing the browser's autoplay restrictions) and finally to help proofread and structure the README file. All the actual Python, SQL, and application logic is 100% our own work.