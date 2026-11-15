---
name: dev-prod-handoff
description: "Use when work is split across a development machine and a production machine: one agent writes code and pushes branches while a different agent reviews, merges and deploys. Holds the role contract, the task brief the dev receives, the report it must return, the project registry that tells prod what is being built, and the rules that keep the two from colliding."
requires: git
needs_tools: exec, read, write, edit, glob, grep
author: Becik
---

# Handing work between a dev machine and a production machine

Two machines, two agents, one repository. The dev machine is where code is written and built. The production
machine is where it runs. The failure this skill prevents is the ordinary one: the dev agent deploys because it
can, the prod agent merges without reading, and nobody can say afterwards which commit is live.

The split only works if both sides keep one rule: **the dev never deploys, the prod never writes application
code.** Everything below follows from that.

## The two roles

**Dev agent** — writes code, Dockerfile, CI workflow, tests. Pushes branches. Runs builds locally. Never touches
production, never holds production credentials, never merges to the deploy branch.

**Prod agent** — reads the diff, merges to the deploy branch, brings the stack up, verifies the result over HTTP.
Does not write application code: if the code is wrong, it goes back to the dev with a reason, because a prod agent
editing code means nobody reviewed it.

**The person** — owns the repository and decides what is built. Where the two agents cannot reach each other (no
shared daemon, no network path), the person relays briefs and reports. Say so plainly rather than pretending a
delegation happened.

## Hard rules

1. **The dev pushes to `feat/<topic>` or `dev`, never to `main`.** `main` is the deploy branch and belongs to prod.
2. **No secret ever enters the repository.** `.env` in `.gitignore` before the first commit. A public repository
   makes one leaked key irreversible; removing it from history does not undo the exposure.
3. **Images are built by CI, never on a server.** Building on the production machine puts a compiler and its RAM
   pressure on the machine serving users, and makes the running version unreproducible.
4. **The app listens on `0.0.0.0`**, not `127.0.0.1`, or the reverse proxy in another container cannot reach it.
5. **The container runs as non-root** (`USER` in the Dockerfile).
6. **`GET /health` returns 200 without authentication.** This is what the deploy verifies; without it "deployed"
   means "a container started", which is not the same thing.
7. **Pin the image by commit SHA.** `latest` makes rollback impossible, because nobody knows what was running before.

## What every project repository must contain

```
Dockerfile                     multi-stage, USER non-root, HEALTHCHECK hitting /health
.dockerignore                  .git, .env, node_modules, __pycache__, *.bak-*
.github/workflows/deploy.yml   build + push to the registry, tagged with the commit SHA
README.md                      how to run locally, how to test
```

The workflow builds and pushes; it does not deploy. Deployment is the prod side's job, and keeping the two apart
means a broken build never reaches a server.

## The task brief

Prod writes the brief; the dev receives it. Use `templates/task-brief.md`. It has five parts and all five matter:
what the task is, why it exists, the concrete steps, the boundaries (which files not to touch, which branch), and
the acceptance criteria. Acceptance criteria must be checkable — "works well" is not one, "`GET /health` returns
200" is.

A brief without boundaries gets a diff that touches everything. A brief without checkable criteria cannot be
rejected, only argued about.

## The report the dev must return

Fixed format, every time, from `templates/report.md`:

```
repo:      <owner/name>
branch:    feat/<topic>
commit:    <full 40-character sha>
changes:   <files created or modified, one per line>
build:     <pass/fail + the command used>
test:      <counts, or "none">
port:      <port the app listens on>
health:    <health endpoint path>
risk:      <db migration? new env var? port change? or "none">
pending:   <deliberately not done, or "none">
```

Validate it with `scripts/check-report.py` before accepting it. Without the SHA and the branch there is nothing to
review, and a report missing either is returned unread — this is the single most useful discipline in the whole
handoff, because it turns "done" into something that can be checked.

## The project registry

This is how prod learns that a project exists at all. Whenever the dev starts work on a repository prod has not
seen, the dev reports it in this shape, and prod records it:

```
NEW PROJECT
repo:      <owner/name>
purpose:   <one sentence: what it does>
stack:     <language/framework, database if any>
port:      <port>
health:    <health path>
domain:    <intended hostname, or "undecided">
visibility: public | private
```

Prod keeps one line per project in a registry file and reads it before writing a brief, so a second task for an
existing project reuses the same port, domain and conventions instead of inventing new ones. Two projects claiming
the same hostname or the same published port is the collision this prevents.

When the dev is unsure whether a project is new, it reports it anyway. A duplicate entry costs one line; a missing
one costs a deployment that fights an existing one for port 443.

## Prod's verification before merge

```bash
gh pr view <n> --json files,title,body
gh pr diff <n>
gh pr diff <n> | grep -iE "api[_-]?key|password|secret|token|BEGIN .*PRIVATE KEY" || echo "clean"
```

Read the diff, not the description. Then confirm the four things that break deployments: the port matches the
proxy configuration, `/health` exists, the container does not run as root, and no credential is in the diff.

## Deploy

The stack lives in one directory on the production machine, brought up by `docker compose up -d`. Updates are
pulled by a timer, not by a person:

```bash
# /usr/local/bin/stack-update
#!/bin/sh
set -eu
cd /srv/stack
docker compose pull --quiet
docker compose up -d --remove-orphans
docker image prune -f
```

A systemd timer runs it every five minutes. Do not use Watchtower: the project is unmaintained and its own README
advises against production use. A timer is fewer moving parts and its failures land in the journal.

Rollback is a variable, not a rebuild:

```bash
cd /srv/stack && IMAGE_TAG=<previous-sha> docker compose up -d app
```

## What goes wrong

- **The dev deploys "just to check".** Then production runs an unreviewed commit and the prod agent's verification
  is theatre. Keep production credentials off the dev machine entirely; a permission that exists will be used.
- **The report says "done" with no SHA.** Nothing can be verified, so the task silently becomes trust. Return it.
- **Two projects, one port.** Both work in isolation and one dies in production. The registry exists for this.
- **The reverse proxy cannot reach the app.** Almost always `127.0.0.1` inside the container, or the two services
  on different Docker networks. `localhost` inside a container is that container, never the host.
- **The certificate is reissued on every restart.** The proxy's data volume was not persisted, and the ACME rate
  limit is not forgiving.
- **The prod agent edits code to fix a small thing.** Now the change has no review and no test. Send it back.
