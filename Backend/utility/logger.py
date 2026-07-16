import sys
from datetime import datetime


def log(*args, sep=" ", end="\n", file=None):
    """
    Print with a UTC timestamp prefix.
    Usage: log("Starting consumer for video", video_id)
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    message = sep.join(str(a) for a in args)
    print(f"[{timestamp}] {message}", end=end, file=file or sys.stdout)