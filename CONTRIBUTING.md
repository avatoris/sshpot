# Contributing

Thanks for taking the time to contribute.

## Reporting bugs and requesting features

Open an issue and include your OS/distribution, Docker version, and the relevant
`docker compose logs -f reporter` output. Redact your API key and any host details
you do not want public.

Do **not** open a public issue for security vulnerabilities — see [SECURITY.md](SECURITY.md).

## Development setup

```bash
git clone <your-fork>
cd sshpot
cp .env.example .env      # set AVATORIS_API_KEY
./scripts/vendor_cowrie.sh
./scripts/preflight.sh
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

The plain `docker-compose.yml` pulls published images from Docker Hub; the
`build.yml` override builds them from your checkout under the same names.

The reporter is a small asyncio service under [`reporter/app/`](reporter/app/).
Cowrie itself is vendored into `vendor/` by the script and is not part of this
repository.

## Pull requests

* Keep changes focused — one topic per PR.
* Match the existing style: standard library first, type hints on function
  signatures, no new runtime dependencies unless there is a good reason.
* Verify the pipeline still works end to end before submitting:

  ```bash
  python3 -m compileall -q reporter/app
  docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
  ./scripts/verify.sh
  ```

* Update the README and `.env.example` when you add or remove configuration.
* Add a line to [CHANGELOG.md](CHANGELOG.md) under "Unreleased".

## Scope

This project is a thin, defensive integration between Cowrie and Avatoris.
Features that turn it into an offensive tool, or that transmit passwords or
payload contents to third parties, are out of scope.

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
