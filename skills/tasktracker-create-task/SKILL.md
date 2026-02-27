---
name: tasktracker-create-task
description: Создание задач в ERP TaskTracker, когда пользователь просит завести новую задачу в TaskTracker.
---

# TaskTracker Create Task

Используй этот скилл для безопасного создания задачи в ERP TaskTracker.

## Обязательные входные данные

- `Title`
- `Description`
- `projectId` (передай параметром `--project-id` или возьми из `.env` ключа `erp_tasktracker_project_id`)

## Опциональные входные данные

- `EpicId`
- `LabelIds`
- `Weight`
- `SprintId`
- `MilestoneId`

## Порядок выполнения

1. Получи `Title`, `Description` и `projectId` (или убедись, что `erp_tasktracker_project_id` задан в `.env`).
2. Собери опциональные параметры, которые пользователь явно указал.
3. Запусти `scripts/create_task.py` для создания задачи через ERP API.
4. Верни пользователю JSON-результат с `TaskId`, `Title`, `Description`, `projectId` и `apiResponse`.

## Команды

Минимальный запуск:

```bash
python <skill_dir>/scripts/create_task.py --title "test" --description "TEST" --project-id 12
```

С опциональными параметрами:

```bash
python <skill_dir>/scripts/create_task.py --title "test" --description "TEST" --project-id 12 --epic-id 191 --label-ids "6,73" --weight 5 --sprint-id 10 --milestone-id 20
```

Где `<skill_dir>` — директория текущего скилла (путь, из которого открыт этот `SKILL.md`).

Запускать команду с `workdir` в корень пользовательского проекта (где находится `.env`), а не из директории skill.

## Требования к устойчивости

- Используй `.env` или переменные окружения `erp_client_id` и `erp_client_secret`.
- Для домена ERP используй `erp_base_url` из `.env` (или `--erp-base-url` в явном виде).
- Загружай `.env` из корня пользовательского проекта через корректный `workdir`; не запускай из директории skill.
- Не отправляй запрос без `Title`, `Description` и `projectId`.
- Для `projectId` сначала используй `--project-id`, при его отсутствии бери `erp_tasktracker_project_id` из `.env`.
- Передавай в API только те опциональные значения, которые пользователь явно задал.
- При ошибке API явно показывай код/причину и останавливай выполнение.
