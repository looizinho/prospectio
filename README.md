# Prospectio — Sistema de Prospeccao Automatizada
**Luiz Neto | AV & Tech Solutions**

## Python com Mise (inicio rapido)

Este projeto fixa o Python em `3.12.13` via `mise.toml`.

```bash
# 1) Instale o mise (se ainda nao tiver)
curl https://mise.run | sh

# 2) Entre na pasta do projeto
cd /Users/luizinho/Development/prospectio

# 3) Instale/ative a versao de Python declarada
mise install
mise trust

# 4) Confirme a versao ativa
mise exec -- python --version
```

Dica: para executar comandos com a versao do `mise`, prefira `mise exec -- <comando>`.

---

## Requisitos

- Python 3.12.13 (via `mise`)
- `pip`
- Playwright + Chromium
- Conta Google (Gmail com App Password)
- Chave da API Anthropic

---

## Instalacao

### 1. Crie e ative o ambiente virtual

```bash
mise exec -- python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\\Scripts\\activate      # Windows
```

### 2. Instale as dependencias

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure as variaveis de ambiente

```bash
cp .env.example .env
```

Preencha no `.env`:
- `ANTHROPIC_API_KEY`
- `EMAIL_REMETENTE`
- `EMAIL_SENHA_APP`
- `EMAIL_NOME_REMETENTE`

Opcionais (Telegram):
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

---

## Uso

### Modo interativo (recomendado)

```bash
python prospector.py
```

No prompt interativo, use comandos com `/` (ex.: `/status`, `/coletar`, `/pipeline`).

## Implementacao do TUI (commit `717905c`, merge `8c0bebe`)

O `prospector.py` foi transformado para operar em dois modos:

- `main_interactive()` quando executado sem argumentos (`python prospector.py`)
- `main_single_command()` para manter compatibilidade com comandos via `sys.argv`

Detalhes da implementacao:

- `parse_command(input_str)`:
  - Exige prefixo `/` no comando
  - Usa `shlex.split` para suportar aspas em argumentos
  - Interpreta flags no formato `--flag` e `--flag valor`
  - Converte `--dry-run` para `dry_run=True`

- `execute_command(parsed)`:
  - Faz o dispatch para `cmd_status`, `cmd_coletar`, `cmd_triar`, `cmd_aprovar`, `cmd_enviar`, `cmd_pipeline`, etc.
  - Implementa comando `/sair` para encerrar o loop
  - Exibe erro amigavel para comando desconhecido e orienta uso de `/ajuda`

- Loop TUI:
  - Prompt fixo `prospector> `
  - Trata `KeyboardInterrupt` e `EOFError` para encerramento limpo
  - Mantem o banner e painel de ajuda com comandos no formato `/comando`

Exemplos no TUI:

```text
/coletar "agencia de marketing" --max 20
/enviar --dry-run
/pipeline --query "produtora de eventos"
/ajuda
/sair
```

### Comandos diretos

```bash
python prospector.py status
python prospector.py coletar
python prospector.py coletar --query "produtora de eventos"
python prospector.py coletar --query "agencia de marketing" --max 20
python prospector.py triar
python prospector.py aprovar
python prospector.py enviar
python prospector.py enviar --dry-run
python prospector.py email_teste
python prospector.py listar
python prospector.py pipeline
python prospector.py telegram
```

---

## Fluxo de trabalho

```text
coletar -> triar -> aprovar -> enviar
```

Atalho para executar em sequencia:

```bash
python prospector.py pipeline
```

---

## Estrutura de arquivos

```text
prospectio/
|-- prospector.py
|-- requirements.txt
|-- mise.toml
|-- .env.example
|-- core/
|   |-- scraper.py
|   |-- triagem.py
|   |-- aprovacao.py
|   |-- email_sender.py
|   `-- telegram_bot.py
`-- data/
    |-- leads_raw.json
    |-- leads_triados.json
    `-- leads_aprovados.json
```

---

## Observacoes importantes

- Triagem com IA roda de forma sequencial para reduzir risco de rate limit.
- Scraping no Google Maps deve ser usado com moderacao.
- Para Gmail, use App Password (nao a senha normal da conta).
- O comando `status` e o fluxo de `coletar` podem enviar notificacoes no Telegram quando configurado.
