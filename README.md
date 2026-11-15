# nouride-skills

Skills shared between the Nouride agents on Ndan's machines.

Repo: https://github.com/HadadKarsa/nouride-skills

## Install

On any Nouride box:

```
skill install HadadKarsa/nouride-skills/dev-prod-handoff
```

Or, if the CLI wants a URL:

```
skill install https://github.com/HadadKarsa/nouride-skills
```

The skill is queued for approval; nothing runs until a person approves it on the Pending tab.

## Contents

| Skill | Use when |
|---|---|
| `dev-prod-handoff` | Work is split across a dev machine and a production machine: one agent writes code and pushes branches, another reviews, merges and deploys. |

## Layout

```
dev-prod-handoff/
├── SKILL.md
├── templates/
│   ├── task-brief.md
│   └── report.md
└── scripts/
    └── check-report.py
```
