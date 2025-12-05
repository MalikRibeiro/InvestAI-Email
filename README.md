# Invest-AI 2.0

### Seu Gestor de Portfólio Inteligente na Nuvem

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/MalikRibeiro/Invest-AI-Email/daily_report.yml)
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

O **Invest-AI 2.0** é um sistema autônomo de análise e gestão de
portfólio que combina automação financeira, dados em tempo real e
Inteligência Artificial (Google Gemini). Ele gera relatórios diários
inteligentes, com fundamentos, notícias, rebalanceamento e recomendações
de aporte.

------------------------------------------------------------------------

## Principais Recursos

### Gestão via Google Sheets

Altere sua carteira editando uma planilha simples. O sistema lê tudo
automaticamente.

### IA Analyst (Gemini Pro)

Analisa fundamentos, explica quedas, identifica riscos e contextualiza o
cenário macroeconômico.

### Contexto de Mercado

Coleta automática das principais notícias financeiras do dia.

### Dados em Tempo Real

-   Yahoo Finance (cotações e indicadores)\
-   Banco Central (Selic, CDI, PTAX)

### Sugestão de Aporte

Algoritmo determina onde investir para manter as metas de alocação.

### Relatório Diário

Enviado em HTML com patrimônio, variação, gráficos, análise da IA e
rebalanceamento.

### Automação Total

Executa sozinho via GitHub Actions às 13:00 (horário de Brasília).

------------------------------------------------------------------------

## Configuração da Carteira (Google Sheets)

  Ticker       Quantidade   Categoria    Meta
  ------------ ------------ ------------ ------
  BBAS3.SA     100          BR_STOCKS    10%
  HCTR11.SA    50           FIIS         5%
  IVVB11.SA    20           ETFS         15%
  AAPL         5            US_STOCKS    5%
  O            10           US_REITS     5%
  USDT-USD     50.5         CRYPTO       2%
  RDB-NUBANK   2150.55      RENDA_FIXA   35%

------------------------------------------------------------------------

## Instalação Local

### Requisitos

Python 3.12+, Conta Google, Gmail com senha de app.

### 1. Clonar e instalar

``` bash
git clone https://github.com/SEU_USUARIO/Invest-AI.git
cd Invest-AI
pip install -r requirements.txt
```

### 2. Criar `.env`

    EMAIL_SENDER=...
    EMAIL_PASSWORD=...
    EMAIL_RECEIVER=...
    GEMINI_API_KEY=...
    LOG_LEVEL=INFO

### 3. Rodar

``` bash
python main.py
```

------------------------------------------------------------------------

## Automação via GitHub Actions

Secrets necessários:

-   EMAIL_SENDER\
-   EMAIL_PASSWORD\
-   EMAIL_RECEIVER\
-   GEMINI_API_KEY

Workflow: `.github/workflows/daily_report.yml`\
Executa dias úteis às 16:00 UTC.

------------------------------------------------------------------------

## Estrutura do Projeto

    .
    ├── main.py
    ├── config/
    ├── src/
    ├── data/
    └── .github/workflows/

------------------------------------------------------------------------

## Segurança

Nunca faça commit do `.env`.\
A planilha publicada deve conter apenas dados de carteira.

------------------------------------------------------------------------

## Licença

Projeto sob licença MIT.
