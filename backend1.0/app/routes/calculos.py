
from datetime import date, timedelta
from math import isfinite

from fastapi import APIRouter, HTTPException

from app.database.supabase import (
    consultar_produto_por_id,
    consultar_regras_por_produto,
)
from app.schemas.calculo import CalculoCreate
from app.schemas.resultado import CalculoResponse
from app.services.motor_calculo import (
    ErroCalculo,
    aplicar_desperdicio,
    calcular_por_faixa,
    calcular_golden,
    calcular_faixa_consumo,
    calcular_consumo_por_fase,
    calcular_calopsita,
    calcular_periquito,
)
from app.services.motor_medicamentos import (
    ErroMedicamento,
    calcular_dose_por_peso,
    calcular_volume_ml,
    calcular_quantidade_comprimidos,
    calcular_quantidade_tratamento,
)

router = APIRouter()


def validar_numero_positivo(valor, nome_campo):
    if (
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not isfinite(valor)
        or valor <= 0
    ):
        raise HTTPException(
            status_code=400,
            detail=f"{nome_campo} deve ser um número maior que zero.",
        )
    return valor


def obter_regra(produto):
    # Mantém compatibilidade com regras que já vêm no objeto do produto.
    regra_existente = produto.get("regra_dosagem")
    if isinstance(regra_existente, dict) and regra_existente:
        return regra_existente

    id_produto = produto.get("id_produto")
    if not id_produto:
        raise HTTPException(
            status_code=400,
            detail="O produto não possui um ID válido.",
        )

    regras = consultar_regras_por_produto(id_produto)

    if not regras:
        raise HTTPException(
            status_code=400,
            detail="O produto não possui regras de dosagem ativas.",
        )

    faixas = []
    regras_fase = []
    percentuais_por_fase = {}

    for regra in regras:
        tipo_regra = str(
            regra.get("tipo_regra", "")
        ).strip().upper()

        if tipo_regra in {
            "CONSUMO_DIRETO",
            "CONSUMO_POR_FAIXA",
            "FAIXA_CONSUMO",
        }:
            faixas.append(regra)

        elif tipo_regra in {
            "CONSUMO_POR_FASE",
            "REGRAS_FASE",
        }:
            regras_fase.append(regra)

        elif tipo_regra == "INCLUSAO_INGREDIENTE":
            fase = regra.get("fase")
            percentual = regra.get("percentual_inclusao")

            if fase is not None and percentual is not None:
                percentuais_por_fase[str(fase)] = percentual

    resultado = {}

    if faixas:
        resultado["faixas"] = faixas

    if regras_fase:
        resultado["regras_fase"] = regras_fase

    if percentuais_por_fase:
        resultado["percentuais_por_fase"] = percentuais_por_fase

    if not resultado:
        raise HTTPException(
            status_code=400,
            detail=(
                "As regras cadastradas ainda não são compatíveis "
                "com o cálculo."
            ),
        )

    return resultado


def calcular_medicamento_endpoint(dados, tipo):
    if dados.dose_por_kg is None or dados.concentracao is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Informe dose_por_kg e concentracao, "
                "com unidades compatíveis e previamente validadas."
            ),
        )

    try:
        dose_mg = calcular_dose_por_peso(
            dados.peso_animal_ou_area,
            dados.dose_por_kg,
        )

        if tipo == "liquido":
            quantidade_por_dose = calcular_volume_ml(
                dose_mg,
                dados.concentracao,
            )
            unidade = "mL"

        elif tipo == "comprimido":
            quantidade_por_dose = calcular_quantidade_comprimidos(
                dose_mg,
                dados.concentracao,
            )
            unidade = "comprimidos"

        else:
            raise HTTPException(
                status_code=400,
                detail="Apresentação de medicamento não configurada.",
            )

        resultado = {
            "dose_calculada": dose_mg,
            "quantidade_por_dose": quantidade_por_dose,
            "unidade": unidade,
        }

        if (
            dados.doses_por_dia is not None
            and dados.duracao_dias is not None
        ):
            resultado["tratamento"] = calcular_quantidade_tratamento(
                quantidade_por_dose,
                dados.doses_por_dia,
                dados.duracao_dias,
            )

        return {
            "tipo": "medicamento",
            "resultado": resultado,
        }

    except ErroMedicamento as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro),
        ) from erro


@router.post("/calculos", response_model=CalculoResponse)
def criar_calculo(dados: CalculoCreate):
    quantidade = validar_numero_positivo(
        dados.peso_animal_ou_area,
        "peso_animal_ou_area",
    )

    try:
        produto = consultar_produto_por_id(dados.id_produto)

    except HTTPException:
        raise

    except Exception as erro:
        print(f"Erro ao consultar produto no Supabase: {erro}")
        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar o produto.",
        ) from erro

    if produto is None:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado.",
        )

    if not isinstance(produto, dict):
        raise HTTPException(
            status_code=502,
            detail="Cadastro de produto inválido.",
        )

    tipo = produto.get("tipo")

    # Medicamentos e vermífugos.
    if tipo in {"medicamento", "vermifugo"}:
        tipo_calculo = dados.tipo_calculo

        if tipo_calculo not in {"liquido", "comprimido"}:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Informe tipo_calculo como 'liquido' ou "
                    "'comprimido'. Confirme a apresentação "
                    "do medicamento escolhido."
                ),
            )

        return calcular_medicamento_endpoint(
            dados,
            tipo_calculo,
        )

    if tipo not in {"racao", "adubo"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tipo de produto ainda não possui cálculo disponível."
            ),
        )

    regra = obter_regra(produto)

    if tipo == "racao":
        especie = str(
            produto.get("especie") or ""
        ).strip().casefold()

        faixas = regra.get("faixas")

        try:
            # IMPORTANTE:
            # Calopsitas e periquitos precisam ser tratados antes
            # das faixas genéricas de consumo mínimo e máximo.
            if especie in {
                "calopsita",
                "periquito",
                "periquitos",
            }:
                if not isinstance(faixas, list) or not faixas:
                    raise ErroCalculo(
                        "Não há faixas de consumo configuradas para esta ave."
                    )

                calculo = calcular_faixa_consumo(
                    faixas,
                    quantidade,
                )

                consumo_min = calculo.get("consumo_min_g_dia")
                consumo_max = calculo.get("consumo_max_g_dia")

                if consumo_min is None or consumo_max is None:
                    raise ErroCalculo(
                        "A regra da ave precisa ter consumo mínimo e máximo."
                    )

                # Localiza a regra que corresponde ao peso informado.
                faixa = next(
                    (
                        item
                        for item in faixas
                        if isinstance(item, dict)
                        and (
                            item.get("peso_min") is None
                            or quantidade >= item["peso_min"]
                        )
                        and (
                            item.get("peso_max") is None
                            or quantidade <= item["peso_max"]
                        )
                    ),
                    None,
                )

                if faixa is None:
                    raise ErroCalculo(
                        "Nenhuma faixa corresponde ao peso informado."
                    )

                possui_desperdicio = faixa.get(
                    "possui_desperdicio",
                    False,
                )

                percentual_desperdicio = faixa.get(
                    "percentual_desperdicio",
                    0,
                )

                # Valida a faixa de peso específica da espécie.
                if especie == "calopsita":
                    calcular_calopsita(quantidade, consumo_min)
                    calcular_calopsita(quantidade, consumo_max)
                else:
                    calcular_periquito(quantidade, consumo_min)
                    calcular_periquito(quantidade, consumo_max)

                # Aplica o desperdício ao mínimo e ao máximo.
                # Exemplo: 6–10 g com 100% de desperdício = 12–20 g.
                consumo_total_min = aplicar_desperdicio(
                    consumo_min,
                    possui_desperdicio,
                    percentual_desperdicio,
                )

                consumo_total_max = aplicar_desperdicio(
                    consumo_max,
                    possui_desperdicio,
                    percentual_desperdicio,
                )

                resultado = {
                    "consumo_min_g_dia": consumo_min,
                    "consumo_max_g_dia": consumo_max,
                    "consumo_total_min_g_dia": consumo_total_min,
                    "consumo_total_max_g_dia": consumo_total_max,
                    "possui_desperdicio": possui_desperdicio,
                    "percentual_desperdicio": percentual_desperdicio,
                }

                peso_embalagem = produto.get("peso_embalagem")

                if peso_embalagem is not None:
                    peso_embalagem_kg = validar_numero_positivo(
                        peso_embalagem,
                        "peso_embalagem",
                    )

                    if consumo_total_min > 0 and consumo_total_max > 0:
                        resultado["duracao_minima_embalagem_dias"] = int(
                            peso_embalagem_kg
                            * 1000
                            / consumo_total_max
                        )

                        resultado["duracao_maxima_embalagem_dias"] = int(
                            peso_embalagem_kg
                            * 1000
                            / consumo_total_min
                        )

                return {
                    "tipo": "racao",
                    "resultado": resultado,
                }

            # Regras com faixas, como Golden.
            if isinstance(faixas, list):
                possui_atividade = any(
                    isinstance(faixa, dict)
                    and faixa.get("nivel_atividade") is not None
                    and faixa.get("consumo_g") is not None
                    for faixa in faixas
                )

                if possui_atividade:
                    if not dados.nivel_atividade:
                        raise ErroCalculo(
                            "Informe o nível de atividade do animal."
                        )

                    calculo = calcular_golden(
                        faixas,
                        quantidade,
                        dados.nivel_atividade,
                    )

                    dose_diaria = calculo.get(
                        "consumo_total_g_dia",
                        calculo.get("consumo_g_dia"),
                    )

                # Faixas com consumo mínimo e máximo, como Magnus e Gatan.
                elif any(
                    isinstance(faixa, dict)
                    and (
                        faixa.get("consumo_min_g") is not None
                        or faixa.get("consumo_max_g") is not None
                    )
                    for faixa in faixas
                ):
                    calculo = calcular_faixa_consumo(
                        faixas,
                        quantidade,
                    )

                    consumo_min = calculo.get("consumo_min_g_dia")
                    consumo_max = calculo.get("consumo_max_g_dia")

                    resultado = dict(calculo)
                    peso_embalagem = produto.get("peso_embalagem")

                    if peso_embalagem is not None:
                        peso_embalagem_kg = validar_numero_positivo(
                            peso_embalagem,
                            "peso_embalagem",
                        )

                        if consumo_min is not None and consumo_max is not None:
                            resultado["duracao_minima_embalagem_dias"] = int(
                                peso_embalagem_kg * 1000 / consumo_max
                            )

                            resultado["duracao_maxima_embalagem_dias"] = int(
                                peso_embalagem_kg * 1000 / consumo_min
                            )

                    return {
                        "tipo": "racao",
                        "resultado": resultado,
                    }

                else:
                    calculo = calcular_por_faixa(
                        faixas,
                        quantidade,
                    )

                    dose_diaria = calculo.get(
                        "consumo_total_g_dia",
                        calculo.get("consumo_g_dia"),
                    )

            elif isinstance(regra.get("regras_fase"), list):
                if not dados.fase:
                    raise ErroCalculo(
                        "Informe a fase de criação."
                    )

                calculo = calcular_consumo_por_fase(
                    regra["regras_fase"],
                    dados.fase,
                )

                consumo_min = calculo.get("consumo_min_g_dia")
                consumo_max = calculo.get("consumo_max_g_dia")

                resultado = dict(calculo)
                peso_embalagem = produto.get("peso_embalagem")

                if peso_embalagem is not None:
                    peso_embalagem_kg = validar_numero_positivo(
                        peso_embalagem,
                        "peso_embalagem",
                    )

                    if consumo_min is not None and consumo_max is not None:
                        resultado["duracao_minima_embalagem_dias"] = int(
                            peso_embalagem_kg * 1000 / consumo_max
                        )

                        resultado["duracao_maxima_embalagem_dias"] = int(
                            peso_embalagem_kg * 1000 / consumo_min
                        )

                return {
                    "tipo": "racao",
                    "resultado": resultado,
                }

            elif regra.get("g_por_kg_dia") is not None:
                gramas_por_kg_dia = validar_numero_positivo(
                    regra.get("g_por_kg_dia"),
                    "g_por_kg_dia",
                )

                dose_diaria = quantidade * gramas_por_kg_dia

            else:
                raise ErroCalculo(
                    "Não há regra de cálculo configurada para este produto."
                )

        except ErroCalculo as erro:
            raise HTTPException(
                status_code=400,
                detail=str(erro),
            ) from erro

        if dose_diaria is None:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível determinar o consumo diário.",
            )

        resultado = {
            "dose_diaria_g": dose_diaria,
        }

        peso_embalagem = produto.get("peso_embalagem")

        if peso_embalagem is not None:
            peso_embalagem_kg = validar_numero_positivo(
                peso_embalagem,
                "peso_embalagem",
            )

            duracao = int(
                (peso_embalagem_kg * 1000) / dose_diaria
            )

            termino = date.today() + timedelta(days=duracao)

            resultado["duracao_estimada_dias"] = duracao
            resultado["data_estimada_termino"] = termino.isoformat()

        return {
            "tipo": "racao",
            "resultado": resultado,
        }

    # Adubos.
    if tipo == "adubo":
        gramas_por_m2 = validar_numero_positivo(
            regra.get("g_por_m2"),
            "g_por_m2",
        )

        peso_embalagem_kg = validar_numero_positivo(
            produto.get("peso_embalagem"),
            "peso_embalagem",
        )

        quantidade_aplicacao = quantidade * gramas_por_m2

        aplicacoes = (
            peso_embalagem_kg * 1000
        ) / quantidade_aplicacao

        return {
            "tipo": "adubo",
            "resultado": {
                "quantidade_por_aplicacao_g": quantidade_aplicacao,
                "quantidade_aplicacoes": aplicacoes,
            },
        }
