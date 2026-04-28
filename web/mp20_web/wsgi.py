"""WSGI config for MP2.0."""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.mp20_web.settings")

application = get_wsgi_application()
