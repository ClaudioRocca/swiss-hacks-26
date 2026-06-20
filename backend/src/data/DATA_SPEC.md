# Mock Data Generation Spec — Private-Bank Client (post-call insights)

> Hand this whole file to a model to generate one client's mock dataset. It
> encodes the database schema **and** the generation rules. Output maps to the
> Python constants in `init_db.py`.

## Goal

Generate a coherent mock dataset for **one** wealthy private-bank client. All of a
client's data lives in **one database** (each client is generated independently).
Keep the persona internally consistent: the same tickers/sectors recur across
portfolio, trades, market data, calls, and news; values and dates tell one
believable story.

## Timeline & hard rules (follow exactly)

- Define **t = the datetime of the most recent ("last") call** = "now" for the
  dashboard. Every time series runs **up to t**.
- **`risk_profile_history`: seed the series from onboarding up to and including
  t‑1 ONLY.** Do **not** create a snapshot for the last call (t). The risk point
  at t is later *inferred by the pipeline* from the last conversation + market
  movements.
- **Last call (most recent `calls` row): leave all analysis-derived fields NULL**
  — `summary`, `sentiment_score`, `sentiment_label`, `risk_signal`, `topics`,
  `insights_json`. Provide only `transcript`, `call_date`, `customer_id`, and the
  call metadata. The pipeline computes the rest live.
- **Past calls (all except the last): fully fill** `summary`, `sentiment_score`,
  `sentiment_label`, `risk_signal`, `topics` — they represent already-processed
  history that feeds the trends.
- Make the **risk drift coherent**: past calls' `risk_signal`, the
  `risk_profile_history.risk_score` series, and sentiment should move together
  (e.g. a "moderate" client gradually expressing more conservative behavior).
- `insights_json` is **always NULL** (pipeline output cache).
- `customer_id` = **1** for the primary client (use **2** for a second client).
  One value throughout a dataset.

## Output format

Produce Python literals assigned to these constant names (JSON arrays are also
acceptable):

`CUSTOMER_PROFILE` (dict), `PORTFOLIO_POSITIONS`, `REAL_ESTATE_INVESTMENTS`,
`TRADE_OPERATIONS`, `MARKET_MOVEMENTS`, `NEWS_ARTICLES`, `CALLS`,
`RISK_PROFILE_HISTORY` (lists of dicts).

Use `None` for nulls. Do **not** include generated/auto columns
(`portfolio.profit_loss`, any autoincrement `id` except `customer_profile.id`).

---

## 1. `CUSTOMER_PROFILE` → table `customer_profile` (exactly 1 dict)

| key | type | required | constraint |
|---|---|---|---|
| `id` | int | yes | `1` (or `2` for client 2) |
| `name` | str | yes | ≤ 200 chars |
| `risk_appetite` | str | yes | one of `conservative`, `moderate`, `aggressive` |
| `investment_horizon` | str | yes | one of `short_term`, `medium_term`, `long_term` |
| `esg_preference` | str | yes | one of `none`, `moderate`, `strong` |
| `preferred_sectors` | str / None | no | **1–5** comma-separated sectors, no spaces (e.g. `"technology,healthcare,financials"`) |
| `total_aum` | float / None | no | ≥ 0 |
| `kyc_status` | str | yes | one of `verified`, `pending`, `expired` |
| `onboarding_date` | str / None | no | `"YYYY-MM-DD"` — start of the timeline |

## 2. `PORTFOLIO_POSITIONS` → table `portfolio` (≈6–10 dicts)

| key | type | required | constraint |
|---|---|---|---|
| `ticker` | str | yes | ≤ 10 chars |
| `quantity` | int | yes | ≥ 1 |
| `purchase_price` | float | yes | 0.01 … 999,999,999.99 |
| `current_price` | float | yes | 0.01 … 999,999,999.99 (should equal the ticker's value at t in `MARKET_MOVEMENTS`) |
| `currency` | str | yes | **exactly 3 chars** (e.g. `CHF`, `USD`, `EUR`) |
| `sector` | str / None | no | ≤ 50 chars |

## 3. `REAL_ESTATE_INVESTMENTS` → table `real_estate_investments` (≈3–6 dicts)

| key | type | required | constraint |
|---|---|---|---|
| `property_type` | str | yes | one of `residential`, `commercial`, `industrial`, `land` |
| `location` | str | yes | ≤ 255 chars |
| `current_value` | float | yes | 0.01 … 999,999,999.99 |
| `acquisition_price` | float | yes | 0.01 … 999,999,999.99 |
| `acquisition_date` | str | yes | `"YYYY-MM-DD"` |
| `rental_yield_percent` | float / None | no | 0.00 … 100.00 (None for `land` / non-income) |
| `status` | str | yes | one of `active`, `sold`, `under_contract` |

## 4. `TRADE_OPERATIONS` → table `trade_operations` (≈8–15 dicts)

| key | type | required | constraint |
|---|---|---|---|
| `ticker` | str | yes | ≤ 10 chars (use portfolio tickers) |
| `quantity` | int | yes | > 0 |
| `value` | float | yes | 0.01 … 999,999,999.99 |
| `operation_type` | str | yes | one of `buy`, `sell`, `short_sell`, `short_cover` |
| `timestamp` | str | yes | ISO 8601 `"YYYY-MM-DDTHH:MM:SSZ"`, ≤ t |

## 5. `MARKET_MOVEMENTS` → table `market_movements` (**time series**)

Generate a **daily series** for each portfolio ticker (plus a few extra market
names) across the trend window, ending at t — so performance/trend charts work.
Produce many dated rows (not a single-day snapshot).

| key | type | required | constraint |
|---|---|---|---|
| `ticker` | str | yes | ≤ 10 chars |
| `company_name` | str / None | no | ≤ 100 chars |
| `sector` | str / None | no | ≤ 50 chars |
| `price_change` | float | yes | day-over-day absolute change (sign = direction) |
| `percentage_change` | float | yes | day-over-day % change |
| `current_price` | float | yes | > 0 (price on that `timestamp`; value at t must match `portfolio.current_price`) |
| `volume` | int / None | no | ≥ 0 |
| `timestamp` | str | yes | ISO 8601, one per trading day up to t |

## 6. `NEWS_ARTICLES` → ChromaDB collection `market_news` (≈25–40 dicts)

Spread `published_date` across the whole window; cover the client's holdings and
`preferred_sectors`. Each dict: `{"text": str, "metadata": {...}}`.

| field | type | required | constraint |
|---|---|---|---|
| `text` | str | yes | ≤ 8000 chars, ~2–4 sentences |
| `metadata.source` | str | yes | e.g. `Reuters`, `Bloomberg`, `NZZ` |
| `metadata.category` | str | yes | one of `macro`, `equity`, `geopolitical`, `real_estate` |
| `metadata.published_date` | str | yes | `"YYYY-MM-DD"`, ≤ t |
| `metadata.tickers_mentioned` | str | yes | comma-separated tickers, `""` if none (e.g. `"AAPL,MSFT"`) |

## 7. `CALLS` → table `calls` (≈4–6 dicts, chronological; most recent = "last call")

| key | type | required | constraint / rule |
|---|---|---|---|
| `customer_id` | int | no | defaults to client id |
| `call_date` | str | **yes** | ISO 8601; the **max** `call_date` defines **t** |
| `duration_seconds` | int / None | no | ≥ 0 |
| `channel` | str / None | no | one of `phone`, `video`, `in_person` |
| `transcript` | str | **yes** | full RM↔client dialogue, grounded in this client's holdings |
| `summary` | str / None | no | **past calls: fill** · **last call: NULL** |
| `sentiment_score` | float / None | no | −1.0 … 1.0 · **past: fill · last: NULL** |
| `sentiment_label` | str / None | no | `negative` / `neutral` / `positive` · **past: fill · last: NULL** |
| `risk_signal` | str / None | no | `conservative` / `moderate` / `aggressive` · **past: fill · last: NULL** |
| `topics` | list[str] / None | no | short labels · **past: fill · last: NULL** |
| `insights_json` | — | — | **omit / NULL always** |

## 8. `RISK_PROFILE_HISTORY` → table `risk_profile_history` (onboarding → **t‑1 only**)

One point at onboarding, then points at past-call dates and/or periodic reviews —
**never at the last call (t)**. The `risk_score` series should visibly trend
(the drift).

| key | type | required | constraint |
|---|---|---|---|
| `customer_id` | int | no | defaults to client id |
| `assessed_date` | str | **yes** | `"YYYY-MM-DD"` or ISO; all **< t** |
| `risk_appetite` | str | **yes** | one of `conservative`, `moderate`, `aggressive` |
| `risk_score` | float / None | no | 1.0 … 10.0 (numeric trend line) |
| `source` | str / None | no | one of `onboarding`, `call`, `review` |
| `note` | str / None | no | short context |

---

**TL;DR for the generating model:** everything is a coherent time series up to **t**
(the last call); seed risk profiles only up to **t‑1**; and leave the last call's
`summary` / `sentiment_*` / `risk_signal` / `topics` and all `insights_json` as
`null` — the pipeline computes those.
