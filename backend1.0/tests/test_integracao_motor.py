import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.routes.calculos import criar_calculo
from app.schemas.calculo import CalculoCreate


class TestIntegracaoMotorCalculo(unittest.TestCase):
    def executar(self, produto, **dados):
        entrada = CalculoCreate(
            id_produto=produto.get("id_produto", 1),
            peso_animal_ou_area=dados.pop("peso_animal_ou_area", 5),
            **dados,
        )
        with patch("app.routes.calculos.consultar_produto_por_id", return_value=produto):
            return criar_calculo(entrada)

    def test_racao_regra_legada(self):
        produto = {
            "id_produto": 1, "tipo": "racao", "peso_embalagem": 1,
            "regra_dosagem": {"g_por_kg_dia": 15},
        }
        resposta = self.executar(produto, peso_animal_ou_area=2)
        self.assertEqual(resposta["tipo"], "racao")
        self.assertEqual(resposta["resultado"]["dose_diaria_g"], 30)
        self.assertEqual(resposta["resultado"]["duracao_estimada_dias"], 33)

    def test_racao_por_faixa_e_atividade(self):
        produto = {
            "id_produto": 2, "tipo": "racao", "peso_embalagem": 3,
            "regra_dosagem": {"faixas": [
                {"peso_min": 1, "peso_max": 10, "nivel_atividade": "ativo", "consumo_g": 75},
            ]},
        }
        resposta = self.executar(produto, peso_animal_ou_area=5, nivel_atividade="ativo")
        self.assertEqual(resposta["resultado"]["dose_diaria_g"], 75)

    def test_racao_faixa_de_consumo(self):
        produto = {
            "id_produto": 3, "tipo": "racao", "peso_embalagem": 3,
            "regra_dosagem": {"faixas": [
                {"peso_min": 1, "peso_max": 10, "consumo_min_g": 50, "consumo_max_g": 80},
            ]},
        }
        resposta = self.executar(produto, peso_animal_ou_area=5)
        self.assertEqual(resposta["resultado"]["consumo_min_g_dia"], 50)
        self.assertEqual(resposta["resultado"]["consumo_max_g_dia"], 80)
        self.assertEqual(resposta["resultado"]["duracao_minima_embalagem_dias"], 37)
        self.assertEqual(resposta["resultado"]["duracao_maxima_embalagem_dias"], 60)

    def test_racao_por_fase(self):
        produto = {
            "id_produto": 4, "tipo": "racao", "peso_embalagem": 20,
            "regra_dosagem": {"regras_fase": [
                {"fase": "postura", "consumo_min_g": 100, "consumo_max_g": 120},
            ]},
        }
        resposta = self.executar(produto, fase="postura")
        self.assertEqual(resposta["resultado"]["fase"], "postura")
        self.assertEqual(resposta["resultado"]["consumo_max_g_dia"], 120)

    def test_endpoint_medicamento_usa_tipo_calculo_do_schema(self):
        produto = {"id_produto": 6, "tipo": "medicamento"}
        resposta = self.executar(
            produto,
            peso_animal_ou_area=10,
            dose_por_kg=2,
            concentracao=5,
            tipo_calculo="liquido",
        )
        self.assertEqual(resposta["tipo"], "medicamento")
        self.assertEqual(resposta["resultado"]["dose_calculada"], 20)
        self.assertEqual(resposta["resultado"]["quantidade_por_dose"], 4)
        self.assertEqual(resposta["resultado"]["unidade"], "mL")

    def test_tipo_calculo_esta_no_schema(self):
        entrada = CalculoCreate(id_produto=1, peso_animal_ou_area=5, tipo_calculo="liquido")
        self.assertEqual(entrada.tipo_calculo, "liquido")

    def test_produto_sem_regra_valida_retorna_erro_http(self):
        produto = {"id_produto": 5, "tipo": "racao", "peso_embalagem": 1, "regra_dosagem": {}}
        with patch(
            "app.routes.calculos.consultar_regras_por_produto",
            return_value=[],
        ):
            with self.assertRaises(HTTPException) as contexto:
                self.executar(produto)
        self.assertEqual(contexto.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
