import logging
import re

from .tailer import LogTailer

logger = logging.getLogger("reporter.authlog")

FAILED_PASSWORD_RE = re.compile(
    r"Failed password for (?:invalid user )?(?P<user>\S+) from (?P<ip>[0-9a-fA-F:.]+) port \d+"
)
INVALID_USER_RE = re.compile(r"Invalid user (?P<user>\S+) from (?P<ip>[0-9a-fA-F:.]+) port \d+")


async def watch_authlog(path: str, poll_interval: float, queue) -> None:
    logger.info("watching host auth log at %s", path)
    async for line in LogTailer(path, poll_interval=poll_interval, from_end=True).lines():
        if "sshd" not in line:
            continue
        match = FAILED_PASSWORD_RE.search(line) or INVALID_USER_RE.search(line)
        if not match:
            continue
        await queue.put(
            {
                "ip": match.group("ip"),
                "category": "ssh_bruteforce",
                "username": match.group("user"),
                "source": "production sshd",
                "outcome": "failed",
            }
        )
