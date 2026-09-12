# Deploying Korean Conversation Lab online

This app is a small **persistent Python server** with a **local progress file**.
That rules out Vercel/Netlify (serverless, no always-on process, no writable disk).
It runs well on any host that gives you a **long-running process** (plus a
persistent disk *if* you want progress to stick around). The app is already
prepared for this:

- It binds `0.0.0.0` and reads the host's `$PORT` automatically.
- It stores progress wherever `KCL_PROGRESS_DIR` points — set that to a mounted disk.
- It skips opening a browser when running on a server.

> **Important — it's a single-user app.** Anyone who has the URL uses the *same*
> progress. Keep the URL private. If you want a password on it, ask and I'll add a
> simple login (one env var, ~15 lines) — it won't affect phone/laptop use.

---

## Option A — Render, free tier (easiest, browser-based)  ⭐ recommended

**Cost: free.** You get an HTTPS URL that works on laptop, phone, and tablet.
Two trade-offs, both fine for casual study:

- The service **sleeps after ~15 min idle**, so the first visit after a nap takes ~30s to wake.
- There's **no persistent disk on free**, so progress is kept only in temporary
  storage — it survives while the app is awake but **resets when it sleeps or
  redeploys**. (Want it to stick forever? See "Keeping progress" below.)

1. Go to <https://dashboard.render.com> and sign up / log in (you can sign in with GitHub).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub and pick the **`valenboubee/krconvo`** repo. Render reads
   [`render.yaml`](render.yaml) and pre-fills everything (free plan, start command, env vars).
4. (Optional) change the `region` near you — edit `render.yaml`, or just pick in the UI.
5. Click **Apply** — no card needed for the free plan.
6. Wait for the first build/deploy (~1–2 min). When it's live, Render shows a URL like
   `https://krconvo.onrender.com` — open that on any device. Done.

Every future `git push` to `main` auto-redeploys.

**Keeping progress (optional, paid):** to make progress permanent, upgrade the
service to **Starter (~$7/mo)** and add a **1 GB disk mounted at `/var/data`**,
then set the env var `KCL_PROGRESS_DIR=/var/data`. That's the only difference —
the app already stores progress wherever `KCL_PROGRESS_DIR` points.

---

## Option B — Fly.io (also cheap, keeps progress, a bit more technical)

Fly runs a tiny always-on machine + a 1 GB volume for roughly **$2–3/month**
(needs a card on file). It's CLI-driven rather than point-and-click, and unlike
free Render it **keeps your progress** and doesn't sleep.

1. Install the CLI (PowerShell): `iwr https://fly.io/install.ps1 -useb | iex`
2. `fly auth signup` (or `fly auth login`).
3. In the project folder: `fly launch --no-deploy` — accept Python detection, choose a
   name and region, and say **no** to Postgres/Redis.
4. Create the volume (same region you picked): `fly volumes create data --size 1`
5. In the generated **`fly.toml`**, make sure it has:

   ```toml
   [env]
     KCL_PROGRESS_DIR = "/data"
     PORT = "8080"

   [http_service]
     internal_port = 8080
     force_https = true
     auto_stop_machines = false
     min_machines_running = 1     # keep it always on (no cold start)

   [[mounts]]
     source = "data"
     destination = "/data"
   ```
6. `fly deploy`. Open the `https://<your-app>.fly.dev` URL it prints.

---

## Option C — Don't host it; run it locally anywhere

The GitHub repo already makes it portable. On any computer with Python:

```bash
git clone https://github.com/valenboubee/krconvo.git
cd krconvo
python app.py
```

Free, fully private, and the original offline single-user design. The only
limitation is it runs on that one machine while the terminal is open.
