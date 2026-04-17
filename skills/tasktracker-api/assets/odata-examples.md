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

Runtime indexes store model fields in `camelCase`, but the OData server typically expects `PascalCase` names in `$select`, `$expand`, `$orderby`, and `$filter`.

Use `ID`, `Title`, `Labels`, not `id`, `title`, `labels`.
Treat `projectId`, `createdAt`, `childEpics`, `hidden` as REST-style model names and convert them to `ProjectId`, `CreatedAt`, `ChildEpics`, `Hidden` in OData expressions.

## Task state filters

For TaskTracker entry entities, `EntryState` is used through the `State` field in OData filters.

- `State eq 10` means open entries.
- `State eq 20` means closed entries.

List open tasks in a project:

```powershell
python api.py -m odata_task --arg project_id=10 --odata-arg '$filter=State eq 10' --odata-arg '$select=ID,Title,State' --odata-arg '$top=50'
```

Count open tasks in a project:

```powershell
python api.py -m odata_task_count --arg project_id=10 --odata-arg '$filter=State eq 10'
```

List closed tasks in a project:

```powershell
python api.py -m odata_task --arg project_id=10 --odata-arg '$filter=State eq 20' --odata-arg '$select=ID,Title,State' --odata-arg '$top=50'
```

Combine task state with a label filter:

```powershell
python api.py -m odata_task --arg project_id=10 --odata-arg '$filter=State eq 10 and Labels/any(l:l/Title eq ''Тестирование'')' --odata-arg '$select=ID,Title,State,Labels' --odata-arg '$expand=Labels' --odata-arg '$top=50'
```

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
- When the user says "open" or "closed", prefer explaining the numeric `State` code in the answer instead of leaving `10` or `20` unexplained.
