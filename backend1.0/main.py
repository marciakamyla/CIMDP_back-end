
from fastapi import FastAPI

from app.routes.produtos import router as produtos_router
from app.routes.calculos import router as calculos_router

app = FastAPI(
    title="CIMDP API",
    version="1.0.0",
)

app.include_router(produtos_router)
app.include_router(calculos_router)


@app.get("/")
def inicio():
    return {
        "mensagem": "API do CIMDP funcionando!"
    }
