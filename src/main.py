from fastapi import APIRouter, FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

api_router = APIRouter(prefix="/frontend-api")


@api_router.get("/users/me")
def get_current_user():
    return {
        "email": "example@example.com",
        "isActive": True,
        "profileId": "1",
        "registeredAt": "2025-06-15T18:29:56+00:00",
        "updatedAt": "2025-06-15T18:29:56+00:00",
        "username": "user123",
    }


app = FastAPI(docs_url=None)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Swagger UI",
        swagger_js_url="https://cdn.staticfile.org/swagger-ui/5.2.0/swagger-ui-bundle.min.js",
        swagger_css_url="https://cdn.staticfile.org/swagger-ui/5.2.0/swagger-ui.min.css",
    )


app.include_router(api_router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
