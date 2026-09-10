"""Run the app the way cPanel's Passenger does: import passenger_wsgi.application.

Uses Python's built-in WSGI server, so no extra packages are needed.

    APP_ENV=production SECRET_KEY=... DATABASE_URL=... python scripts/serve_like_passenger.py

Then open http://127.0.0.1:8000/healthz
"""
import os
import sys
from pathlib import Path
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # Passenger runs from the app root

from passenger_wsgi import application  # noqa: E402

port = int(os.environ.get("PORT", "8000"))
print(f"APP_ENV={os.environ.get('APP_ENV', 'development')}  serving on http://127.0.0.1:{port}  (Ctrl+C to stop)")
with make_server("127.0.0.1", port, application) as server:
    server.serve_forever()
