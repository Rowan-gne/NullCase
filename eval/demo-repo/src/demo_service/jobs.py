"""Background jobs."""

import random
import threading
import time

_jitter = random.SystemRandom()


def start_cache_warmup(done: threading.Event) -> None:
    """Warm the cache on a background thread; sets ``done`` when finished."""

    def warm() -> None:
        time.sleep(_jitter.uniform(0.005, 0.03))  # variable I/O latency
        done.set()

    threading.Thread(target=warm, daemon=True).start()
