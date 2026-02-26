---
name: tasktracker-comment-task
description: Публикация комментария в задачу ERP TaskTracker по ID задачи с авторизацией через client_credentials. Использовать, когда пользователь просит оставить комментарий в задаче TaskTracker, опубликовать замечания/уточнения в задаче или добавить структурированный фидбек по конкретному taskId.
---

# TaskTracker Comment Task

Используй этот скилл для безопасной публикации комментария в задачу TaskTracker.

## Обязательные входные данные

- ID задачи (`taskId`)
- Текст комментария

## Порядок выполнения

1. Получи от пользователя `taskId` и текст комментария.
2. Подготовь комментарий: кратко, структурированно, без лишнего текста.
3. Отправь комментарий через `scripts/post_task_comment.py`.
4. Верни пользователю результат публикации (`taskId` и ответ API).

## Команды

Опубликовать комментарий строкой:

```bash
python C:/Users/<user>/.codex/skills/tasktracker-comment-task/scripts/post_task_comment.py --task-id "12345" --text "Текст комментария"
```

Опубликовать комментарий из файла:

```bash
python C:/Users/<user>/.codex/skills/tasktracker-comment-task/scripts/post_task_comment.py --task-id "12345" --text-file "comment.md"
```

Опубликовать комментарий в другом ERP-контуре:

```bash
python C:/Users/<user>/.codex/skills/tasktracker-comment-task/scripts/post_task_comment.py --base-url "https://erp.example.cloud" --task-id "12345" --text "Текст комментария"
```

Запускать команду с `workdir` в корень пользовательского проекта (где находится `.env`), а не из директории skill.

## Требования к устойчивости

- Используй `.env` или переменные окружения `erp_client_id` и `erp_client_secret`.
- Загружай `.env` из корня пользовательского проекта через корректный `workdir`; не запускай из директории skill.
- Не отправляй пустой комментарий.
- При ошибке API явно показывай код/причину и останавливай выполнение.
- Не выдумывай `taskId`: используй ID, который дал пользователь.
