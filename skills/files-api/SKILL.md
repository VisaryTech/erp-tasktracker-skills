---
name: files-api
description: "Use this skill when you need to read or change ERP Files entities through Swagger documentation, including drives, items, file downloads, previews, links, annotations, cleanup endpoints, and file-system metadata operations."
metadata: {"openclaw":{"requires":{"anyBins":["python","python3","py"],"env":["ERP_CLIENT_ID","ERP_CLIENT_SECRET","ERP_TOKEN_URL","ERP_API_BASE_URL"]}}}
---

# Files API

Use this skill when you need to work with ERP Files strictly through Swagger documentation.

Skill artifacts:

- `assets/index/manifest.json` - the only entry point into runtime indexes.
- `api.py` - the short CLI entry point from the skill root.
- `references/api-docs.md` - compact reference for domain indexes, payload patterns, and download rules.

Rules:

- Swagger/OpenAPI Files is the only source of truth.
- Before any call, open `assets/index/manifest.json` first.
- Select the relevant compact domain index only through entries listed in `assets/index/manifest.json`.
- Use only commands and fields that exist in the generated indexes.
- If a field is missing in Swagger, do not invent it.
- Do not invent high-level scenarios unless they map to a concrete documented endpoint.
- The client always gets an access token through `client_credentials`.
- REST-style query names and JSON body fields must stay exactly as shown in Swagger, including mixed casing such as `ItemId`, `DriveId`, `fileId`, and the typo path segment `favorive`.
- For large or binary download responses, use `--save-to <path>` instead of printing the body.
- For complex bodies, prefer `--arg body=<json-object>` over many fragmented `--arg` values.

Workflow:

1. Open `assets/index/manifest.json`.
2. Select the relevant domain index.
3. Find the required endpoint by `key`, `summary`, or `pythonMethod`.
4. Take the `cliShape` field from the matched entry.
5. Use the command from `cliShape`.
6. If Swagger does not contain the required endpoint or there is no matching index entry, report that explicitly and stop.

Use the short shell entry point `api.py` from the skill root.

CLI example:

```bash
# entry selected through assets/index/items.json
{
  "key": "GET /items",
  "summary": "GetList",
  "cliShape": "python api.py -m get_items --arg drive_id=<value> --arg directory_id=<value> --arg take=<value> --arg skip=<value> --arg total_count=<value> --arg order=<value> --arg desc=<value> --arg order_directory=<value> --arg type=<value>"
}

python api.py -m get_items --arg drive_id=12 --arg directory_id=345 --arg take=50 --arg skip=0

# create a directory by simple body field
python api.py -m post_items --arg drive_id=12 --arg directory_id=345 --arg name='Specs'

# restore a deleted item with explicit JSON body
python api.py -m post_items_deleted_restore --arg body='{"id":101,"driveId":12,"newDirectoryId":345,"newName":"Specs-restored"}'

# download to disk instead of printing bytes
python api.py -m get_files_download --arg drive_id=12 --arg item_id='[101]' --save-to tmp\\file.bin
```

Notes:

- `api.py` runs the CLI command selected by the agent from the compact index.
- `api.py` supports repeated `--arg key=value`; values are parsed as JSON when possible.
- `api.py` supports `--save-to` for raw response bytes.
- Runtime indexes are split by domain and listed in `assets/index/manifest.json`.
- Domain entries contain `key`, `summary`, `pythonMethod`, request parameter metadata, and `cliShape`.
