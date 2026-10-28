# CIMDP Backend 1.0

API REST do CIMDP desenvolvida com FastAPI, com consultas ao Supabase e motor de cálculo para rações, ingredientes, adubos e medicamentos.

## Estrutura

- `main.py`: inicialização da API.
- `app/routes/`: endpoints de produtos e cálculos.
- `app/database/supabase.py`: comunicação com o Supabase.
- `app/schemas/`: validação dos dados de entrada e saída.
- `app/services/`: regras e funções de cálculo.
- `tests/`: testes automatizados do motor e da integração simulada.

## Configuração local

1. Instale Python 3.10 ou superior.
2. Crie e ative um ambiente virtual.
3. Instale as dependências:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Copie `.env.example` para `.env` e preencha `SUPABASE_URL` e `SUPABASE_KEY` com os valores do seu projeto. Não compartilhe o `.env`.
5. Inicie a API:

   ```bash
   uvicorn main:app --reload
   ```

6. Acesse a documentação interativa em `http://127.0.0.1:8000/docs`.

## Testes

Execute a partir da pasta do projeto:

```bash
python -m unittest discover -s tests -v
```

Os testes de integração simulam as consultas ao produto; eles não confirmam que as tabelas ou regras reais já existem no Supabase. O fluxo completo deverá ser validado quando os produtos e regras estiverem cadastrados.

## Observações

- O cálculo de medicamentos depende de dose e concentração com unidades compatíveis e previamente confirmadas.
- Este backend é uma versão de trabalho. As regras de negócio devem ser validadas com as tabelas oficiais antes de uso real.
- O arquivo `.env` e os ambientes virtuais não são incluídos no pacote.
