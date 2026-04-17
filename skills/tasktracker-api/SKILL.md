---
name: tasktracker-api
description: "Use this skill when you need to read or change ERP TaskTracker entities such as tasks, epics, projects, comments, boards, sprints, milestones, and labels."
metadata: {"openclaw":{"requires":{"anyBins":["python","python3","py"],"env":["ERP_CLIENT_ID","ERP_CLIENT_SECRET","ERP_API_BASE_URL","ERP_TOKEN_URL"]}}}
---

# TaskTracker API

Use this skill when you need to work with ERP TaskTracker through the generated runtime indexes and CLI wrappers shipped with the skill.

Skill artifacts:

- `assets/index/manifest.json` — the only entry point into runtime indexes.
- `api.py` — the short CLI entry point from the skill root.
- `assets/odata-examples.md` — validated OData examples and common pitfalls.

Rules:

- Before any call, open `assets/index/manifest.json` first.
- Runtime indexes in `assets/index/*.json` and the `cliShape` commands derived from them are the only source of truth for agent actions.
- Use only commands and fields that exist in the runtime indexes.
- If a field or endpoint is missing in the runtime indexes, do not invent it.
- Do not invent high-level scenarios such as "create task", "change labels", or "read epic" unless they are tied to a concrete documented endpoint.
- The client always gets an access token through `client_credentials`.
- `ERP_API_BASE_URL` and `~/.config/erp/api_base_url` are treated as the ERP base URL; the client calls TaskTracker at `ERP_API_BASE_URL + "/tasktracker"`.
- `erp_tasktracker_api_base_url` or config `endpoint` can still override the fully qualified TaskTracker endpoint directly.
- OData read endpoints must exclude hidden entities by default with `Hidden eq false`; use `--include-hidden` only when reading deleted data is explicitly required.
- Domain model field names are interpreted differently by API surface: REST-oriented model fields and request parameters use `camelCase`, while OData entity fields in `$select`, `$filter`, `$expand`, and `$orderby` use `PascalCase`.
- Treat `EntryState` values as a fixed domain convention when filtering OData entities with the `State` field: `State eq 10` means open entries, `State eq 20` means closed entries.

Workflow:

1. Open `assets/index/manifest.json`.
2. Select the relevant compact index only through entries listed in `assets/index/manifest.json`.
3. Find the required endpoint by `key` or `summary`.
4. Take the `cliShape` field from the matched entry.
5. For OData endpoints, preserve the base command from `cliShape` and add `--odata-arg key=value` as needed. The CLI will append `Hidden eq false` to `$filter` by default.
6. Use the command from `cliShape`.
7. If the required endpoint is absent from the runtime indexes or there is no matching index entry, report that explicitly and stop.

## OData Pitfalls

- In PowerShell, wrap every `--odata-arg` in single quotes. Double quotes will expand `$select`, `$filter`, and similar names.
- OData wire field names usually use `PascalCase`, for example `ID`, `Title`, `Labels`, even when the local runtime index model shows `camelCase`.
- Treat local model examples like `projectId`, `createdAt`, `childEpics`, `hidden` as REST-style names; for OData write them as `ProjectId`, `CreatedAt`, `ChildEpics`, `Hidden`.
- Unless `--include-hidden` is passed, OData reads automatically apply `Hidden eq false`. If you pass your own `$filter`, the CLI combines it with `and Hidden eq false`.
- For collection filters, use `any(...)`, for example `Labels/any(l:l/Title eq 'Тестирование')`.
- If you need nested collection objects in the response body, add `$expand`, for example `$expand=Labels`.
- Treat `project_id` as required for project-scoped OData endpoints such as `odata_epic`, `odata_task`, `odata_board`, `odata_sprint`, and `odata_milestone`.
- For TaskTracker entry entities, use `State eq 10` for open items and `State eq 20` for closed items. When the user asks for "open tasks" or "closed tasks", prefer these explicit filters instead of leaving the state mapping implicit.
- Before inventing a complex OData filter, open `assets/odata-examples.md` and reuse a validated pattern when possible.

## EntryState Conventions

- `State eq 10` means open entries.
- `State eq 20` means closed entries.
- For user phrasing like "open tasks", "active tasks", or "not closed tasks", prefer `State eq 10`.
- For user phrasing like "closed tasks" or "completed tasks", prefer `State eq 20`.

Use the short shell entry point `api.py` from the skill root.

CLI example:

```bash
# entry selected through assets/index/manifest.json
{
  "key": "GET /Task/query/Get/{taskId}",
  "summary": "get task task id",
  "cliShape": "python api.py -m get_task_query_get_task_id --posarg <task_id>"
}

python api.py -m get_task_query_get_task_id --posarg 123

# URL-based variant when taskId is inside the link
python api.py -m get_task_query_get_task_id --task-url https://example.local/tasktracker/projects/10/tasks/123

# OData variant with explicit query options
# effective filter: (State eq 10) and Hidden eq false
python api.py -m odata_task --arg project_id=10 --odata-arg '$filter=State eq 10' --odata-arg '$select=ID,Title' --odata-arg '$top=50'

# OData variant for closed tasks
# effective filter: (State eq 20) and Hidden eq false
python api.py -m odata_task --arg project_id=10 --odata-arg '$filter=State eq 20' --odata-arg '$select=ID,Title' --odata-arg '$top=50'

# OData count for open tasks
# effective filter: (State eq 10) and Hidden eq false
python api.py -m odata_task_count --arg project_id=10 --odata-arg '$filter=State eq 10'

# OData epic filter by label title
# effective filter: (Labels/any(l:l/Title eq 'Тестирование')) and Hidden eq false
python api.py -m odata_epic --arg project_id=12 --odata-arg '$filter=Labels/any(l:l/Title eq ''Тестирование'')' --odata-arg '$select=ID,Title,Labels' --odata-arg '$expand=Labels' --odata-arg '$top=10'

# OData epic filter by label id
# effective filter: (Labels/any(l:l/ID eq 80)) and Hidden eq false
python api.py -m odata_epic_count --arg project_id=12 --odata-arg '$filter=Labels/any(l:l/ID eq 80)'

# Explicit hidden read when deleted entities are required
python api.py -m odata_task --arg project_id=10 --include-hidden --odata-arg '$filter=Hidden eq true' --odata-arg '$select=ID,Title,Hidden'
```

Notes:

- `api.py` runs the CLI command selected by the agent from the compact indexes.
- `api.py` supports `--task-url`, `--epic-url`, and `--project-url` for extracting IDs from links.
- `api.py` supports repeated `--odata-arg key=value` for OData query options.
- `api.py` supports `--include-hidden` to disable the default OData safety filter.
- For OData endpoints, supported runtime query options are `$filter`, `$select`, `$expand`, `$top`, `$skip`, `$orderby`, `$count`.
- Runtime indexes contain `key`, `summary`, and `cliShape`.
- Runtime indexes are generated from TaskTracker API descriptions; if generated artifacts and live behavior diverge, follow the shipped indexes for agent actions and report the discrepancy instead of inventing fields.
- `api.py` prints UTF-8 JSON and emits OData hints to stderr for common filter mistakes.
