# OData Examples

These examples are validated against the live ERP TaskTracker API.

## PowerShell quoting

Use single quotes around each `--odata-arg` value. PowerShell expands `$select`, `$filter`, and other `$...` names inside double quotes.

Correct:

```powershell
python api.py -m odata_epic --arg project_id=12 --odata-arg '$select=ID,Title,Labels'
```

Incorrect:

```powershell
python api.py -m odata_epic --arg project_id=12 --odata-arg "$select=ID,Title,Labels"
```

## Field name casing

Swagger indexes store model fields in `camelCase`, but the OData server typically expects `PascalCase` names in `$select`, `$expand`, `$orderby`, and `$filter`.

Use `ID`, `Title`, `Labels`, not `id`, `title`, `labels`.

## Epic labels

Count epics that have at least one label:

```powershell
python api.py -m odata_epic_count --arg project_id=12 --odata-arg '$filter=Labels/any()'
```

Filter epics by label title:

```powershell
python api.py -m odata_epic --arg project_id=12 --odata-arg '$filter=Labels/any(l:l/Title eq ''Тестирование'')' --odata-arg '$select=ID,Title,Labels' --odata-arg '$expand=Labels' --odata-arg '$top=10'
```

Filter epics by label id:

```powershell
python api.py -m odata_epic --arg project_id=12 --odata-arg '$filter=Labels/any(l:l/ID eq 80)' --odata-arg '$select=ID,Title,Labels' --odata-arg '$expand=Labels' --odata-arg '$top=10'
```

Return only the count for the same filter:

```powershell
python api.py -m odata_epic_count --arg project_id=12 --odata-arg '$filter=Labels/any(l:l/ID eq 80)'
```

## Notes

- For `/odata/Epic`, `project_id` is effectively required by the API.
- Add `$expand=Labels` when you need label objects returned in the payload.
- The same casing rule usually applies to other OData endpoints.
