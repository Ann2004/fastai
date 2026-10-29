from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

api_router = APIRouter(prefix="/frontend-api")


@api_router.get("/hello")
def hello():
    return {"message": "Привет из бекенда!"}


app = FastAPI()
app.include_router(api_router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
