"""Saves each uploaded team CSV and its scores to a Cloud Storage bucket.

On Cloud Run the bucket is mounted as a folder (a volume), by default at /mnt/data,
so saving a file there is a normal file write and the file stays after the app stops.
If the folder does not exist (for example on a laptop), saving is simply switched off.
"""
import csv
import io
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

from app import config

IST = timezone(timedelta(hours=5, minutes=30), "IST")
PREFIX = "team-"
NAME = re.compile(r"^team-\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_[0-9a-f]{4}_(original|scored)\.csv$")
SCORED_COLUMNS = ["employee_id", "department", "risk_percent", "band", "top_driver"]

log = logging.getLogger("attrition.storage")


def enabled():
    return config.DATA_DIR.is_dir()


def save(raw, results):
    """Writes the original upload and the scored table. Never raises: scoring must work even if saving fails."""
    if not enabled():
        return {"saved": False, "files": [], "message": "Storage is not connected, so nothing was saved."}
    base = "%s%s_%s" % (PREFIX, datetime.now(IST).strftime("%Y-%m-%d_%H-%M-%S"), secrets.token_hex(2))
    original, scored = base + "_original.csv", base + "_scored.csv"
    table = io.StringIO()
    writer = csv.DictWriter(table, fieldnames=SCORED_COLUMNS)
    writer.writeheader()
    writer.writerows(results)
    try:
        (config.DATA_DIR / original).write_bytes(raw)
        (config.DATA_DIR / scored).write_text(table.getvalue(), encoding="utf-8")
    except OSError as error:
        log.warning("saving to %s failed: %s", config.DATA_DIR, error)
        return {"saved": False, "files": [], "message": "Could not save to storage. Check the bucket permission."}
    log.info("saved %s and %s", original, scored)
    return {"saved": True, "files": [original, scored], "message": "Saved to Cloud Storage."}


def recent(limit=10):
    """Newest saved files first (names start with the date and time, so sorting by name is enough)."""
    if not enabled():
        return []
    try:
        names = sorted((p.name for p in config.DATA_DIR.iterdir() if NAME.match(p.name)), reverse=True)[:limit]
        return [{"name": n, "kb": round((config.DATA_DIR / n).stat().st_size / 1024, 1)} for n in names]
    except OSError as error:
        log.warning("listing %s failed: %s", config.DATA_DIR, error)
        return []
