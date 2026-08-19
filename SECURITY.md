# Security Policy

## Supported versions

Only the latest commit on `main` is supported. Please reproduce issues against
`main` before reporting.

## Reporting a vulnerability

Do **not** open a public issue for security vulnerabilities.

Report privately via GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
(Security → Report a vulnerability) or by email to `justin@jnlte.de`.

Please include a description of the issue, steps to reproduce, and the impact you
expect. You can expect an initial response within 7 days.

## Scope

In scope: the reporter service, the container configuration in
`docker-compose.yml`, the patched Cowrie Dockerfile, and the helper scripts.

Out of scope: vulnerabilities in [Cowrie](https://github.com/cowrie/cowrie)
itself (report those upstream) and in the Avatoris API.

## Operating this honeypot safely

A honeypot is an intentionally exposed system. Run it only on infrastructure you
own or are authorized to operate, keep it isolated from anything sensitive, and
never reuse real credentials or hostnames in its configuration.
