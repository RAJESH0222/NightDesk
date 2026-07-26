# NIGHT DESK — going live

This package is exactly what the page's own "DATA PIPELINE" tab describes,
pulled out into real files: `index.html`, `.github/workflows/refresh.yml`,
`scripts/fetch_snapshot.py`. Nothing has been changed — this is not a rewrite,
just the code the page already shows you, made runnable.

I cannot create your GitHub repo, your Finnhub key, or your Netlify site for
you — those need your own accounts. Everything below is copy-paste.

## Steps

1. **Get a free Finnhub key** — finnhub.io → sign up → dashboard → copy the API key.
2. **Create a new GitHub repo** (see cost note below on public vs private), push these
   three files/folders to it as-is: `index.html`, `.github/`, `scripts/`.
3. **Add the secret** — repo → Settings → Secrets and variables → Actions →
   New repository secret → name it exactly `FINNHUB_KEY` → paste the key.
4. **Trigger the first run manually** — repo → Actions tab → "refresh-snapshot" →
   Run workflow (this uses the `workflow_dispatch` trigger already in the
   YAML, so you don't have to wait for the next cron tick). This creates
   `data/snapshot.json` and commits it.
5. **Connect the repo to Netlify** — same flow you've already used for your
   other sites (New site from Git → pick the repo → no build command needed,
   publish directory `/`).
6. Reload the live URL. The "DATA SNAPSHOT" badge in the header should flip
   from `EMBEDDED SAMPLE FEED` to `LIVE · data/snapshot.json`.

## Three things worth knowing before you flip this on

**1. The page's own "FREE · 2,000 MIN/MO" claim doesn't hold on a private repo.**
The cron fires 32 times in the NSE/BSE window, 32 times in the US window, and
once daily = 65 runs/weekday ≈ 1,410 runs/month. `pip install yfinance` plus
looping 26 symbols with the deliberate rate-limit sleeps realistically takes
1.5–2.5 minutes per run, not under 1. That's **~2,100–3,500 Actions minutes/month**
against a **2,000/month free cap — but only on private repos.** Public repos get
unlimited free minutes on standard GitHub-hosted runners. Fix: make the repo
public. Nothing sensitive lives in it — `FINNHUB_KEY` stays a masked secret,
never printed or committed.

**2. yfinance hits Yahoo's unofficial endpoint from a shared GitHub Actions IP range.**
Yahoo is known to rate-limit or 429 datacenter/cloud IP ranges more
aggressively than home connections, precisely because tools like yfinance
share runner IPs with thousands of other repos doing the same thing. This can
start failing weeks after you set it up with zero code changes on your end —
worth spot-checking the Actions run logs occasionally, not just trusting a
green checkmark.

**3. If you connect the repo to Netlify via Git, every 15-minute snapshot commit
triggers a Netlify deploy.** At ~1,400 commits/month that's a lot of deploys
for a page that never actually changes — only its data does. **This is now
fixed in `index.html`** — `loadSnapshot()` fetches directly from
`https://raw.githubusercontent.com/RAJESH0222/NightDesk/main/data/snapshot.json`
with a cache-busting query param, instead of a same-origin path. Netlify now
only redeploys when you actually change `index.html`, never on data commits.

I originally suggested the jsDelivr GitHub CDN mirror instead — walking that
back: jsDelivr caches GitHub content at its edge for hours, which would
silently defeat a 15-minute refresh cycle (you'd see a stale badge saying
"LIVE" while showing hours-old numbers). `raw.githubusercontent.com` has a
much shorter edge-cache window and sends proper CORS headers for browser
`fetch()`, so it's the correct choice here despite being the less exotic
option. The `?v=<minute-bucket>` query param on each request additionally
busts any caching layer regardless of provider.

**If you ever rename the repo, or push to a branch other than `main`, this
URL breaks silently** — the page just falls back to `EMBEDDED SAMPLE FEED`
with no error shown. Update the `SNAPSHOT_URL` constant in `loadSnapshot()`
if that happens.

## What "live" actually means here

Prices are still snapshot-based, refreshed every 15–20 minutes during market
hours — not real-time streaming, and the page is explicit about that. Between
snapshots the frontend fakes small price drift locally (clearly labeled "SIM
DRIFT" in the toolbar) so it doesn't look frozen. That's by design, not a bug
to fix.
