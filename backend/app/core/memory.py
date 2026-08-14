import gc
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

PROC_STATUS_PATH = Path("/proc/self/status")


def current_rss_bytes() -> int | None:
    """Return the current resident set size in bytes, or None if unknown.

    Prefers the Linux ``/proc/self/status`` VmRSS value (authoritative and
    reflects current usage). Falls back to ``resource.getrusage`` for other
    POSIX platforms, using a size heuristic because macOS reports bytes while
    Linux reports kilobytes. Returns None when neither is available.
    """
    try:
        for line in PROC_STATUS_PATH.read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except Exception:
        pass

    try:
        import resource

        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (ImportError, AttributeError):
        return None

    if value < (1 << 31):
        return value * 1024

    return value


def format_rss(rss_bytes: int | None) -> str:
    if rss_bytes is None:
        return "unknown"
    return f"{rss_bytes / (1024 * 1024):.1f} MB"


def log_memory(context: str) -> None:
    rss = current_rss_bytes()
    if rss is not None:
        logger.info("memory %s: %s", context, format_rss(rss))


def collect_garbage() -> None:
    gc.collect()
