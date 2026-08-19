# avatoris-sshpot

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker Hub](https://img.shields.io/docker/v/jnltedev/avatoris_sshpot-reporter?label=docker%20hub&sort=semver)](https://hub.docker.com/r/jnltedev/avatoris_sshpot-reporter)
[![Cowrie](https://img.shields.io/badge/honeypot-Cowrie-informational)](https://github.com/cowrie/cowrie)

SSH honeypot based on [Cowrie](https://github.com/cowrie/cowrie) with automatic reporting of failed login attempts to [Avatoris](https://avatoris.com/api).

The project can monitor both:

* the fake SSH service provided by Cowrie
* the real host `sshd` authentication log (optional)

Failed login attempts are automatically deduplicated per source IP according to the Avatoris reporting limit. Passwords are **never transmitted to Avatoris**.

## Architecture

```text
docker-compose.yml
├── cowrie
│   └── Fake SSH server (Cowrie, pinned release, locally vendored and patched)
│       └── Port 2222 inside the container
│
└── reporter
    └── Custom Python service
        ├── Tails Cowrie's JSON log
        │   ├── cowrie.login.failed
        │   └── cowrie.login.success
        │
        ├── Optionally tails the host's /var/log/auth.log
        │
        ├── Deduplicates reports per source IP
        │
        ├── Stores local counters and usernames in SQLite
        │
        └── Reports to:
            POST https://avatoris.com/api/v1/report
```

The honeypot is intended to be exposed as a real SSH service, typically on TCP port `22`, while the host's actual SSH daemon can be moved to another port.

## Reporting Behavior

The reporter follows a simple rate-limiting and aggregation strategy.

### First attempt

The **first failed login attempt from an IP address** is reported to Avatoris immediately.

### Subsequent attempts

Additional attempts from the same IP during Avatoris' 30-minute reporting window are **not sent individually**.

Instead, the reporter:

1. stores the attempts locally in SQLite
2. counts the additional attempts
3. records the observed usernames
4. waits for the reporting window to expire
5. sends an aggregated follow-up report

This prevents unnecessary duplicate API requests while preserving useful attack telemetry.

### Password privacy

Passwords are never sent to Avatoris.

Only relevant metadata is reported, including:

* source IP address
* timestamp
* category
* attempt count
* observed usernames

## Requirements

* Docker with the Compose v2 plugin
* An Avatoris API key
* A publicly reachable TCP port for the honeypot

Nothing else — the images are prebuilt and pulled from Docker Hub. A local
clone, a Python toolchain, or a build step are only needed if you want to
change the code (see [Building from source](#building-from-source)).

The images are published for `linux/amd64` and `linux/arm64`:

* [`jnltedev/avatoris_sshpot-cowrie`](https://hub.docker.com/r/jnltedev/avatoris_sshpot-cowrie)
* [`jnltedev/avatoris_sshpot-reporter`](https://hub.docker.com/r/jnltedev/avatoris_sshpot-reporter)

Monitoring the host's real `sshd` additionally requires a Linux host and
read access to its authentication log.

## Quick start

Get a free API key at https://avatoris.com/login, then:

```bash
curl -O https://raw.githubusercontent.com/avatoris/sshpot/main/docker-compose.yml
AVATORIS_API_KEY=your-key docker compose up -d
docker compose logs -f reporter
```

That is the whole setup. The honeypot listens on port `22` by default, so on a
host with a real SSH daemon either move that daemon away from `22` first (see
[Using port 22](#using-port-22)) or pick another port:

```bash
AVATORIS_API_KEY=your-key HONEYPOT_PUBLIC_PORT=2222 docker compose up -d
```

Test it from another machine, using any password:

```bash
ssh -p 2222 test@YOUR_SERVER_IP
```

The login fails, and the reporter log shows the report going out.

Keeping the settings in a `.env` file next to `docker-compose.yml` is more
comfortable than repeating them on every command — Compose picks that file up
automatically:

```bash
echo "AVATORIS_API_KEY=your-key" > .env
docker compose up -d
```

### Configuration

Every setting is an environment variable. Pass it inline, export it, or put it
in `.env` — all three work. Only `AVATORIS_API_KEY` has no default.

| Variable | Default | Purpose |
| --- | --- | --- |
| `AVATORIS_API_KEY` | *(required)* | Your Avatoris API key |
| `HONEYPOT_PUBLIC_PORT` | `22` | Public port of the decoy SSH service |
| `HONEYPOT_HOSTNAME` | `prod-db-02` | Hostname the fake shell presents to attackers |
| `SSHPOT_TAG` | `latest` | Image tag to run, e.g. a pinned release |
| `ENABLE_HONEYPOT_WATCH` | `true` | Report failed logins seen by Cowrie |
| `ENABLE_HOST_SSHD_WATCH` | `false` | Also report failed logins against the real host `sshd` |
| `HOST_AUTH_LOG_PATH` | `/dev/null` | Host auth log to watch when the above is enabled |
| `GROUP_ADD_GID` | `4` | Host group that may read that log (`adm` on Debian/Ubuntu) |
| `REPORT_WINDOW_SECONDS` | `1800` | Avatoris deduplication window |
| `REPORTS_PER_MINUTE` | `25` | Client-side rate limit |
| `FLUSH_INTERVAL_SECONDS` | `60` | How often aggregated counts are flushed |

### Watching the real host sshd

This is optional and Linux-only. Point the reporter at the host's auth log —
`/var/log/auth.log` on Debian/Ubuntu, `/var/log/secure` on RHEL/Fedora — and
give it a group that may read it:

```bash
ENABLE_HOST_SSHD_WATCH=true \
HOST_AUTH_LOG_PATH=/var/log/auth.log \
GROUP_ADD_GID=$(getent group adm | cut -d: -f3) \
docker compose up -d
```

The log is mounted read-only and the reporter runs as an unprivileged user.

## Using port 22

The honeypot is most convincing on the standard SSH port. If the host runs a
real SSH daemon there, move it first:

```bash
sudo sed -i 's/^#\?Port .*/Port 2200/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

**Do not close your current SSH session until you have confirmed the new port
works** from a second terminal:

```bash
ssh -p 2200 root@YOUR_SERVER_IP
```

### Systems using systemd socket activation

Some distributions activate SSH through `ssh.socket`. If

```bash
systemctl cat ssh.socket
```

contains `ListenStream=22`, that socket has to be changed as well:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ssh.socket
```

Confirm port `22` is free before starting the honeypot:

```bash
ss -lntp | grep -E ':(22|2200)\b'
```

## Building from source

Only needed to change the code or to vendor a different Cowrie release.

```bash
git clone https://github.com/avatoris/sshpot.git
cd sshpot
./scripts/vendor_cowrie.sh
./scripts/preflight.sh
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

Cowrie is vendored into `vendor/` from a pinned release (`COWRIE_TAG`, default
`v3.0.12`) and its `docker/Dockerfile` is replaced with the patched copy in
`patches/cowrie-Dockerfile`. Re-run `./scripts/vendor_cowrie.sh` after changing
the tag or pulling repository changes.

### Why is Cowrie patched?

Upstream's Dockerfile has the `pip install -e .` step commented out, so the
package version file is never generated and the container crash-loops with:

```text
Cowrie is not installed. Run 'pip install -e .'
```

The patched Dockerfile installs the source while pip is still present. The
issue is present in at least `v2.9.10` through `v3.0.12`.

### Publishing images

Tagging a release (`v1.2.3`) triggers `.github/workflows/publish.yml`, which
vendors Cowrie and pushes both images to Docker Hub. It needs the repository
secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.


## Verification

Trigger a failed login against the honeypot from another machine and watch it
travel through the pipeline:

```bash
ssh -p 22 test@YOUR_SERVER_IP        # any password
docker compose logs --tail=20 reporter
```

A line like `reported <ip> categories=[...]` confirms the report was accepted.

From a source checkout, `./scripts/verify.sh` automates the same check (it
needs `sshpass`). Note that `127.0.0.1` is not a great end-to-end test target,
because reputation services commonly ignore loopback and private addresses.

However, the local pipeline can still be fully tested:

```text
Cowrie
  ↓
JSON log
  ↓
Reporter
  ↓
Avatoris API
```

### Testing deduplication

Repeat a failed login from the same source IP within the 30-minute reporting window.

The reporter should **not** send another individual report for that IP.

Instead, the additional attempt should only be recorded locally.

After the reporting window expires, the aggregated report is sent with the accumulated attempt count and observed usernames.

## Operations

### View logs

Reporter:

```bash
docker compose logs -f reporter
```

Cowrie:

```bash
docker compose logs -f cowrie
```

All services:

```bash
docker compose logs -f
```

### Update

Pull the current images and restart:

```bash
docker compose pull
docker compose up -d
```

To pin a specific release instead of tracking `latest`, set `SSHPOT_TAG`, for
example `SSHPOT_TAG=1.2.3`.

From a source checkout, changing `COWRIE_TAG` additionally requires re-running
`./scripts/vendor_cowrie.sh` before rebuilding.

### Log rotation

Docker's default `json-file` logging configuration may allow container logs to grow indefinitely.

For long-running deployments, consider configuring log rotation for each service:

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

### Configure reporting behavior

Reporting window, flush interval, rate limiting and the enabled log sources are
all environment variables — see [Configuration](#configuration).

The wording of the reports themselves is generated in:

```text
reporter/app/main.py
```

Specifically:

```text
build_comment
```

## Security

Security is an important part of the honeypot design.

### Cowrie

The Cowrie container runs with:

* `cap_drop: ALL`
* `read_only: true`
* `no-new-privileges`
* non-root user

These settings reduce the potential impact of a compromised honeypot container.

### Reporter

The reporter container also runs with:

* `cap_drop: ALL`
* `no-new-privileges`
* non-root user
* dedicated UID `10001`

The reporter reads the host authentication log through the `adm` group and does not require root privileges.

### API key

The `AVATORIS_API_KEY` is stored only in `.env`.

The file is excluded through `.gitignore`.

The API key is never written to application logs or included in reports.

### Reported data

The reporter sends only relevant attack metadata:

* source IP
* timestamp
* category
* attempt count
* usernames

**Passwords are never transmitted to Avatoris.**

## Known Limitations

### Log tailing starts at EOF

After a reporter restart, log tailing starts at the end of the current log file.

Historical entries are intentionally not processed.

This prevents a restart from replaying an entire historical log and incorrectly treating old attempts as new first-time attacks.

### Aggregated report timing

Aggregated reports may occasionally be delayed by up to one `FLUSH_INTERVAL_SECONDS` period.

This is a timing limitation rather than data loss.

The locally recorded attempts remain available in SQLite until they are processed.

### Host SSH monitoring

Host `sshd` monitoring depends on the host's authentication log being available at the expected path and readable by the reporter.

Log locations and permissions can differ between Linux distributions.

## Project Structure

```text
.
├── docker-compose.yml        # the only file end users need
├── docker-compose.build.yml  # contributor override: build instead of pull
├── .env.example
├── cowrie/
│   └── cowrie.cfg            # config overlay used by local builds
├── patches/
│   └── cowrie-Dockerfile     # upstream Dockerfile with the install fix
├── reporter/
│   └── app/                  # asyncio reporter service
│       └── main.py
├── scripts/
│   ├── preflight.sh
│   ├── verify.sh
│   └── vendor_cowrie.sh
└── vendor/                   # Cowrie source, fetched on demand (not committed)
    └── cowrie/
```

## Disclaimer

This project is intended for defensive security research, threat intelligence, and honeypot deployments.

Only deploy the honeypot on infrastructure you own or are explicitly authorized to operate.

A honeypot exposed to the public Internet should be treated as an intentionally exposed security research system and should be isolated from sensitive infrastructure.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the
development setup and pull request expectations, and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community guidelines.

Notable changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## Security

Please report vulnerabilities privately rather than through a public issue.
See [SECURITY.md](SECURITY.md).

## Credits

* [Cowrie](https://github.com/cowrie/cowrie) — the honeypot engine, by Michel
  Oosterhof and contributors, BSD 3-Clause licensed. It is fetched at build time
  and is not redistributed as part of this repository.
* [Avatoris](https://avatoris.com) — the threat intelligence API this project
  reports to.

## License

[MIT](LICENSE) © 2026 Justin Nolte

Cowrie is licensed separately under BSD 3-Clause; its license applies to the
vendored source under `vendor/cowrie/`.
