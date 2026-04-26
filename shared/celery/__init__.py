"""Celery application setup for async task processing.

Used by the risk service for long-running AI workflows that shouldn't block
HTTP requests. The same app instance can be imported by both the API service
(to enqueue tasks) and the worker process (to execute them).
"""
