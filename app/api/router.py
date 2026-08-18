from fastapi import APIRouter

from app.api.routes import (
    announcements,
    auth,
    chat,
    classes,
    courses,
    dashboard,
    health,
    memberships,
    notifications,
    resources,
    search,
    tasks,
    users,
    class_courses
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(classes.router)
api_router.include_router(memberships.router)
api_router.include_router(courses.router)
api_router.include_router(tasks.router)
api_router.include_router(feed.router)
api_router.include_router(announcements.router)
api_router.include_router(resources.router)
api_router.include_router(notifications.router)
api_router.include_router(search.router)
api_router.include_router(dashboard.router)
api_router.include_router(chat.router)
api_router.include_router(class_courses.router)
