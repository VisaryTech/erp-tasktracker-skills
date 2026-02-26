---
name: tasktracker-read-task
description: Чтение задачи из ERP TaskTracker по ссылке с автоматическим получением данных через ERP API. Использовать, когда пользователь просит получить данные задачи по URL и вернуть поля TaskId, Title, Description.
---

# TaskTracker Read Task

Используй `scripts/get_task_data.py` как ЕДИНСТВЕННУЮ точку получения данных задачи. Не выдумывай данные. Если не можешь запустить скрипт — остановись и попроси у пользователя JSON-вывод скрипта целиком.

Пример запуска:

```bash
python C:/Users/<user>/.codex/skills/tasktracker-read-task/scripts/get_task_data.py --url "https://erp.visary.cloud/tasktracker/projects/{ProjectId}/tasks/{TaskId}"
```

Запускать команду с `workdir` в корень пользовательского проекта (где находится `.env`), а не из директории skill.

Скрипт возвращает JSON с полями:

- `TaskId`
- `Title`
- `Description`

## Порядок выполнения

1. Определи корень пользовательского проекта и проверь наличие `.env`.
2. Запусти `scripts/get_task_data.py` с URL задачи, используя `workdir=<project_root>`.
3. Если скрипт завершился с ошибкой, зафиксируй причину и заверши выполнение.
4. Возьми `TaskId`, `Title`, `Description` из JSON-результата.
5. Верни пользователю только эти поля.

## Требования к устойчивости

- Используй `.env` или переменные окружения `erp_client_id` и `erp_client_secret`.
- Загружай `.env` из корня пользовательского проекта через корректный `workdir`; не запускай из директории skill.
- Для получения задачи используй только `scripts/get_task_data.py`.
- Не подставляй значения вручную при ошибках API или авторизации.
- Завершай выполнение с явной причиной при критических ошибках (token/task fetch).
