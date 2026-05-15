#!/usr/bin/env python3
"""
prospector.py — CLI principal do Prospectio
Luiz Neto | AV & Tech Solutions

Uso:
  python prospector.py coletar               # Coleta leads do Google Maps
  python prospector.py coletar --query "..." # Coleta com query específica
  python prospector.py triar                 # Triagem com IA
  python prospector.py aprovar               # Revisão e aprovação no terminal
  python prospector.py enviar                # Disparo de e-mails
  python prospector.py enviar --dry-run      # Preview sem enviar
  python prospector.py email_teste           # Envia e-mail de teste
  python prospector.py telegram              # Inicia bot Telegram
  python prospector.py listar                # Lista leads aprovados
  python prospector.py pipeline              # Executa tudo em sequência
  python prospector.py status                # Painel de status geral
"""

import asyncio
import sys
import json
import logging
import random
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def exibir_banner():
    banner = """
 ██████╗ ██████╗  ██████╗ ███████╗██████╗ ███████╗ ██████╗ ████████╗██╗ ██████╗
 ██╔══██╗██╔══██╗██╔═══██╗██╔════╝██╔══██╗██╔════╝██╔════╝ ╚══██╔══╝██║██╔═══██╗
 ██████╔╝██████╔╝██║   ██║███████╗██████╔╝█████╗  ██║         ██║   ██║██║   ██║
 ██╔═══╝ ██╔══██╗██║   ██║╚════██║██╔═══╝ ██╔══╝  ██║         ██║   ██║██║   ██║
 ██║     ██║  ██║╚██████╔╝███████║██║     ███████╗╚██████╗    ██║   ██║╚██████╔╝
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝     ╚══════╝ ╚═════╝    ╚═╝   ╚═╝ ╚═════╝
    """
    console.print(f"[bold cyan]{banner}[/bold cyan]")
    console.print("[dim]  Prospectio — Sistema de Prospecção | Luiz Neto | AV & Tech Solutions[/dim]\n")


def cmd_status():
    """Exibe painel de status geral do sistema."""
    arquivos = {
        "Raw (coletados)": "data/leads_raw.json",
        "Triados": "data/leads_triados.json",
        "Aprovados": "data/leads_aprovados.json",
    }

    table = Table(title="Status do Pipeline", box=box.ROUNDED)
    table.add_column("Etapa", style="bold white")
    table.add_column("Total", justify="center", style="cyan")
    table.add_column("Detalhes", style="dim")

    status_data = {
        "raw_total": 0,
        "raw_pendentes": 0,
        "triados_total": 0,
        "triados_quentes": 0,
        "triados_mornos": 0,
        "aprovados_total": 0,
        "aprovados_enviados": 0,
        "aprovados_aguardando": 0,
        "aprovados_sem_email": 0,
    }

    for label, arquivo in arquivos.items():
        path = Path(arquivo)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                dados = json.load(f)
            count = len(dados)

            if "aprovados" in arquivo:
                enviados = len([l for l in dados if l.get("status_envio") == "enviado"])
                aguardando = len([l for l in dados if l.get("email") and l.get("status_envio") != "enviado"])
                sem_email = len([l for l in dados if not l.get("email")])
                detalhes = f"Enviados: {enviados} | Aguardando: {aguardando} | Sem e-mail: {sem_email}"
                status_data["aprovados_total"] = count
                status_data["aprovados_enviados"] = enviados
                status_data["aprovados_aguardando"] = aguardando
                status_data["aprovados_sem_email"] = sem_email
            elif "triados" in arquivo:
                quentes = len([l for l in dados if l.get("classificacao") == "QUENTE"])
                mornos = len([l for l in dados if l.get("classificacao") == "MORNO"])
                detalhes = f"🔥 {quentes} quentes | 🌡 {mornos} mornos"
                status_data["triados_total"] = count
                status_data["triados_quentes"] = quentes
                status_data["triados_mornos"] = mornos
            else:
                pendentes = len([l for l in dados if l.get("status") == "pendente"])
                detalhes = f"Pendentes de triagem: {pendentes}"
                status_data["raw_total"] = count
                status_data["raw_pendentes"] = pendentes

            table.add_row(label, str(count), detalhes)
        else:
            table.add_row(label, "—", "[dim]arquivo não existe[/dim]")

    console.print(table)

    # Enviar notificação via Telegram
    timestamp_str = datetime.now().strftime("%H:%M:%S")
    conteudo = (
        f"📊 *Status do Pipeline*\n"
        f"• Raw: {status_data['raw_total']} leads ({status_data['raw_pendentes']} pendentes)\n"
        f"• Triados: {status_data['triados_total']} (🔥 {status_data['triados_quentes']} quentes, "
        f"🌡 {status_data['triados_mornos']} mornos)\n"
        f"• Aprovados: {status_data['aprovados_total']}\n"
        f"• Enviados: {status_data['aprovados_enviados']} | "
        f"Aguardando: {status_data['aprovados_aguardando']} | "
        f"Sem e-mail: {status_data['aprovados_sem_email']}\n"
        f"_Atualizado em {timestamp_str}_"
    )

    try:
        from core.telegram_bot import notificar_telegram
        asyncio.run(notificar_telegram(titulo="Status do Pipeline", conteudo=conteudo, emoji="📊"))
    except Exception as e:
        logger.error(f"Erro ao enviar notificação Telegram: {e}")


def cmd_coletar(query=None, max_results=10):
    from core.scraper import executar_coleta, QUERIES

    # Determine query that will be used
    q = query or random.choice(QUERIES)

    # Read file state BEFORE execution
    path = Path("data/leads_raw.json")
    leads_antes = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            leads_antes = json.load(f)
    count_antes = len(leads_antes)

    # Execute scraping
    leads = asyncio.run(executar_coleta(query=query, max_results=max_results))

    # Read file state AFTER execution
    leads_depois = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            leads_depois = json.load(f)
    count_depois = len(leads_depois)

    novos = count_depois - count_antes

    # Send Telegram notification
    timestamp_str = datetime.now().strftime("%H:%M:%S")
    conteudo = (
        f"🔍 *Coleta Concluída*\n"
        f"• Query: \"{q}\"\n"
        f"• Leads encontrados: {len(leads)}\n"
        f"• Novos: {novos}\n"
        f"• Total acumulado: {count_depois}\n"
        f"_Atualizado em {timestamp_str}_"
    )

    try:
        from core.telegram_bot import notificar_telegram
        asyncio.run(notificar_telegram(
            titulo="Coleta Concluída",
            conteudo=conteudo,
            emoji="🔍"
        ))
    except Exception as e:
        logger.error(f"Erro ao enviar notificação Telegram: {e}")


def cmd_triar():
    from core.triagem import triar_leads_pendentes
    triar_leads_pendentes()


def cmd_aprovar():
    from core.aprovacao import fluxo_aprovacao
    fluxo_aprovacao()


def cmd_enviar(dry_run=False):
    from core.email_sender import processar_fila_envio
    processar_fila_envio(dry_run=dry_run)


def cmd_email_teste():
    from core.email_sender import enviar_email_teste
    console.print("[bold cyan]📧 Enviando e-mail de teste para luizzinho@gmail.com...[/bold cyan]")
    sucesso = enviar_email_teste()
    if sucesso:
        console.print("[green]✓ E-mail de teste enviado com sucesso![/green]")
    else:
        console.print("[red]✗ Erro ao enviar e-mail de teste.[/red]")


def cmd_listar():
    from core.aprovacao import listar_aprovados
    listar_aprovados()


def cmd_telegram():
    from core.telegram_bot import start_bot_async
    asyncio.run(start_bot_async())


def cmd_pipeline(query=None):
    """Executa o pipeline completo: coletar → triar → aprovar → enviar."""
    console.print("[bold cyan]🚀 Executando pipeline completo...[/bold cyan]\n")

    console.print("[bold]Etapa 1/4 — Coleta[/bold]")
    cmd_coletar(query=query)

    console.print("\n[bold]Etapa 2/4 — Triagem por IA[/bold]")
    cmd_triar()

    console.print("\n[bold]Etapa 3/4 — Aprovação manual[/bold]")
    cmd_aprovar()

    console.print("\n[bold]Etapa 4/4 — Envio de e-mails[/bold]")
    cmd_enviar()


def exibir_ajuda():
    console.print(Panel(
        """[bold cyan]Comandos disponíveis:[/bold cyan]

  [bold]coletar[/bold]              Busca novos leads no Google Maps
    --query "..."        Busca com query específica
    --max N              Máximo de resultados (padrão: 10)

  [bold]triar[/bold]                Avalia leads pendentes com IA

  [bold]aprovar[/bold]              Revisão interativa no terminal

  [bold]enviar[/bold]               Dispara e-mails para leads aprovados
    --dry-run            Preview sem enviar

  [bold]email_teste[/bold]          Envia e-mail de teste para luizzinho@gmail.com

  [bold]listar[/bold]               Lista leads aprovados

  [bold]pipeline[/bold]             Executa tudo em sequência

  [bold]telegram[/bold]              Inicia bot Telegram (polling)

  [bold]status[/bold]               Painel de status geral

  [bold]ajuda[/bold]                Esta mensagem""",
        title="Prospectio — Ajuda",
        border_style="cyan"
    ))


def main():
    exibir_banner()

    args = sys.argv[1:]

    if not args or args[0] in ("ajuda", "help", "-h", "--help"):
        exibir_ajuda()
        return

    cmd = args[0].lower()

    if cmd == "status":
        cmd_status()

    elif cmd == "coletar":
        query = None
        max_results = 10
        if "--query" in args:
            idx = args.index("--query")
            if idx + 1 < len(args):
                query = args[idx + 1]
        if "--max" in args:
            idx = args.index("--max")
            if idx + 1 < len(args):
                max_results = int(args[idx + 1])
        cmd_coletar(query=query, max_results=max_results)

    elif cmd == "triar":
        cmd_triar()

    elif cmd == "aprovar":
        cmd_aprovar()

    elif cmd == "enviar":
        dry_run = "--dry-run" in args
        cmd_enviar(dry_run=dry_run)

    elif cmd == "email_teste":
        cmd_email_teste()

    elif cmd == "listar":
        cmd_listar()

    elif cmd == "pipeline":
        query = None
        if "--query" in args:
            idx = args.index("--query")
            if idx + 1 < len(args):
                query = args[idx + 1]
        cmd_pipeline(query=query)

    elif cmd == "telegram":
        cmd_telegram()

    else:
        console.print(f"[red]Comando desconhecido: {cmd}[/red]")
        exibir_ajuda()


if __name__ == "__main__":
    main()
