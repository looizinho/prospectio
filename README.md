\# Prospector — Sistema de Prospecção Automatizada
**Luiz Neto | AV & Tech Solutions**

---

## Requisitos

- Python 3.11+
- pip
- Conta Google (Gmail com App Password)
- Chave da API Anthropic (gratuita com limites)

---

## Instalação

### 1. Clone ou copie o projeto para sua máquina

```bash
cd ~/projetos
# copie a pasta prospector aqui
cd prospector
```

### 2. Crie e ative o ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\\Scripts\\activate         # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure as variáveis de ambiente

```bash
cp .env.example .env
nano .env   # ou use seu editor preferido
```

Preencha:
- `ANTHROPIC_API_KEY` — https://console.anthropic.com
- `EMAIL_REMETENTE` — seu Gmail
- `EMAIL_SENHA_APP` — App Password do Google (não é sua senha normal!)

#### Como gerar App Password no Google:
1. Acesse: https://myaccount.google.com/security
2. Ative verificação em 2 etapas (obrigatório)
3. Pesquise \"App Passwords\" ou acesse: https://myaccount.google.com/apppasswords
4. Crie um app password para \"Mail\"
5. Copie a senha de 16 dígitos gerada

---

## Uso

### Comandos principais

```bash
# Ver status geral do pipeline
python prospector.py status

# Pipeline completo (recomendado para uso diário)
python prospector.py pipeline

# Ou etapa por etapa:
python prospector.py coletar
python prospector.py triar
python prospector.py aprovar
python prospector.py enviar

# Preview de e-mails sem enviar
python prospector.py enviar --dry-run

# Busca com query específica
python prospector.py coletar --query \"produtora de eventos corporativos São Paulo\"

# Lista todos os leads aprovados
python prospector.py listar
```

---

## Fluxo de Trabalho Diário

```
1. python prospector.py coletar     → Busca ~10 novos leads
2. python prospector.py triar       → IA avalia e classifica
3. python prospector.py aprovar     → Você revisa e aprova
4. python prospector.py enviar      → Dispara e-mails personalizados
```

Tempo estimado por ciclo: **15-20 minutos**

---

## Estrutura de Arquivos

```
prospector/
├── prospector.py          ← CLI principal (ponto de entrada)
├── requirements.txt
├── .env                   ← suas credenciais (NÃO commitar)
├── .env.example
├── core/
│   ├── scraper.py         ← Coleta do Google Maps
│   ├── triagem.py         ← Avaliação por IA
│   ├── aprovacao.py       ← Interface de aprovação no terminal
│   └── email_sender.py    ← Geração e envio de e-mails
├── data/
│   ├── leads_raw.json     ← Leads coletados (brutos)
│   ├── leads_triados.json ← Leads avaliados pela IA
│   └── leads_aprovados.json ← Leads aprovados por você
└── logs/
```

---

## Limitações e Cuidados

- **Google Maps scraping**: O Google pode bloquear requisições excessivas. Use com moderação (10/dia é seguro).
- **Anthropic API gratuita**: Tem limite de tokens/min. O sistema já respeita isso.
- **Gmail**: Limite de 500 e-mails/dia com conta comum.
- **LGPD**: Ao contatar empresas B2B por e-mail com proposta comercial legítima, você está dentro do permitido. Mantenha opt-out claro no e-mail.

---

## Próximas Funcionalidades (Roadmap)

- [ ] Bot Telegram para aprovação pelo celular
- [ ] Scraping do LinkedIn
- [ ] Scraping do Instagram por hashtags
- [ ] Integração com WhatsApp (quando a API oficial ficar acessível)
- [ ] Dashboard de métricas (taxa de resposta, conversão)
- [ ] Agendamento automático (cron job diário)

