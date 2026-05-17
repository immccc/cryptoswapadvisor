import asyncio
import os

from saq import Queue
import structlog

from backtest.broker.actions import process_backtest_request
from runner.dependencies import register_dependencies

_COOLDOWN_TIME_BETWEEN_JOBS = 10

log = structlog.get_logger()

_queue = None

def get_broker_queue():
    global _queue
    if not _queue:
        _queue = Queue.from_url(f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT', 6379)}/15")

    return _queue

def _worker_startup(_):
    register_dependencies()
    log.info("Worker started")

def _worker_shutdown(_):
    log.info("Worker stopped")

async def _before_process(ctx):
    log.info("New job received", job_id=ctx["job"])

async def _after_process(ctx):
    log.info("Job finished", job_id=ctx["job"])
    await asyncio.sleep(_COOLDOWN_TIME_BETWEEN_JOBS)


settings = {
    "queue": get_broker_queue(),
    "functions": [process_backtest_request],
    "concurrency": 1,
    "startup": _worker_startup,
    "shutdown": _worker_shutdown,
    "before_process": _before_process,
    "after_process": _after_process,
}

if __name__ == "__main__":
    from saq import Worker
    worker = Worker(**settings)
    asyncio.run(worker.start())