import asyncio
import json
import logging
import signal
import sys

from .authlog_watcher import watch_authlog
from .avatoris_client import AvatorisClient
from .config import CONFIG
from .cowrie_watcher import watch_cowrie
from .dedup_store import DedupStore
from .rate_limiter import TokenBucketLimiter

logger = logging.getLogger("reporter")


def build_comment(source: str, outcome: str, usernames: list[str], extra: str = "") -> str:
    users = ", ".join(usernames[:5]) if usernames else "unknown"
    if outcome == "success":
        verb = "successful login on a decoy honeypot (treat as compromise attempt)"
    else:
        verb = "failed login attempt(s)"
    comment = f"SSH {verb} on {source}; usernames observed: {users}{extra}"
    return comment[:500]


async def event_consumer(queue: asyncio.Queue, store: DedupStore, client: AvatorisClient, window_seconds: int):
    while True:
        event = await queue.get()
        try:
            should_report, usernames = await store.register_attempt(
                event["ip"], event["category"], event.get("username"), window_seconds
            )
            if should_report:
                comment = build_comment(event["source"], event["outcome"], usernames)
                asyncio.create_task(client.report(event["ip"], [event["category"]], comment))
            else:
                logger.debug("suppressed duplicate report for %s within window", event["ip"])
        except Exception:
            logger.exception("failed to process event %s", event)
        finally:
            queue.task_done()


async def flush_loop(store: DedupStore, client: AvatorisClient, window_seconds: int, interval: int):
    while True:
        await asyncio.sleep(interval)
        try:
            candidates = await store.flush_candidates(window_seconds)
        except Exception:
            logger.exception("flush_candidates failed")
            continue
        for ip, category, pending_count, usernames_json in candidates:
            usernames = json.loads(usernames_json)
            extra = f"; {pending_count} additional attempt(s) since last report"
            comment = build_comment("aggregated window", "failed", usernames, extra)
            if await client.report(ip, [category], comment):
                await store.mark_flushed(ip, category)


async def main():
    logging.basicConfig(
        level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    CONFIG.validate()

    store = DedupStore(CONFIG.state_db_path)
    limiter = TokenBucketLimiter(CONFIG.reports_per_minute)
    client = AvatorisClient(CONFIG.api_key, limiter)
    queue: asyncio.Queue = asyncio.Queue()

    tasks = [
        asyncio.create_task(event_consumer(queue, store, client, CONFIG.report_window_seconds)),
        asyncio.create_task(
            flush_loop(store, client, CONFIG.report_window_seconds, CONFIG.flush_interval_seconds)
        ),
    ]
    if CONFIG.watch_honeypot:
        tasks.append(
            asyncio.create_task(
                watch_cowrie(CONFIG.cowrie_json_path, CONFIG.poll_interval_seconds, queue)
            )
        )
    if CONFIG.watch_host_sshd:
        tasks.append(
            asyncio.create_task(
                watch_authlog(CONFIG.auth_log_path, CONFIG.poll_interval_seconds, queue)
            )
        )

    logger.info(
        "reporter started (window=%ss, rate=%s/min, honeypot=%s, host_sshd=%s)",
        CONFIG.report_window_seconds,
        CONFIG.reports_per_minute,
        CONFIG.watch_honeypot,
        CONFIG.watch_host_sshd,
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()
    logger.info("shutting down")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValueError as exc:
        # Misconfiguration, not a crash: keep the container log readable
        # instead of dumping a traceback on every restart.
        logging.basicConfig(level="INFO", format="%(levelname)s: %(message)s")
        logger.error("configuration error: %s", exc)
        sys.exit(1)
