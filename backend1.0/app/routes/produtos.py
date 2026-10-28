from fastapi import APIRouter

from app.database.supabase import consultar_produtos

router = APIRouter()


@router.get("/produtos")
def listar_produtos():
    return consultar_produtos()