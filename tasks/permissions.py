def can_change_task(task, user):
    return user.id in (task.author_id, task.assignee_id)


def can_delete_task(task, user):
    return task.author_id == user.id
