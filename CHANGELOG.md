# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

* The Avatoris API base URL is now a fixed constant instead of a configurable
  environment variable.
* Log level is fixed at `INFO`; the `LOG_LEVEL` variable was removed.
* `docker-compose.yml` now pulls published images and configures everything
  through environment variables with defaults; a `.env` file is optional and
  only `AVATORIS_API_KEY` is required.
* The Cowrie hostname is set via `HONEYPOT_HOSTNAME` (passed through as
  `COWRIE_HONEYPOT_HOSTNAME`) instead of a mounted `cowrie.cfg`.
* Host `sshd` watching is off by default and its log mount defaults to
  `/dev/null`, so the stack starts on any host including macOS.
* A missing or invalid configuration now logs a single clear error instead of
  a traceback.

### Added

* Prebuilt images on Docker Hub (`jnltedev/avatoris_sshpot-cowrie` and
  `jnltedev/avatoris_sshpot-reporter`), published by a GitHub Actions workflow
  on release tags. Running the stack no longer requires a clone or a build.
* `docker-compose.build.yml` override for contributors who want to build the
  images locally.
* Open source project files: license, contributing guide, security policy,
  code of conduct, and issue/pull request templates.

## [0.1.0]

### Added

* Cowrie honeypot with a pinned, locally vendored and patched release.
* Reporter service that tails Cowrie's JSON log and, optionally, the host
  `sshd` authentication log.
* Per-IP deduplication and aggregation matching the Avatoris 30-minute
  reporting window, with SQLite-backed state.
* Helper scripts: `preflight.sh`, `verify.sh`, `vendor_cowrie.sh`.
