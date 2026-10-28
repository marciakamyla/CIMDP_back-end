
from math import isfinite
import unicodedata


class ErroMedicamento(Exception):
    """Erro durante o cálculo de medicamentos."""


def validar_positivo(valor, nome_campo):
    """Valida um número finito maior que zero."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErroMedicamento(
            f"{nome_campo} deve ser um número maior que zero."
        )

    try:
        numero_valido = isfinite(valor)
    except (OverflowError, TypeError, ValueError):
        numero_valido = False

    if not numero_valido or valor <= 0:
        raise ErroMedicamento(
            f"{nome_campo} deve ser um número finito maior que zero."
        )

    return valor


def calcular_dose_por_peso(peso_kg, dose_por_kg):
    """
    Calcula uma quantidade a partir de valores previamente definidos.
    Não determina nem recomenda uma dose clínica.
    """
    validar_positivo(peso_kg, "Peso em kg")
    validar_positivo(dose_por_kg, "Dose por kg")

    return peso_kg * dose_por_kg


def calcular_volume_ml(quantidade_mg, concentracao_mg_ml):
    """Calcula o volume matemático correspondente em mL."""
    validar_positivo(quantidade_mg, "Quantidade em mg")
    validar_positivo(
        concentracao_mg_ml,
        "Concentração em mg/mL",
    )

    return quantidade_mg / concentracao_mg_ml


def calcular_quantidade_comprimidos(
    quantidade_mg,
    concentracao_mg_comprimido,
):
    """Calcula a quantidade matemática de comprimidos."""
    validar_positivo(quantidade_mg, "Quantidade em mg")
    validar_positivo(
        concentracao_mg_comprimido,
        "Concentração em mg por comprimido",
    )

    return quantidade_mg / concentracao_mg_comprimido


def calcular_quantidade_tratamento(
    quantidade_por_dose,
    doses_por_dia,
    duracao_dias,
):
    """Calcula a quantidade total de um tratamento prescrito."""
    validar_positivo(
        quantidade_por_dose,
        "Quantidade por dose",
    )
    validar_positivo(doses_por_dia, "Doses por dia")
    validar_positivo(duracao_dias, "Duração em dias")

    total = quantidade_por_dose * doses_por_dia * duracao_dias

    return {
        "quantidade_por_dose": quantidade_por_dose,
        "doses_por_dia": doses_por_dia,
        "duracao_dias": duracao_dias,
        "quantidade_total": total,
    }


def identificar_tipo_calculo(apresentacao):
    """Identifica o tipo de cálculo pela apresentação informada."""
    if not isinstance(apresentacao, str) or not apresentacao.strip():
        raise ErroMedicamento(
            "A apresentação do medicamento deve ser informada."
        )

    chave = unicodedata.normalize(
        "NFKD",
        apresentacao.strip().casefold(),
    )
    chave = "".join(
        caractere
        for caractere in chave
        if not unicodedata.combining(caractere)
    )
    chave = " ".join(chave.split())

    tipos = {
        "comprimido": "comprimido",
        "comprimidos": "comprimido",
        "liquido": "liquido",
        "suspensao": "liquido",
        "solucao oral": "liquido",
    }

    if chave not in tipos:
        raise ErroMedicamento(
            "Apresentação ainda não possui cálculo configurado."
        )

    return tipos[chave]


def calcular_medicamento(
    apresentacao,
    quantidade,
    concentracao,
):
    """Direciona o cálculo conforme a apresentação informada."""
    tipo = identificar_tipo_calculo(apresentacao)

    if tipo == "liquido":
        resultado = calcular_volume_ml(
            quantidade,
            concentracao,
        )

        return {
            "tipo": tipo,
            "quantidade_calculada": resultado,
            "unidade": "mL",
        }

    if tipo == "comprimido":
        resultado = calcular_quantidade_comprimidos(
            quantidade,
            concentracao,
        )

        return {
            "tipo": tipo,
            "quantidade_calculada": resultado,
            "unidade": "comprimidos",
        }

    raise ErroMedicamento(
        "Não foi possível calcular esta apresentação."
    )
