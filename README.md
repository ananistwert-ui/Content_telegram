# Multi-Tenant Telegram Bot Ecosystem

Production-ready reference implementation: one **Master Admin Bot** controls
an arbitrary number of **Child Bots**, all sharing one Postgres database,
one Redis instance, one codebase, and one running process — only the
Telegram token + DB-driven config differ between child bots.

## 1. Architecture

```
                 ┌─────────────────────┐
Telegram ───────▶│  aiohttp web app     │
 (webhooks)      │  /webhook/admin      │──▶ admin_dp (FSM via Redis) ──▶ admin_router
                 │  /webhook/{bot_id}   │──▶ user_dp  (shared)        ──▶ user_router
                 └─────────┬────────────┘
                           │  DbSessionMiddleware / BotContextMiddleware / Throttling
                           ▼
                 ┌─────────────────────┐        ┌────────────┐
                 │   Service layer      │◀──────▶│   Redis    │  (sub-check cache,
                 │ (business rules)     │        │            │   FSM, throttling,
                 └─────────┬────────────┘        └────────────┘   webhook route cache)
                           ▼
                 ┌─────────────────────┐        ┌────────────┐
                 │  Repository layer    │◀──────▶│  Postgres  │
                 └─────────────────────┘        └────────────┘

                 ┌─────────────────────┐
                 │  arq worker           │──▶ scheduled + rate-limited broadcasts
                 │  (separate process)   │    (cron sweep every minute)
                 └─────────────────────┘
```

**Why webhook, not polling.** At ~5000 concurrent users across N bots,
long-polling would mean N competing infinite loops. One aiohttp process
with one route per bot scales horizontally (just add web replicas behind
a load balancer) and only costs resources on actual traffic.

**Why one shared `Dispatcher` for all child bots.** Every handler reads
bot-specific data (`db_bot`, `db_bot_config`) injected by
`BotContextMiddleware` instead of hardcoding anything — this is what makes
the same code run identically for bot #1 and bot #47. The **admin bot
runs its own separate `Dispatcher`** (`admin_dp`) so that if the admin
opens a child bot personally, they get the normal user flow there, not
the admin panel — cleanly avoids reusing one Dispatcher across roles.

**Why Redis is required, not optional.**
- FSM storage for the admin bot's multi-step wizards (register bot, edit
  welcome, add channel, create broadcast, ...) — survives restarts.
- Subscription-check cache: `getChatMember` is rate-limited and users
  mash "Check Again"; a 30s TTL cache avoids hammering Telegram.
- Per-(bot,user) throttling to survive spam/abuse at scale.
- `bot_id → DB row id` cache so the hot path (every single update) skips
  a DB query.

**Why `arq` for broadcasts/scheduling.** Redis-native, async, no extra
broker (Celery+RabbitMQ would be overkill here). One cron job sweeps
`Broadcast.scheduled_at <= now()` every minute and enqueues sends; sends
themselves are rate-limited to stay under Telegram's ~30 msg/sec cap and
are resumable (per-recipient `BroadcastJob` rows survive a crash mid-send).

**Join-request strategy (recommendation delivered as implemented).** Each
`PrivateChannel` gets **one permanent invite link** created with
`creates_join_request=True`. When a user taps it, Telegram fires a
`ChatJoinRequest` update; `handle_join_request` re-validates every
required-channel subscription **at that exact moment** and calls
`approve_chat_join_request` / `decline_chat_join_request`. This is
superior to generating one-time links per user because:
- no link-expiry/cleanup bookkeeping,
- it closes the race where a user unsubscribes between getting the link
  in-chat and actually using it (the earlier in-bot check is UX only —
  this is the actual gate),
- it scales to arbitrarily many private-channel tiers without extra API
  calls per user.

## 2. Database schema (normalized, see `app/models/`)

| Table | Purpose |
|---|---|
| `bots` | Identity row per bot (token, username, is_master, is_active) |
| `bot_configs` | 1:1 branding + welcome + captcha config per bot |
| `users` | End-users, **scoped per bot** (`UNIQUE(bot_id, tg_id)`) — enables per-bot lead attribution for free |
| `channels` | Any news/required/forum/private channel the bot knows about |
| `private_channels` | Wraps a `channels` row of type `private`; holds the invite link |
| `channel_requirements` | M:N — which channels gate which private channel |
| `menu_buttons` | Admin-configured inline menu, ordered by `(row, position)` |
| `broadcasts` / `broadcast_jobs` | Campaign + per-recipient fan-out row (resumable, isolates per-user failures) |
| `user_subscriptions` | Durable record of the last subscription check (Redis holds the hot short-TTL cache) |
| `join_events` | Audit trail of every join-request approve/decline decision |
| `analytics_events` | Schema-light, append-only event log (`event_type` enum + JSON `meta`) — new metrics never need a migration |

All FKs cascade appropriately; every per-bot table indexes `bot_id`.

## 3. Folder structure

```
app/
  core/        # settings (pydantic-settings), logging
  db/          # async engine/session, Base, Redis client
  models/      # SQLAlchemy ORM (+ enums.py)
  repositories/# thin CRUD/query layer, no business logic
  services/    # business rules: captcha, subscriptions, private-channel
               # gating, bot orchestration, broadcast fan-out
  middlewares/ # DB session (unit of work), bot-context resolution, throttling
  keyboards/   # inline keyboard builders shared by user + admin handlers
  handlers/
    user/      # /start -> captcha -> welcome -> menu -> private channels -> join requests
    admin/     # bot mgmt, welcome/captcha/menu/channel editors, broadcast, stats
  bot/         # dispatcher factory, bot instance manager, webhook aiohttp app, arq tasks
migrations/    # Alembic (async), hand-verified initial revision
docker/        # Dockerfile + docker-compose (postgres, redis, web, worker, migrate)
```

## 4. Key design decisions / improvements over a typical "legacy" bot

- **Telegram-native HTML stored verbatim.** Admin-entered captions are
  saved via `message.html_text` (bold/italic/underline/spoiler/blockquote/
  custom-emoji entities preserved) and re-sent as-is — no lossy custom
  markup parser.
- **Per-bot-scoped users**, not a single global `users` table keyed only
  by `tg_id` — this is what makes "Bot 1 → X leads, Bot 2 → Y leads"
  trivial instead of requiring a join through some attribution table.
- **Resumable broadcasts.** A crash or Telegram 429 mid-broadcast doesn't
  lose progress or double-send; each recipient's status is tracked.
- **Bot admin verification at channel-add time.** When an admin adds a
  channel with a numeric `chat_id`, the system immediately checks the bot
  is actually an admin there and warns if not — this is the #1 cause of
  "subscription checks always fail" bugs in hand-rolled bots.
- **No hardcoded captcha/menu content anywhere in code** — fully
  data-driven per bot, editable at runtime with no redeploy.
- **Dynamic bot onboarding without redeploy.** Registering a new bot in
  the admin panel validates the token live, persists it, and calls
  `set_webhook` immediately — the bot is online in seconds.

## 5. Known limitations / things to productionize further

- Telegram formatting entities (`html_text`) do not preserve **custom
  premium emoji** perfectly across resend in all aiogram versions —
  verify against your current aiogram release when wiring this up for
  real premium-emoji use, and pin the version accordingly.
- `SubscriptionService.check_all` checks required channels sequentially
  to respect Telegram's rate limits; for private channels with many (10+)
  requirements, consider a bounded `asyncio.Semaphore` fan-out.
- The admin bot enforces a single hardcoded `ADMIN_TG_ID` per spec — add
  a proper roles table if you later need multiple admins.
- `BotManager` caches `Bot` instances in-process; if you run >1 web
  replica behind a load balancer, that's fine (each replica lazily builds
  its own instance), but make sure your LB doesn't require sticky
  sessions — it doesn't, since state lives in Postgres/Redis, not memory.

## 6. Running it

```bash
cp .env.example .env   # fill in ADMIN_TG_ID, ADMIN_BOT_TOKEN, BASE_WEBHOOK_URL, WEBHOOK_SECRET
cd docker
docker compose up --build
```

This runs, in order: `postgres`, `redis`, `migrate` (Alembic `upgrade head`,
runs once), then `web` (aiohttp webhook server) and `worker` (arq, for
scheduled/rate-limited broadcasts).

Then message your admin bot's `/start` — it self-registers on first boot
and immediately sets its own webhook. From there, use **➕ Register new
bot** to bring child bots online.
