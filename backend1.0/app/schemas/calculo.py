
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CalculoCreate(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
    )

    id_produto: int = Field(gt=0)
    peso_animal_ou_area: float = Field(gt=0)

    # Campos opcionais para cálculos de medicamentos.
    dose_por_kg: float | None = Field(default=None, gt=0)
    concentracao: float | None = Field(default=None, gt=0)
    doses_por_dia: float | None = Field(default=None, gt=0)
    duracao_dias: int | None = Field(default=None, gt=0)

    tipo_calculo: str | None = None
    nivel_atividade: str | None = None
    fase: str | None = None

    @field_validator("tipo_calculo")
    @classmethod
    def validar_tipo_calculo(cls, valor):
        if valor is None:
            return valor

        valor = valor.strip().casefold()

        if valor not in {"liquido", "comprimido"}:
            raise ValueError(
                "tipo_calculo deve ser 'liquido' ou 'comprimido'."
            )

        return valor

    @field_validator("nivel_atividade", "fase")
    @classmethod
    def normalizar_texto_opcional(cls, valor):
        if valor is None:
            return valor

        valor = valor.strip()

        return valor or None
