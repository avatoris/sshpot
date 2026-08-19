import os
from dataclasses import dataclass

# Fixed endpoint of the Avatoris API.
API_BASE = "https://avatoris.com/api/v1"


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    api_key: str = os.environ.get("AVATORIS_API_KEY", "")
    cowrie_json_path: str = os.environ.get(
        "COWRIE_JSON_PATH", "/data/cowrie_var/log/cowrie/cowrie.json"
    )
    auth_log_path: str = os.environ.get("AUTH_LOG_PATH", "/data/auth.log")
    state_db_path: str = os.environ.get("STATE_DB_PATH", "/data/state/reporter.db")
    report_window_seconds: int = int(os.environ.get("REPORT_WINDOW_SECONDS", "1800"))
    reports_per_minute: int = int(os.environ.get("REPORTS_PER_MINUTE", "25"))
    flush_interval_seconds: int = int(os.environ.get("FLUSH_INTERVAL_SECONDS", "60"))
    poll_interval_seconds: float = float(os.environ.get("POLL_INTERVAL_SECONDS", "1.0"))
    watch_honeypot: bool = _bool("ENABLE_HONEYPOT_WATCH", True)
    watch_host_sshd: bool = _bool("ENABLE_HOST_SSHD_WATCH", True)

    def validate(self) -> None:
        if not self.api_key:
            raise ValueError("AVATORIS_API_KEY is not set")
        if not self.watch_honeypot and not self.watch_host_sshd:
            raise ValueError("both ENABLE_HONEYPOT_WATCH and ENABLE_HOST_SSHD_WATCH are false")


CONFIG = Config()
