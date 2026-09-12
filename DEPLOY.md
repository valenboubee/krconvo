# Hosting Korean Conversation Lab

This app is a small **persistent Python server** that saves your progress to a
**file on the server**. That rules out Vercel/Netlify (serverless — no always-on
process, and their disk is read-only). You want a host that runs a real process
**and keeps your files**. The app is already prepared for this: it binds `$PORT`,
serves over WSGI, and stores progress wherever `KCL_PROGRESS_DIR` points (or, by
default, in your home folder, which most hosts keep).

> **It's a single-user app.** Anyone with the URL shares your one progress file.
> Keep the link to yourself. Want a password? Ask and I'll add one (a few lines,
> one env var — it won't get in the way of phone/laptop use).

---

## Option A — PythonAnywhere (FREE, always-on, saves progress)  ⭐ recommended

Free forever, runs even when your computer is off, and your progress is kept on
PythonAnywhere's persistent disk. Works on laptop, phone, and tablet at
`https://YOURNAME.pythonanywhere.com`.

**One-time setup (all in the browser):**

1. **Sign up** for the free **Beginner** plan at <https://www.pythonanywhere.com>.

2. **Get the code onto it.** The repo is private, so the simplest path is to make
   it public first (it has no secrets — just app code and Korean lessons):
   - Easiest: tell me and I'll flip `valenboubee/krconvo` to public for you.
   - Then, on PythonAnywhere: open a **Bash console** (Consoles tab) and run:
     ```bash
     git clone https://github.com/valenboubee/krconvo.git
     ```
   - *Prefer to keep it private?* Create a GitHub token (repo scope) and clone with
     `git clone https://TOKEN@github.com/valenboubee/krconvo.git` instead.

3. **Create the web app.** Go to the **Web** tab → **Add a new web app** →
   **Manual configuration** (not Django/Flask) → pick **Python 3.10** or newer.

4. **Wire up the app.** On the Web tab, click the **WSGI configuration file** link.
   Delete everything in that editor and paste the contents of
   [`deploy/pythonanywhere_wsgi.py`](deploy/pythonanywhere_wsgi.py). Change
   `USERNAME` to your PythonAnywhere username. **Save.**

5. *(Optional, faster)* Still on the Web tab, add a **Static files** mapping:
   URL `/static/` → Directory `/home/YOURNAME/krconvo/static`.

6. Click the big green **Reload** button. Open
   `https://YOURNAME.pythonanywhere.com` on any device. Done.

**Keep it alive:** free apps ask you to click a "Run until 3 months from now"
button every ~3 months (they email you a reminder). One click, stays free.

**Update it later** (e.g. when I add lessons): in a PythonAnywhere Bash console,
`cd krconvo && git pull`, then hit **Reload** on the Web tab.

---

## Other options

### B — Your laptop + a free private link (Tailscale)
No hosting, no code changes, fully private. Install [Tailscale](https://tailscale.com)
(free) on your laptop and your phone/tablet, run `python app.py` on the laptop, and
open its Tailscale address from the other devices. Catch: only works while your
laptop is on and running the app.

### C — Managed paid hosts (Render / Fly.io)
If you ever want zero-maintenance always-on hosting and don't mind ~$3–7/month,
[`render.yaml`](render.yaml) is a one-click Render Blueprint (with a persistent
disk), and Fly.io works too. Not needed for free use — Option A covers that.

### D — Just run it locally
On any computer with Python: `git clone` this repo and `python app.py`. Free and
fully private; runs only on that machine while the terminal is open.
