---
name: tasktracker-api
description: "Унифицированная работа с ERP TaskTracker через API: чтение задачи/эпика по URL или ID, создание задачи и публикация комментария. Использовать, когда пользователь просит получить содержание задачи или эпика, создать новую задачу в проекте или добавить комментарий к задаче."
---

# TaskTracker API

Используй этот скилл как единую точку для операций TaskTracker: `read`, `create`, `comment`.

Общие правила:

- Используй только скрипты из `scripts/` этого скилла.
- Запускай команды с `workdir` в корень пользовательского проекта, где находится `.env`.
- Для авторизации используй `.env` или переменные окружения `erp_client_id` и `erp_client_secret`.
- Для базового домена ERP используй `erp_base_url` из `.env` или аргумент `--erp-base-url` (где применимо).
- При ошибке API или сети явно показывай причину и останавливай выполнение.
- Не выдумывай данные и идентификаторы.

## Read Task / Epic

Используй для чтения задачи или эпика:

- Задача: по URL или по `TaskId`. Возвращай только `TaskId`, `Title`, `Description`.
- Эпик: по URL или по `EpicId`. Возвращай только `ID`, `Title`, `Description`, `ProjectId`.

Команда (по URL задачи или эпика):

```bash
python <skill_dir>/scripts/get_task_data.py --url "<erp_base_url>/tasktracker/projects/{ProjectId}/tasks/{TaskId}"
python <skill_dir>/scripts/get_task_data.py --url "<erp_base_url>/tasktracker/projects/{ProjectId}/epics/{EpicId}"
```

Команда (по ID):

```bash
python <skill_dir>/scripts/get_task_data.py --task-id "12345" --erp-base-url "<erp_base_url>"
python <skill_dir>/scripts/get_task_data.py --epic-id "191" --erp-base-url "<erp_base_url>"
```

Порядок:

1. Проверь, что передан `url`, `taskId` или `epicId`.
2. Для `taskId`/`epicId` проверь, что доступен базовый URL: `--erp-base-url` или `erp_base_url` в `.env`.
3. Запусти `get_task_data.py`.
4. Для задачи верни только `TaskId`, `Title`, `Description` из JSON-ответа.
5. Для эпика верни только `ID`, `Title`, `Description`, `ProjectId` из JSON-ответа.

## Create Task

Используй для создания новой задачи.

Обязательные параметры:

- `--title`
- `--description`
- `--project-id` или `erp_tasktracker_project_id` в `.env`

Опциональные параметры:

- `--epic-id`
- `--label-ids` (CSV, например `6,73`)
- `--weight`
- `--sprint-id`
- `--milestone-id`
- `--erp-base-url`

Команда:

```bash
python <skill_dir>/scripts/create_task.py --title "test" --description "TEST" --project-id 12
```

Порядок:

1. Получи `title`, `description`, `projectId`.
2. Добавь только явно заданные опциональные параметры.
3. Запусти `create_task.py`.
4. Верни JSON-результат с `TaskId`, `Title`, `Description`, `projectId`, `apiResponse`.

## Comment Task

Используй для публикации комментария по `taskId`.

Обязательные параметры:

- `--task-id`
- `--text` или `--text-file`

Команды:

```bash
python <skill_dir>/scripts/post_task_comment.py --task-id "12345" --text "Текст комментария"
```

```bash
python <skill_dir>/scripts/post_task_comment.py --task-id "12345" --text-file "comment.md"
```

Порядок:

1. Получи `taskId` и текст комментария.
2. Убедись, что комментарий не пустой.
3. Запусти `post_task_comment.py`.
4. Верни `taskId` и `apiResponse`.
