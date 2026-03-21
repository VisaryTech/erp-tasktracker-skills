import re


_TASK_URL_PATTERN = re.compile(r"/tasks/(?P<task_id>\d+)(?:[/?#]|$)", re.IGNORECASE)
_EPIC_URL_PATTERN = re.compile(r"/epics/(?P<epic_id>\d+)(?:[/?#]|$)", re.IGNORECASE)
_PROJECT_URL_PATTERN = re.compile(r"/projects/(?P<project_id>\d+)(?:[/?#]|$)", re.IGNORECASE)


def _extract_id_from_url(pattern, url, label):
    match = pattern.search(url)
    if not match:
        raise ValueError(f"Cannot extract {label} from URL")
    return int(match.group(label))


def get_task_id_from_url(url):
    return _extract_id_from_url(_TASK_URL_PATTERN, url, "task_id")


def get_epic_id_from_url(url):
    return _extract_id_from_url(_EPIC_URL_PATTERN, url, "epic_id")


def get_project_id_from_url(url):
    return _extract_id_from_url(_PROJECT_URL_PATTERN, url, "project_id")


def get_entity_from_url(url):
    task_match = _TASK_URL_PATTERN.search(url)
    if task_match:
        return {"entity": "task", "id": int(task_match.group("task_id"))}

    epic_match = _EPIC_URL_PATTERN.search(url)
    if epic_match:
        return {"entity": "epic", "id": int(epic_match.group("epic_id"))}

    raise ValueError("Cannot extract taskId or epicId from URL")
