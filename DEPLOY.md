# Deploying Korean Conversation Lab online

This app is a small **persistent Python server** with a **local progress file**.
That rules out Vercel/Netlify (serverless, no always-on process, no writable disk).
It runs well on any host that gives you a **long-running process + a persistent
disk**. The app is already prepared for this:

- It binds `0.0.0.0` and reads the host's `$PORT` automatically.
- It stores progress wherever `KCL_PROGRESS_DIR` points — set that to a mounted disk.
- It skips opening a browser when running on a server.

> **Important — it's a single-user app.** Anyone who has the URL uses the *same*
> progress. Keep the URL private. If you want a password on it, ask and I'll add a
> simple login (one env var, ~15 lines) — it won't affect phone/laptop use.

---

## Option A — Render (easiest, browser-based)  ⭐ recommended

**Cost, honestly:** keeping your progress needs a persistent disk, and disks are
only on a **paid** instance (**Starter, ~$7/month**). Render's Free tier has no
disk and sleeps after ~15 minutes, so on Free your progress resets and the first
visit after a nap is slow. The Blueprint below asks for Starter for that reason.

1. Go to <https://dashboard.render.com> and sign up / log in (you can sign in with GitHub).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub and pick the **`valenboubee/krconvo`** repo. Render reads
   [`render.yaml`](render.yaml) and pre-fills everything (start command, disk, env vars).
4. (Optional) change the `region` near you — edit `render.yaml`, or just pick in the UI.
5. Click **Apply**. Render confirms the Starter plan (~$7/mo) because of the disk — approve it.
6. Wait for the first build/deploy (~1–2 min). When it's live, Render shows a URL like
   `https://krconvo.onrender.com` — open that on your phone or laptop. Done.

Every future `git push` to `main` auto-redeploys. Your progress lives on the
`/var/data` disk and **survives redeploys and restarts**.

---

## Option B — Fly.io (cheaper, a bit more technical)

Fly runs a tiny always-on machine + a 1 GB volume for roughly **$2–3/month**
(needs a card on file). It's CLI-driven rather than point-and-click.

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
