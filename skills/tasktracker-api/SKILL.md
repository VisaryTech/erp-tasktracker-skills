---
name: tasktracker-api
description: "Use this skill when you need to read or change ERP TaskTracker entities such as tasks, epics, projects, comments, boards, sprints, milestones, and labels."
metadata: {"openclaw":{"requires":{"anyBins":["python","python3","py"]}}}
---

# TaskTracker API

Use this skill when you need to work with ERP TaskTracker strictly through Swagger documentation.

Skill artifacts:

- `assets/index/manifest.json` — the only entry point into runtime indexes.
- `api.py` — the short CLI entry point from the skill root.
- `scripts/tasktracker_api.py` — Python client `TaskTrackerAPI` generated from the same OpenAPI.
- `scripts/tasktracker_call.py` — CLI wrapper for invoking TaskTracker API methods.

Rules:

- Swagger/OpenAPI TaskTracker is the only source of truth.
- Before any call, open `assets/index/manifest.json` first.
- Use only commands and fields that exist in indexes generated from Swagger.
- If a field is missing in Swagger, do not invent it.
- If a value is missing in Swagger and that matters for the data structure, use `unknown_from_swagger`.
- Do not invent high-level scenarios such as "create task", "change labels", or "read epic" unless they are tied to a concrete documented endpoint.
- The client always gets an access token through `client_credentials` using `ERP_CLIENT_ID` and `ERP_CLIENT_SECRET`.

## Configuration

- `client_id`: `ERP_CLIENT_ID` or `~/.config/erp/client_id`
- `client_secret`: `ERP_CLIENT_SECRET` or `~/.config/erp/client_secret`
- `base_url`: `config["endpoint"]` or `ERP_API_BASE_URL` or `erp_tasktracker_api_base_url` or `~/.config/erp/api_base_url`
- `token_url`: `config["tokenUrl"]` or `ERP_TOKEN_URL` or `erp_tasktracker_token_url` or `~/.config/erp/token_url` or fallback `id-<host>/oidc/connect/token`

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
  "cliShape": "python skills/tasktracker-api/api.py -m get_task_query_get_task_id --posarg <task_id>"
}

python skills/tasktracker-api/api.py -m get_task_query_get_task_id --posarg 123

# URL-based variant when taskId is inside the link
python skills/tasktracker-api/api.py -m get_task_query_get_task_id --task-url https://example.local/tasktracker/projects/10/tasks/123
```

Notes:

- `api.py` invokes methods through compact indexes whose access starts at `assets/index/manifest.json`.
- `api.py` supports `--task-url`, `--epic-url`, and `--project-url` for extracting IDs from links.
- Runtime indexes contain `key`, `summary`, and `cliShape`.
- Public method names in `scripts/tasktracker_api.py` are generated deterministically from the Swagger description.
