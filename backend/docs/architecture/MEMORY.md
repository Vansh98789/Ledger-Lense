# Memory & State Management

All persistent state lives in **PostgreSQL (Neon in prod / SQLite locally)** via `app/db/postgres.py`.

---

## 1. User Login Data (`users`) 

| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `email` | `String(255)` | Unique, indexed |
| `password_hash` | `Text` | bcrypt hash |
| `created_at` | `DateTime(tz)` | UTC timestamp |

---

## 2. User Documents (`documents`) 
| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `user_id` | `String(36)` FK | → `users.id` (`CASCADE`), indexed |
| `filename` | `String(255)` | Original PDF filename |
| `storage_key` | `Text` | R2 key or local path |
| `status` | `String(20)` | `QUEUED` → `EXTRACTING` → `COMPLETED` / `FAILED` |
| `error_message` | `Text` | Nullable, populated on `FAILED` |
| `created_at` | `DateTime(tz)` | UTC timestamp |

---

## 3. Chat Memory Management 

### Tables

**`chat_sessions`** — tracks summary state per conversation:
| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `user_id` | `String(36)` FK | → `users.id` (`CASCADE`), indexed |
| `summary` | `Text` | Nullable, compressed summary of older turns |
| `last_summarized_at` | `DateTime(tz)` | Nullable, marks cutoff for unsummarized messages |
| `created_at` | `DateTime(tz)` | UTC timestamp |

**`chat_messages`** — stores **all** raw messages (so the UI always has full scrollback):
| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `session_id` | `String(36)` FK | → `chat_sessions.id` (`CASCADE`), indexed |
| `user_id` | `String(36)` FK | → `users.id` (`CASCADE`), indexed |
| `role` | `String(20)` | `"user"` \| `"assistant"` |
| `content` | `Text` | Message text |
| `confidence` | `String(20)` | Nullable (`HIGH` / `MEDIUM` / `LOW` / `NOT_FOUND` / `CONVERSATIONAL`) |
| `citations` | `Text` | Nullable JSON string |
| `created_at` | `DateTime(tz)` | UTC timestamp, indexed |

---

### Runtime Flow (`POST /api/chat/`)

1. **Load context:** Fetch `session.summary` + all `chat_messages` after `session.last_summarized_at`.
2. **Gateway (`not_need_retreival`):** Decide if docs are needed using query + recent context.
3. **Query Rewrite (if docs needed):** Condense follow-ups (e.g. *"What about Q3?"* → *"What was Q3 revenue?"*) before calling `retrieve()`.
4. **Generate & Save:** Return answer, save both user + assistant messages to `chat_messages`.
5. **Background Summarization:** Run in `BackgroundTasks` (never blocks response) whenever **unsummarized messages > 5** — folds older messages into `session.summary` (keeping latest 5 exact) and updates `last_summarized_at`.

### Routes
- `GET /api/chat/history` → returns full raw `chat_messages` for UI scrollback.
- `POST /api/chat/` → uses `summary` + last 5 messages for LLM context, saves new turn.
