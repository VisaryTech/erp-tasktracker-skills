# Files API Reference

## Entry Points

- Use `assets/index/manifest.json` as the only entry point into runtime indexes.
- Open the relevant domain file from `assets/index/` for endpoint selection, argument names, and CLI shapes.
- Use `api.py` as the short shell entry point from the skill root.

## Domain Indexes

- `admin.json`
- `annotations.json`
- `assetsupload.json`
- `cleanup.json`
- `drives.json`
- `extracttextdownload.json`
- `extracttextupload.json`
- `fileinfo.json`
- `filesdownload.json`
- `filesupload.json`
- `info.json`
- `items.json`
- `link.json`
- `linkdownload.json`
- `previewdownload.json`
- `previewlinkdownload.json`
- `previewupload.json`
- `systemfilesdownload.json`
- `unzip.json`

## Configuration

Preferred environment variables:

- `ERP_API_BASE_URL`
- `ERP_CLIENT_ID`
- `ERP_CLIENT_SECRET`
- `ERP_TOKEN_URL`

Fallbacks:

- `ERP_API_BASE_URL` is accepted and resolved as `ERP_API_BASE_URL + "/files"`.
- `~/.config/erp/api_base_url` and the generic `~/.config/erp/*` secrets are also accepted.

## CLI Rules

- Pass path parameters through `--posarg` in the order shown by `cliShape`.
- Pass query parameters and simple body fields through `--arg key=value`.
- Values are parsed as JSON when possible, so booleans, arrays, numbers, and objects can be passed directly.
- For complex request bodies, prefer `--arg body=<json-object>`.
- For download endpoints, prefer `--save-to <path>` to avoid dumping binary payloads into stdout.

## Endpoint Families

### Drives

- `GET /drives` lists drives with pagination, ownership, and ordering flags.
- `POST /drives` and `POST /drives/for_user/{owner_id}` create drives.
- `PUT /drives/by_id/{drive_id}/edit` updates the mutable drive fields from Swagger.
- `PUT /drives/by_id/{drive_id}/favorive` toggles favorite state. The path is spelled `favorive` in Swagger and must be used as-is.

### Items

- `GET /items` reads directory contents.
- `POST /items` creates a directory in the target drive/directory.
- `DELETE /items` deletes a batch of items. Pass the body as `{"items":[...],"force":true|false}`.
- `POST /items/move` and `POST /items/copy` accept `items` arrays in the JSON body.
- `GET /items/versions` and `POST /items/restore` work with item history.
- `POST /items/deleted/restore` restores an item from recycle bin and can move or rename it.

### Files And Previews

- `GET /files/download`, `GET /files/version`, `GET /files/guid`, `GET /preview/download`, and similar endpoints can return binary payloads. Use `--save-to`.
- `HEAD` variants return metadata only and are safe to print as JSON.
- `POST /files/upload`, `PUT /files/replace`, `POST /preview/upload`, and `POST /extractText/upload` are queue/control endpoints in Swagger and are driven by query parameters rather than multipart uploads.

### Links

- `POST /link/path_link/by_id`, `POST /link/version_link/by_id`, and `POST /link/file_link/by_id` generate share links.
- `POST /link/file_link/by_guid` generates a file link from `item_guid`.
- `GET /link/revoke` revokes a previously generated file link.
- `GET /link/info` and `GET /link/download` resolve or download an existing link.

### Annotations

- `GET /annotations` filters by `ItemId`, `Version`, and `DriveId`.
- `POST /annotations` and `PUT /annotations/{id}` accept `rect` and `selection` as structured JSON values.
- `DELETE /annotations/{id}` still expects a JSON body with `itemId`, `driveId`, and `version`.

## Examples

List items in a directory:

```bash
python api.py -m get_items --arg drive_id=12 --arg directory_id=345 --arg take=50 --arg skip=0
```

Create a drive with explicit JSON body:

```bash
python api.py -m post_drives --arg body='{"name":"Docs","label":"docs","quota":1073741824,"permissions":[],"itemsDefaultPermissions":[],"isCrypted":false,"isSystem":false,"hasHistory":true,"hasRecycleBin":true}'
```

Move several items:

```bash
python api.py -m post_items_move --arg drive_id=12 --arg directory_id=999 --arg items='[101,102,103]'
```

Download a file to disk:

```bash
python api.py -m get_files_download --arg drive_id=12 --arg item_id='[101]' --save-to tmp\\download.bin
```

Read preview headers without downloading the body:

```bash
python api.py -m head_preview_download --arg drive_id=12 --arg item_id=101 --arg size='m'
```
