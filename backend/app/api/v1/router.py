from fastapi import APIRouter
from app.api.v1 import auth, spaces, projects, materials, tutor, quizzes, mastery, admin, analytics, cheat_sheet

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(spaces.router)
api_router.include_router(projects.router)
api_router.include_router(materials.router)
api_router.include_router(tutor.router)
api_router.include_router(quizzes.router)
api_router.include_router(mastery.router)
api_router.include_router(admin.router)
api_router.include_router(analytics.router)
api_router.include_router(cheat_sheet.router)

