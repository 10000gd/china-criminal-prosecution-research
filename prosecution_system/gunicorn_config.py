"""Gunicorn config - production settings"""
import os

bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
# Workers manage their own LawRAG singleton lazily on first use.
# First request to each worker is slow (LawRAG init ~2s), subsequent requests are fast (<500ms).
preload_app = False
