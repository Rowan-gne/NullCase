import threading
import time

from demo_service.jobs import start_cache_warmup


def test_cache_warmup_finishes_quickly():
    done = threading.Event()
    start_cache_warmup(done)
    time.sleep(0.02)
    assert done.is_set()
