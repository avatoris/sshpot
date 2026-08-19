import json
import logging

from .tailer import LogTailer

logger = logging.getLogger("reporter.cowrie")

INTERESTING_EVENTS = {"cowrie.login.failed", "cowrie.login.success"}


async def watch_cowrie(path: str, poll_interval: float, queue) -> None:
    logger.info("watching cowrie JSON log at %s", path)
    async for line in LogTailer(path, poll_interval=poll_interval, from_end=True).lines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("eventid") not in INTERESTING_EVENTS:
            continue
        ip = event.get("src_ip")
        if not ip:
            continue
        outcome = "success" if event["eventid"] == "cowrie.login.success" else "failed"
        await queue.put(
            {
                "ip": ip,
                "category": "ssh_bruteforce",
                "username": event.get("username"),
                "source": "honeypot",
                "outcome": outcome,
            }
        )
