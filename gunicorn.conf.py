"""Gunicorn configuration for LabsManager   ."""

import logging
import multiprocessing
import os

logger = logging.getLogger('labsmanager')

workers = os.environ.get('LABSMANAGER_GUNICORN_WORKERS', None)

if workers is not None:
    try:
        workers = int(workers)
    except ValueError:
        workers = None

if workers is None:
    workers = multiprocessing.cpu_count() * 2 + 1

logger.info(f"Starting gunicorn server with {workers} workers")

max_requests = 1000
max_requests_jitter = 50