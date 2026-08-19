**What does this change**

**Why**

**Testing**

- [ ] `python3 -m compileall -q reporter/app`
- [ ] `docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build` succeeds
- [ ] `./scripts/verify.sh` passes

**Checklist**

- [ ] README and `.env.example` updated if configuration changed
- [ ] `CHANGELOG.md` updated under "Unreleased"
- [ ] No secrets, API keys, or real host details in the diff
