---
name: tasktracker-api
description: "Унифицированная работа с ERP TaskTracker через API: чтение задачи/эпика по URL или ID, чтение комментариев задачи/эпика, создание задачи и публикация комментариев к задачам и эпикам. Использовать, когда пользователь просит получить содержание задачи/эпика, прочитать комментарии задачи/эпика, создать новую задачу в проекте или добавить комментарий к задаче/эпику."
---

# TaskTracker API

Используй этот скилл как единую точку для операций TaskTracker: `read`, `read comments`, `create`, `comment`.

Общие правила:

- Используй только скрипты из `scripts/` этого скилла.
- Запускай команды с `workdir` в корень пользовательского проекта, где находится `.env`.
- Для авторизации используй `.env` или переменные окружения `erp_client_id` и `erp_client_secret`.
- Для базового домена ERP используй `erp_base_url` из `.env` или аргумент `--erp-base-url` (где применимо).
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

## Create Task

Используй для создания новой задачи.

Обязательные параметры:

- `--title`
- `--description`
- `--project-id` или `erp_tasktracker_project_id` в `.env`

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
