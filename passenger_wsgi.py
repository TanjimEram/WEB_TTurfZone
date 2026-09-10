"""Entry point for cPanel "Setup Python App" (Passenger).

In cPanel set:  Application startup file = passenger_wsgi.py,  Entry point = application
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app  # noqa: E402

application = create_app()
