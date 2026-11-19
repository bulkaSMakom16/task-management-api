from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from config.database import SessionLocal

from .jobs import cancel_overdue_tasks
from .models import Task


async def register_and_login(client, username):
    credentials = {"username": username, "password": "Walk-by-the-river-27!"}
    response = await client.post("/api/auth/register/", json=credentials)
    user_id = response.json()["id"]

    response = await client.post("/api/auth/login/", json=credentials)
    token = response.json()["access_token"]
    return user_id, {"Authorization": f"Bearer {token}"}


def days_from_now(days):
    deadline = datetime.now(timezone.utc) + timedelta(days=days)
    return deadline.isoformat()


async def move_deadline_to_past(task_id):
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    query = update(Task).where(Task.id == task_id).values(deadline=yesterday)
    async with SessionLocal() as session:
        await session.execute(query)
        await session.commit()


class TestTaskAPI:
    async def test_create_task_comment_and_change_status(self, client):
        author_id, author_headers = await register_and_login(client, "author")
        worker_id, worker_headers = await register_and_login(client, "worker")
        _, stranger_headers = await register_and_login(client, "stranger")
        data = {
            "title": "Write report",
            "priority": "high",
            "assignee_id": worker_id,
            "deadline": days_from_now(1),
        }

        url = "/api/tasks/"
        response = await client.post(url, json=data)
        assert response.status_code == 401

        response = await client.post(url, json=data, headers=author_headers)
        assert response.status_code == 201
        assert response.json()["status"] == "backlog"
        assert response.json()["author_id"] == author_id

        task_id = response.json()["id"]
        detail_url = f"{url}{task_id}/"
        status_url = f"{detail_url}status/"
        comments_url = f"{detail_url}comments/"

        comment = {"text": "I can help with the charts."}
        response = await client.post(comments_url, json=comment, headers=stranger_headers)
        assert response.status_code == 201
        response = await client.get(comments_url, headers=author_headers)
        assert response.json()["count"] == 1
        assert response.json()["results"][0]["text"] == "I can help with the charts."

        data = {"status": "in_progress"}
        response = await client.patch(status_url, json=data, headers=stranger_headers)
        assert response.status_code == 403

        response = await client.patch(status_url, json={"status": "done"}, headers=worker_headers)
        assert response.status_code == 400

        data = {"status": "in_progress"}
        response = await client.patch(status_url, json=data, headers=worker_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

        response = await client.delete(detail_url, headers=author_headers)
        assert response.status_code == 409

        response = await client.patch(status_url, json={"status": "review"}, headers=worker_headers)
        assert response.status_code == 200

        data = {"status": "backlog"}
        response = await client.patch(status_url, json=data, headers=worker_headers)
        assert response.status_code == 400

        data = {"assignee_id": author_id}
        response = await client.patch(detail_url, json=data, headers=author_headers)
        assert response.status_code == 409

        response = await client.patch(status_url, json={"status": "done"}, headers=worker_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "done"

        data = {"title": "New title"}
        response = await client.patch(detail_url, json=data, headers=author_headers)
        assert response.status_code == 409

    async def test_done_needs_assignee_and_future_deadline(self, client):
        worker_id, headers = await register_and_login(client, "worker")
        url = "/api/tasks/"

        data = {"title": "Old task", "deadline": days_from_now(-1)}
        response = await client.post(url, json=data, headers=headers)
        assert response.status_code == 422

        data = {"title": "Task without assignee", "deadline": days_from_now(1)}
        response = await client.post(url, json=data, headers=headers)
        status_url = f"{url}{response.json()['id']}/status/"
        for status in ("in_progress", "review"):
            response = await client.patch(status_url, json={"status": status}, headers=headers)
            assert response.status_code == 200

        response = await client.patch(status_url, json={"status": "done"}, headers=headers)
        assert response.status_code == 400
        assert "assignee" in response.json()["detail"]

        data = {"title": "Late task", "assignee_id": worker_id, "deadline": days_from_now(1)}
        response = await client.post(url, json=data, headers=headers)
        task_id = response.json()["id"]
        detail_url = f"{url}{task_id}/"
        status_url = f"{detail_url}status/"

        data = {"deadline": days_from_now(-1)}
        response = await client.patch(detail_url, json=data, headers=headers)
        assert response.status_code == 422

        for status in ("in_progress", "review"):
            response = await client.patch(status_url, json={"status": status}, headers=headers)
            assert response.status_code == 200

        await move_deadline_to_past(task_id)
        response = await client.patch(status_url, json={"status": "done"}, headers=headers)
        assert response.status_code == 400
        assert "deadline" in response.json()["detail"]

    async def test_delete_task(self, client):
        _, author_headers = await register_and_login(client, "author")
        _, stranger_headers = await register_and_login(client, "stranger")

        url = "/api/tasks/"
        response = await client.post(url, json={"title": "Clean desk"}, headers=author_headers)
        detail_url = f"{url}{response.json()['id']}/"

        response = await client.delete(detail_url, headers=stranger_headers)
        assert response.status_code == 403

        response = await client.delete(detail_url, headers=author_headers)
        assert response.status_code == 204
        response = await client.get(detail_url, headers=author_headers)
        assert response.status_code == 404

    async def test_active_task_limit(self, client):
        worker_id, headers = await register_and_login(client, "worker")
        url = "/api/tasks/"

        for number in range(10):
            data = {"title": f"Task {number}", "assignee_id": worker_id}
            response = await client.post(url, json=data, headers=headers)
            assert response.status_code == 201

        last_task_id = response.json()["id"]
        data = {"title": "One more task", "assignee_id": worker_id}
        response = await client.post(url, json=data, headers=headers)
        assert response.status_code == 400

        response = await client.post(url, json={"title": "Free task"}, headers=headers)
        assert response.status_code == 201
        free_task_url = f"{url}{response.json()['id']}/"
        data = {"assignee_id": worker_id}
        response = await client.patch(free_task_url, json=data, headers=headers)
        assert response.status_code == 400

        status_url = f"{url}{last_task_id}/status/"
        response = await client.patch(status_url, json={"status": "cancelled"}, headers=headers)
        assert response.status_code == 200

        data = {"assignee_id": worker_id}
        response = await client.patch(free_task_url, json=data, headers=headers)
        assert response.status_code == 200

    async def test_list_filters_overdue_stats_and_auto_cancel(self, client):
        worker_id, headers = await register_and_login(client, "worker")
        url = "/api/tasks/"
        tasks = [
            {"title": "Fix login bug", "priority": "high", "deadline": days_from_now(3)},
            {"title": "Write docs", "description": "Explain login", "priority": "low"},
            {"title": "Plan sprint", "priority": "medium", "deadline": days_from_now(1)},
            {
                "title": "Fix typo",
                "priority": "high",
                "assignee_id": worker_id,
                "deadline": days_from_now(1),
            },
        ]
        task_ids = {}
        for data in tasks:
            response = await client.post(url, json=data, headers=headers)
            task_ids[data["title"]] = response.json()["id"]

        response = await client.get(url, headers=headers)
        titles = [task["title"] for task in response.json()["results"]]
        assert titles == ["Fix typo", "Fix login bug", "Plan sprint", "Write docs"]

        response = await client.get(url, params={"search": "LOGIN"}, headers=headers)
        assert response.json()["count"] == 2

        params = {"priority": "high", "assignee_id": worker_id}
        response = await client.get(url, params=params, headers=headers)
        assert response.json()["count"] == 1

        params = {"status": "backlog", "deadline_to": days_from_now(2)}
        response = await client.get(url, params=params, headers=headers)
        assert response.json()["count"] == 2

        response = await client.get(url, params={"ordering": "-created_at"}, headers=headers)
        assert response.json()["results"][0]["title"] == "Fix typo"

        response = await client.get(url, params={"ordering": "deadline"}, headers=headers)
        assert response.json()["results"][-1]["title"] == "Write docs"

        params = {"page": 2, "page_size": 3}
        response = await client.get(url, params=params, headers=headers)
        assert response.json()["count"] == 4
        assert len(response.json()["results"]) == 1

        await move_deadline_to_past(task_ids["Plan sprint"])
        response = await client.get(f"{url}overdue/", headers=headers)
        assert response.json()["count"] == 1

        response = await client.get(f"{url}stats/", headers=headers)
        assert response.json()["total"] == 4
        assert response.json()["overdue"] == 1
        assert response.json()["active"] == 4
        assert response.json()["by_priority"]["high"] == 2

        cancelled_count = await cancel_overdue_tasks()
        assert cancelled_count == 1

        response = await client.get(f"{url}{task_ids['Plan sprint']}/", headers=headers)
        assert response.json()["status"] == "cancelled"

        response = await client.get(f"{url}stats/", headers=headers)
        assert response.json()["overdue"] == 0
        assert response.json()["active"] == 3
        assert response.json()["by_status"]["cancelled"] == 1
