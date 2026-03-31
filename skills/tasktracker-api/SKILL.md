---
name: tasktracker-api
description: "Use this skill when you need to read or change ERP TaskTracker entities such as tasks, epics, projects, comments, boards, sprints, milestones, and labels."
metadata: {"openclaw":{"requires":{"anyBins":["python","python3","py"],"env":["ERP_CLIENT_ID","ERP_CLIENT_SECRET","ERP_API_BASE_URL","ERP_TOKEN_URL"]}}}
---

# TaskTracker API

Use this skill when you need to work with ERP TaskTracker strictly through Swagger documentation.

Skill artifacts:

- `assets/index/manifest.json` — the only entry point into runtime indexes.
- `api.py` — the short CLI entry point from the skill root.

Rules:

- Swagger/OpenAPI TaskTracker is the only source of truth.
- Before any call, open `assets/index/manifest.json` first.
- Use only commands and fields that exist in indexes generated from Swagger.
- If a field is missing in Swagger, do not invent it.
- Do not invent high-level scenarios such as "create task", "change labels", or "read epic" unless they are tied to a concrete documented endpoint.
- The client always gets an access token through `client_credentials`.

Workflow:

1. Open `assets/index/manifest.json`.
2. Select the relevant compact index only through entries listed in `assets/index/manifest.json`.
3. Find the required endpoint by `key` or `summary`.
4. Take the `cliShape` field from the matched entry.
5. Use the command from `cliShape`.
6. If Swagger does not contain the required endpoint or there is no matching index entry, report that explicitly and stop.

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
```

Notes:

- `api.py` runs the CLI command selected by the agent from the compact indexes.
- `api.py` supports `--task-url`, `--epic-url`, and `--project-url` for extracting IDs from links.
- Runtime indexes contain `key`, `summary`, and `cliShape`.
