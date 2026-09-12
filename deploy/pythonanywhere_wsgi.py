"""
WSGI config for hosting Korean Conversation Lab on PythonAnywhere (free tier).

PythonAnywhere doesn't run `python app.py` — it imports a WSGI callable. On the
PythonAnywhere **Web** tab, click the "WSGI configuration file" link, delete
everything in that editor, paste this file's contents, change USERNAME below to
your PythonAnywhere username, Save, then click the green **Reload** button.

Progress is saved under your PythonAnywhere home (~/.korean-conversation-lab/),
which persists across reloads — no database, no paid disk.
"""
import sys

# Point this at the folder where you cloned the repo on PythonAnywhere.
PROJECT_DIR = "/home/USERNAME/krconvo"

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import application  # noqa: E402  (this is the WSGI app PythonAnywhere serves)
