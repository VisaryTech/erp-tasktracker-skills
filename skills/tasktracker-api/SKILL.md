---
name: tasktracker-api
description: "Унифицированная работа с ERP TaskTracker через API: чтение задачи/эпика по URL или ID, чтение комментариев задачи/эпика, создание задачи, смена меток, управление связями задач и публикация комментариев к задачам и эпикам. Использовать, когда пользователь просит получить содержание задачи/эпика, прочитать комментарии задачи/эпика, создать новую задачу в проекте, изменить метки/связи задачи или добавить комментарий к задаче/эпику."
metadata: {"openclaw":{"requires":{"anyBins":["python","python3","py"],"env":["erp_client_id","erp_client_secret"]}}}
---

# TaskTracker API

Используй этот скилл как единую точку для операций TaskTracker: `read`, `read comments`, `create`, `change labels`, `manage links`, `comment`.

Общие правила:

- Используй только скрипты из `scripts/` этого скилла.
- Запускай команды с `workdir` в корень пользовательского проекта, где находится `.env`.
- Для авторизации используй `.env` или переменные окружения `erp_client_id` и `erp_client_secret`.
- Для базового домена ERP используй `erp_base_url` из `.env` или аргумент `--erp-base-url` (где применимо).
- Для Project ID используй `projectId` из `.env` (или аргумент `--project-id`, где применимо).
- При ошибке API или сети явно показывай причину и останавливай выполнение.
- Не выдумывай данные и идентификаторы.

## Read Task / Epic

Используй для чтения задачи или эпика:

- Задача: по URL или по `TaskId`. Возвращай JSON-ответ API как есть.
- Эпик: по URL или по `EpicId`. Возвращай JSON-ответ API как есть.

Команда (по URL задачи или эпика):

```bash
python <skill_dir>/scripts/get_task_data.py --url "<erp_base_url>/tasktracker/projects/{ProjectId}/tasks/{TaskId}"
python <skill_dir>/scripts/get_task_data.py --url "<erp_base_url>/tasktracker/projects/{ProjectId}/epics/{EpicId}"
```

Команда (по ID):

```bash
python <skill_dir>/scripts/get_task_data.py --task-id "<task_id>" --erp-base-url "<erp_base_url>"
python <skill_dir>/scripts/get_task_data.py --epic-id "<epic_id>" --erp-base-url "<erp_base_url>"
```

Порядок:

1. Проверь, что передан `url`, `taskId` или `epicId`.
2. Для `taskId`/`epicId` проверь, что доступен базовый URL: `--erp-base-url` или `erp_base_url` в `.env`.
3. Запусти `get_task_data.py`.
4. Верни JSON-ответ API без изменений.

## Read Comments

Используй для чтения комментариев задачи по `TaskId` или эпика по `EpicId`.

- Возвращай JSON-массив комментариев API как есть.

Команды:

```bash
python <skill_dir>/scripts/get_task_data.py --task-comments-id "<task_id>" --erp-base-url "<erp_base_url>"
python <skill_dir>/scripts/get_task_data.py --epic-comments-id "<epic_id>" --erp-base-url "<erp_base_url>"
```

Порядок:

1. Проверь, что передан `taskCommentsId` или `epicCommentsId`.
2. Проверь, что доступен базовый URL: `--erp-base-url` или `erp_base_url` в `.env`.
3. Запусти `get_task_data.py` с `--task-comments-id` или `--epic-comments-id`.
4. Верни JSON-ответ API без изменений.

## Read Epic Lists

Используй для чтения списков эпиков в статусах проверки.

- На проверке (`to-approve`): фильтр по метке `erp_label_to_approve`.
- Готовы (`approved`): фильтр по метке `erp_label_approved`.
- По умолчанию читается top=50; можно изменить через `--top`.

Команды:

```bash
python <skill_dir>/scripts/get_task_data.py --epics-to-approve --project-id "<project_id>" --erp-base-url "<erp_base_url>"
python <skill_dir>/scripts/get_task_data.py --epics-approved --project-id "<project_id>" --erp-base-url "<erp_base_url>"
```

Порядок:

1. Получи режим: `to-approve` или `approved`.
2. Возьми `projectId` из `--project-id` или `.env` (`projectId`).
3. Возьми ID метки из `.env` (`erp_label_to_approve` или `erp_label_approved`).
4. Запусти `get_task_data.py` и верни JSON-ответ API без изменений.

## Create Task

Используй для создания новой задачи.

Обязательные параметры:

- `--title`
- `--description`
- `--project-id` или `projectId` в `.env`

Опциональные параметры:

- `--epic-id`
- `--label-ids` (CSV)
- `--weight`
- `--sprint-id`
- `--milestone-id`
- `--erp-base-url`

Команда:

```bash
python <skill_dir>/scripts/create_task.py --title "test" --description "TEST" --project-id "<project_id>"
```

Порядок:

1. Получи `title`, `description`, `projectId`.
2. Добавь только явно заданные опциональные параметры.
3. Запусти `create_task.py`.
4. Верни JSON-ответ API без изменений.

## Comment

Используй для публикации комментария к задаче или эпику.

Обязательные параметры:

- `--entity` (`task` или `epic`)
- `--id` (`taskId` или `epicId`)
- `--text` или `--text-file`

Опциональные параметры:

- `--parent-id` (если это ответ на существующий комментарий)

Команды:

```bash
python <skill_dir>/scripts/post_comment.py --entity task --id "<task_id>" --text "Текст комментария"
```

```bash
python <skill_dir>/scripts/post_comment.py --entity epic --id "<epic_id>" --parent-id "<parent_comment_id>" --text-file "comment.md"
```

Порядок:

1. Получи `entity`, `id`, текст комментария и опционально `parentId`.
2. Убедись, что комментарий не пустой.
3. Запусти `post_comment.py`.
4. Верни JSON-ответ API без изменений.

## Change Task Labels

Используй для изменения меток задачи через endpoint `/Task/command/ChangeLabels/{taskId}`.

Обязательные параметры:

- `--task-id`

Опциональные параметры:

- `--label-ids` (CSV; пустая строка очищает все метки)
- `--erp-base-url`

Команда:

```bash
python <skill_dir>/scripts/change_task_labels.py --task-id "<task_id>" --label-ids "1,2,3"
```

Порядок:

1. Получи `taskId` и `labelIds` (если не переданы, отправляй пустой массив).
2. Запусти `change_task_labels.py`.
3. Верни JSON-ответ API без изменений.

## Change Epic Labels / Status

Используй для изменения меток эпика через endpoint `/epic/command/changeLabels/{epicId}`.

Обязательные параметры:

- `--epic-id`

Один из вариантов:

- `--status checked` (ставит метку из `erp_label_approved`)
- `--status to-define` (ставит метку из `erp_label_to_define`)
- `--label-ids` (CSV) для явного набора меток

Команды:

```bash
python <skill_dir>/scripts/change_epic_labels.py --epic-id "<epic_id>" --status checked
python <skill_dir>/scripts/change_epic_labels.py --epic-id "<epic_id>" --status to-define
```

Порядок:

1. Получи `epicId` и статус (`checked` или `to-define`) либо явные `labelIds`.
2. Для статуса возьми label ID из `.env` (`erp_label_approved` или `erp_label_to_define`).
3. Запусти `change_epic_labels.py`.
4. Верни JSON-ответ API без изменений.

## Manage Task Links

Используй для управления связями задач через endpoints:

- `/Task/command/CreateLink/{taskId}`
- `/Task/command/ChangeLinkType/{taskId}`
- `/Task/command/DeleteLink/{taskId}`

Поддерживаемые типы связи (`TaskLinkType`):

- `RelatesTo = 0`
- `Blocks = 1`
- `IsBlocked = 2`

Обязательные параметры:

- `--action` (`create`, `change-type`, `delete`)
- `--task-id`
- `--other-task-id`

Опциональные параметры:

- `--type` (обязателен для `create` и `change-type`; принимает `0|1|2` или `RelatesTo|Blocks|IsBlocked`)
- `--erp-base-url`

Команды:

```bash
python <skill_dir>/scripts/manage_task_links.py --action create --task-id "<task_id>" --other-task-id "<other_task_id>" --type RelatesTo
python <skill_dir>/scripts/manage_task_links.py --action change-type --task-id "<task_id>" --other-task-id "<other_task_id>" --type 1
python <skill_dir>/scripts/manage_task_links.py --action delete --task-id "<task_id>" --other-task-id "<other_task_id>"
```

Порядок:

1. Получи `action`, `taskId`, `otherTaskId` и при необходимости `type`.
2. Для `create`/`change-type` проверь, что `type` задан и валиден.
3. Запусти `manage_task_links.py`.
4. Верни JSON-ответ API без изменений.
