"""WSGI entrypoint for production servers (gunicorn/uWSGI).

Exposes ``app`` and ``application`` so either ``wsgi:app`` or ``wsgi:application``
works. Run with:

    gunicorn -c gunicorn.conf.py wsgi:app
"""

from server import app

# gunicorn/uWSGI look for ``application`` by convention.
application = app

__all__ = ["app", "application"]
