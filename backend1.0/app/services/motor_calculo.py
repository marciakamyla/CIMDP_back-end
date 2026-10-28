
from math import isfinite


class ErroCalculo(Exception):
    """Erro ocorrido durante uma operação do motor de cálculo."""


def validar_numero_positivo(valor, nome_campo):
    """Valida se o valor é numérico, finito e maior que zero."""
    if (
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not isfinite(valor)
        or valor <= 0
    ):
        raise ErroCalculo(
            f"O campo '{nome_campo}' deve ser um número finito maior que zero."
        )
    return valor


def validar_percentual(valor, nome_campo="percentual"):
    """Valida um percentual entre 0 e 100."""
    if (
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not isfinite(valor)
        or not 0 <= valor <= 100
    ):
        raise ErroCalculo(
            f"O campo '{nome_campo}' deve estar entre 0 e 100."
        )
    return valor


def validar_faixa_consumo(consumo_min, consumo_max):
    """Valida e retorna os limites de consumo de uma regra."""
    if consumo_min is None and consumo_max is None:
        raise ErroCalculo("A regra não possui consumo configurado.")

    if consumo_min is not None:
        validar_numero_positivo(consumo_min, "consumo_min_g")

    if consumo_max is not None:
        validar_numero_positivo(consumo_max, "consumo_max_g")

    if (
        consumo_min is not None
        and consumo_max is not None
        and consumo_min > consumo_max
    ):
        raise ErroCalculo(
            "O consumo mínimo não pode superar o consumo máximo."
        )

    return consumo_min, consumo_max


def aplicar_desperdicio(
    consumo_g,
    possui_desperdicio,
    percentual_desperdicio=0,
):
    """Aplica o percentual de desperdício ao consumo."""
    validar_numero_positivo(consumo_g, "consumo_g")

    if not isinstance(possui_desperdicio, bool):
        raise ErroCalculo(
            "possui_desperdicio deve ser verdadeiro ou falso."
        )

    validar_percentual(
        percentual_desperdicio,
        "percentual_desperdicio",
    )

    if not possui_desperdicio:
        return consumo_g

    return consumo_g * (1 + percentual_desperdicio / 100)


def calcular_consumo_direto(
    consumo_g,
    possui_desperdicio=False,
    percentual_desperdicio=0,
):
    """Calcula o consumo diário, incluindo desperdício quando aplicável."""
    consumo_total = aplicar_desperdicio(
        consumo_g,
        possui_desperdicio,
        percentual_desperdicio,
    )

    return {
        "consumo_g_dia": consumo_g,
        "consumo_total_g_dia": consumo_total,
        "desperdicio_aplicado": consumo_total - consumo_g,
    }


def validar_faixas(faixas):
    """Valida a estrutura de uma lista de faixas de peso."""
    if not isinstance(faixas, list):
        raise ErroCalculo("As faixas devem ser informadas em uma lista.")

    for faixa in faixas:
        if not isinstance(faixa, dict):
            raise ErroCalculo("Cada faixa deve ser um objeto.")

        peso_min = faixa.get("peso_min")
        peso_max = faixa.get("peso_max")

        if peso_min is not None:
            validar_numero_positivo(peso_min, "peso_min")

        if peso_max is not None:
            validar_numero_positivo(peso_max, "peso_max")

        if (
            peso_min is not None
            and peso_max is not None
            and peso_min > peso_max
        ):
            raise ErroCalculo(
                "O peso mínimo não pode superar o peso máximo."
            )


def encontrar_faixa_peso(faixas, peso_kg):
    """Retorna a única faixa compatível com o peso informado."""
    validar_numero_positivo(peso_kg, "peso_kg")
    validar_faixas(faixas)

    candidatas = []

    for faixa in faixas:
        peso_min = faixa.get("peso_min")
        peso_max = faixa.get("peso_max")

        atende_min = peso_min is None or peso_kg >= peso_min
        atende_max = peso_max is None or peso_kg <= peso_max

        if atende_min and atende_max:
            candidatas.append(faixa)

    if len(candidatas) > 1:
        raise ErroCalculo(
            "Existem várias faixas compatíveis com esse peso. "
            "Revise os limites das regras cadastradas."
        )

    return candidatas[0] if candidatas else None


def calcular_por_faixa(faixas, peso_kg):
    """Calcula o consumo usando uma faixa de peso."""
    faixa = encontrar_faixa_peso(faixas, peso_kg)

    if faixa is None:
        raise ErroCalculo(
            "Nenhuma faixa corresponde ao peso informado."
        )

    consumo = validar_numero_positivo(
        faixa.get("consumo_g"),
        "consumo_g",
    )

    return calcular_consumo_direto(
        consumo,
        faixa.get("possui_desperdicio", False),
        faixa.get("percentual_desperdicio", 0),
    )


def encontrar_faixa_por_atividade(
    faixas,
    peso_kg,
    nivel_atividade,
):
    """Busca uma faixa compatível com o peso e a atividade."""
    validar_numero_positivo(peso_kg, "peso_kg")

    if not isinstance(nivel_atividade, str) or not nivel_atividade.strip():
        raise ErroCalculo("Informe o nível de atividade.")

    validar_faixas(faixas)

    atividade = nivel_atividade.strip().casefold()
    candidatas = []

    for faixa in faixas:
        peso_min = faixa.get("peso_min")
        peso_max = faixa.get("peso_max")

        atende_min = peso_min is None or peso_kg >= peso_min
        atende_max = peso_max is None or peso_kg <= peso_max

        if atende_min and atende_max:
            candidatas.append(faixa)

    correspondentes = [
        faixa
        for faixa in candidatas
        if isinstance(faixa.get("nivel_atividade"), str)
        and faixa["nivel_atividade"].strip().casefold() == atividade
    ]

    if len(correspondentes) > 1:
        raise ErroCalculo(
            "Existem várias regras para o mesmo peso e nível de atividade."
        )

    if len(correspondentes) == 1:
        return correspondentes[0]

    genericas = [
        faixa
        for faixa in candidatas
        if faixa.get("nivel_atividade") is None
    ]

    if len(genericas) > 1:
        raise ErroCalculo(
            "Existem várias regras genéricas para o peso informado."
        )

    return genericas[0] if genericas else None


def calcular_golden(faixas, peso_kg, nivel_atividade):
    """Calcula o consumo para uma regra que considera atividade."""
    faixa = encontrar_faixa_por_atividade(
        faixas,
        peso_kg,
        nivel_atividade,
    )

    if faixa is None:
        raise ErroCalculo(
            "Nenhuma faixa corresponde ao peso e à atividade informados."
        )

    consumo = validar_numero_positivo(
        faixa.get("consumo_g"),
        "consumo_g",
    )

    return calcular_consumo_direto(consumo, False, 0)


def calcular_faixa_consumo(faixas, peso_kg):
    """Retorna o consumo mínimo e máximo de uma faixa de peso."""
    faixa = encontrar_faixa_peso(faixas, peso_kg)

    if faixa is None:
        raise ErroCalculo(
            "Nenhuma faixa corresponde ao peso informado."
        )

    consumo_min, consumo_max = validar_faixa_consumo(
        faixa.get("consumo_min_g"),
        faixa.get("consumo_max_g"),
    )

    return {
        "consumo_min_g_dia": consumo_min,
        "consumo_max_g_dia": consumo_max,
    }


def encontrar_regra_por_fase(regras, fase):
    """Encontra uma única regra pelo nome da fase."""
    if not isinstance(fase, str) or not fase.strip():
        raise ErroCalculo("Informe a fase de criação.")

    if not isinstance(regras, list):
        raise ErroCalculo("As regras devem ser informadas em uma lista.")

    fase_normalizada = fase.strip().casefold()
    correspondentes = []

    for regra in regras:
        if not isinstance(regra, dict):
            raise ErroCalculo("Cada regra deve ser um objeto.")

        nome_fase = regra.get("fase")

        if (
            isinstance(nome_fase, str)
            and nome_fase.strip().casefold() == fase_normalizada
        ):
            correspondentes.append(regra)

    if len(correspondentes) > 1:
        raise ErroCalculo(
            "Existe mais de uma regra cadastrada para essa fase."
        )

    return correspondentes[0] if correspondentes else None


def calcular_consumo_por_fase(regras, fase):
    """Calcula a faixa de consumo diário de uma fase."""
    regra = encontrar_regra_por_fase(regras, fase)

    if regra is None:
        raise ErroCalculo("Não existe regra para a fase informada.")

    consumo_min, consumo_max = validar_faixa_consumo(
        regra.get("consumo_min_g"),
        regra.get("consumo_max_g"),
    )

    return {
        "fase": fase,
        "consumo_min_g_dia": consumo_min,
        "consumo_max_g_dia": consumo_max,
    }


def calcular_inclusao_ingrediente(
    consumo_total_g,
    percentual_inclusao,
):
    """Calcula a quantidade de ingrediente conforme o percentual."""
    validar_numero_positivo(consumo_total_g, "consumo_total_g")
    validar_percentual(percentual_inclusao, "percentual_inclusao")

    quantidade = consumo_total_g * percentual_inclusao / 100

    return {
        "consumo_total_g": consumo_total_g,
        "percentual_inclusao": percentual_inclusao,
        "quantidade_ingrediente_g": quantidade,
    }


def encontrar_percentual_inclusao(percentuais, fase):
    """Busca o percentual de inclusão correspondente à fase."""
    if not isinstance(percentuais, dict):
        raise ErroCalculo(
            "Os percentuais devem ser informados em um objeto."
        )

    if not isinstance(fase, str) or not fase.strip():
        raise ErroCalculo("Informe a fase de criação.")

    chave = fase.strip().casefold()
    correspondentes = [
        valor
        for nome, valor in percentuais.items()
        if isinstance(nome, str) and nome.strip().casefold() == chave
    ]

    if not correspondentes:
        raise ErroCalculo(
            "Não existe percentual para a fase informada."
        )

    if len(correspondentes) > 1:
        raise ErroCalculo(
            "Existem chaves duplicadas para essa fase."
        )

    return validar_percentual(
        correspondentes[0],
        "percentual_inclusao",
    )


def calcular_ingrediente_por_fase(
    consumo_total_g,
    percentuais,
    fase,
):
    """Calcula a quantidade de ingrediente para uma fase."""
    percentual = encontrar_percentual_inclusao(percentuais, fase)

    return calcular_inclusao_ingrediente(
        consumo_total_g,
        percentual,
    )


def validar_faixa_peso(peso_kg, peso_min, peso_max):
    """Valida se o peso está dentro dos limites informados."""
    validar_numero_positivo(peso_kg, "peso_kg")
    validar_numero_positivo(peso_min, "peso_min")
    validar_numero_positivo(peso_max, "peso_max")

    if peso_min > peso_max:
        raise ErroCalculo(
            "O peso mínimo não pode superar o máximo."
        )

    if not peso_min <= peso_kg <= peso_max:
        raise ErroCalculo("O peso está fora da faixa configurada.")

    return True


def calcular_calopsita(peso_kg, consumo_g):
    """Calcula o consumo para calopsita com desperdício de 100%."""
    validar_faixa_peso(peso_kg, 0.06, 0.12)

    return calcular_consumo_direto(
        consumo_g,
        possui_desperdicio=True,
        percentual_desperdicio=100,
    )


def calcular_periquito(peso_kg, consumo_g):
    """Calcula o consumo para periquito com desperdício de 100%."""
    validar_faixa_peso(peso_kg, 0.03, 0.06)

    return calcular_consumo_direto(
        consumo_g,
        possui_desperdicio=True,
        percentual_desperdicio=100,
    )
