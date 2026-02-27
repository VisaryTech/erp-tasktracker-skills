# ERP TaskTracker Skills

Набор локальных Codex-скиллов для работы с ERP TaskTracker.

Репозиторий включает скиллы для:

- создание и чтение задачи;
- публикации комментариев к задаче;
- проверка готовности задачи к разработке.

## Требования

- Python 3.10+
- Доступ к ERP API
- Учетные данные:
  - `.env` с `erp_base_url`, `erp_client_id` и `erp_client_secret`
  - или переменные окружения `erp_base_url`, `erp_client_id` и `erp_client_secret`
- Для скилла создания задачи: `.env` ключ `erp_tasktracker_project_id` (если не передаешь `--project-id`)
