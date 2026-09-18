"""Gunicorn config - production settings"""
import os
import sys

# Fixed absolute path - gunicorn daemon mode changes cwd to /
basedir = "/root/.openclaw/workspace/prosecution_system"
os.chdir(basedir)
sys.path.insert(0, basedir)

bind = "0.0.0.0:5001"
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
