---
name: calendar-api
description: "Use this skill when you need to read or change ERP Calendar entities through Swagger documentation, including calendars, events, permissions, and calendar import/export operations."
metadata: {"openclaw":{"requires":{"anyBins":["python","python3","py"],"env":["ERP_CLIENT_ID","ERP_CLIENT_SECRET","ERP_API_BASE_URL","ERP_TOKEN_URL"]}}}
---

# Calendar API

Use this skill when you need to work with ERP Calendar strictly through Swagger documentation.

Skill artifacts:

- `assets/index/manifest.json` - the only entry point into runtime indexes.
- `api.py` - the short CLI entry point from the skill root.

Model note:

- Each domain index in `assets/index/*.json` contains its own `model` section.
- Swagger does not publish response fields or example payloads for calendar reads.
- `assets/index/calendar.json` contains fields observed from a live `GET /calendar` response and should be treated as runtime-confirmed rather than Swagger-derived.
- `assets/index/event.json` contains fields observed from live `GET /event` and `GET /event/{id}` responses.
- `assets/index/permission.json` contains fields observed from a live `PATCH /calendar/{id}` response when a non-empty `Permissions` array was sent.

Rules:

- Swagger/OpenAPI Calendar is the only source of truth.
- Before any call, open `assets/index/manifest.json` first.
- Use only commands and fields that exist in indexes generated from Swagger.
- If a field is missing in Swagger, do not invent it.
- Do not invent high-level scenarios unless they map to a concrete documented endpoint.
- The client always gets an access token through `client_credentials`.
- Base URL resolution uses only `ERP_API_BASE_URL + "/calendar"`.
- REST query parameters and JSON body fields use `camelCase` exactly as shown in Swagger.
- Swagger exposes generic object bodies for create and update operations. Treat payload shape as unknown unless the user provides it or another trusted source documents it.
- `POST /calendar/import/{id}` requires `--file <path>` with multipart upload.
- `GET /calendar/export/{id}` can write the response body to disk through `--output <path>`.
- `PATCH /calendar/{id}` behaves like a replace-style update in practice; omitting `Alias` cleared it in a live probe.
- `PATCH /calendar/{id}` echoes a typed `Permissions` collection in the response when the request body includes it, even when a subsequent `GET /calendar/{id}` still returns `Permissions: null`.
- `PATCH /event` enforces optimistic concurrency; a body without the current `RowVersion` returned `ERROR_UpdateConcurrencyException`.
- Calendar event bodies are patched into `Visary.Calendars.Entities.Event` on the server, not into a DTO contract.
- Event payloads therefore need entity-compatible nested collections: `Users` items use `UserId`, `Groups` items use `GroupId`, and `Notifications` items use `NotificationTime`.
- The CLI normalizes common shorthand event payloads such as `calendarId`, `users: [1,3]`, `groups: [7]`, and `notifications: [15,30]` into the server-compatible shape before sending the request.

Workflow:

1. Open `assets/index/manifest.json`.
2. Select the relevant compact index only through entries listed in `assets/index/manifest.json`.
3. Find the required endpoint by `key` or `summary`.
4. Take the `cliShape` field from the matched entry.
5. Use the command from `cliShape`.
6. If Swagger does not contain the required endpoint or there is no matching index entry, report that explicitly and stop.

Documented query parameters:

- `GET /event`: `calendarId`, `start`, `end`
- `GET /permission`: `calendarId`
- `GET /calendar/export/{id}`: `start`, `end`, `fileName`

Swagger limitations:

- Most Calendar endpoints do not publish concrete response schemas.
- Create and update bodies are generic JSON objects with unknown field shape.
- Do not invent request fields. Reuse only fields explicitly provided by the user or by another trusted source.

Use the short shell entry point `api.py` from the skill root.

CLI examples:

```bash
# entry selected through assets/index/manifest.json
{
  "key": "GET /calendar/{id}",
  "summary": "get calendar id",
  "cliShape": "python api.py -m get_calendar_id --posarg <id>"
}

python api.py -m get_calendar
python api.py -m get_calendar_by_owner_id_owner_id --posarg 7
python api.py -m get_event --arg calendar_id=12 --arg start='2026-04-01T00:00:00Z' --arg end='2026-04-30T23:59:59Z'

# generic JSON body from user-provided payload
python api.py -m post_calendar --arg body='{\"title\":\"Team calendar\",\"ownerId\":7}'
python api.py -m patch_event --arg body='{\"id\":55,\"title\":\"Rescheduled demo\"}'
python api.py -m post_event --arg body='{\"calendarId\":12,\"title\":\"Planning\",\"startDate\":\"2026-04-11T10:00:00Z\",\"endDate\":\"2026-04-11T11:00:00Z\",\"users\":[1,3,4,5]}'

# export response to file
python api.py -m get_calendar_export_id --posarg 12 --arg start='2026-04-01T00:00:00Z' --arg end='2026-04-30T23:59:59Z' --arg file_name='team.ics' --output .\\team.ics

# import file into calendar
python api.py -m post_calendar_import_id --posarg 12 --file .\\team.ics
```

Notes:

- `api.py` runs the CLI command selected by the agent from the compact index.
- Use `--arg body=<json-object>` for endpoints with generic JSON request bodies.
- Use repeated `--arg key=value` for documented query parameters.
- Runtime indexes contain `key`, `summary`, and `cliShape`.
- For export without `--output`, the CLI prints JSON metadata and includes the response body as text when it is decodable.
- For event create/update, prefer passing `calendarId`, `users`, `groups`, and `notifications` in shorthand form through the CLI; it will expand them to the entity contract expected by the API.
