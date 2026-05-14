"""
aprovacao.py — Interface de aprovação de leads via terminal (rich UI)
"""

import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box
from rich.text import Text

console = Console()


CORES_CLASSIFICACAO = {
    "QUENTE": "bold red",
    "MORNO": "bold yellow",
    "FRIO": "bold blue",
}

EMOJIS_CLASSIFICACAO = {
    "QUENTE": "🔥",
    "MORNO": "🌡 ",
    "FRIO": "❄️ ",
}


def exibir_lead(lead: dict, indice: int, total: int):
    """
    Exibe um lead de forma visual no terminal para revisão.
    """
    classificacao = lead.get("classificacao", "MORNO")
    cor = CORES_CLASSIFICACAO.get(classificacao, "white")
    emoji = EMOJIS_CLASSIFICACAO.get(classificacao, "•")

    titulo = f"{emoji} Lead {indice}/{total} — Score: {lead.get('score', '?')}/10 — {classificacao}"

    conteudo = f"""
[bold white]{lead.get('nome', 'N/A')}[/bold white]
[dim]{lead.get('categoria', 'N/A')}[/dim]

📍 {lead.get('endereco', 'N/A')}
📞 {lead.get('telefone', 'N/A')}
🌐 {lead.get('website', 'N/A')}
⭐ Rating: {lead.get('rating', 'N/A')}

[bold cyan]Análise da IA:[/bold cyan]
  Justificativa:  {lead.get('justificativa', 'N/A')}
  Dor provável:   {lead.get('dor_provavel', 'N/A')}

[bold green]Sugestão de abordagem:[/bold green]
  {lead.get('abordagem_sugerida', 'N/A')}
"""

    console.print(Panel(
        conteudo,
        title=f"[{cor}]{titulo}[/{cor}]",
        border_style=cor,
        padding=(1, 2)
    ))


def fluxo_aprovacao(
    arquivo_triados: str = "data/leads_triados.json",
    arquivo_aprovados: str = "data/leads_aprovados.json"
):
    """
    Apresenta leads triados um a um para aprovação manual no terminal.
    """
    path_triados = Path(arquivo_triados)
    if not path_triados.exists():
        console.print("[red]Nenhum lead triado encontrado. Execute a triagem primeiro.[/red]")
        return []

    with open(path_triados, "r", encoding="utf-8") as f:
        todos = json.load(f)

    # Filtra apenas pendentes de aprovação
    pendentes = [
        l for l in todos
        if l.get("status_aprovacao") not in ("aprovado", "rejeitado", "enviado")
    ]

    if not pendentes:
        console.print("[yellow]Nenhum lead aguardando aprovação.[/yellow]")
        return []

    console.print(f"\n[bold cyan]📋 {len(pendentes)} leads aguardando sua aprovação[/bold cyan]")
    console.print("[dim]Comandos: [S] Aprovar  [N] Rejeitar  [P] Pular  [Q] Sair[/dim]\n")

    aprovados_sessao = []
    rejeitados_sessao = []

    for i, lead in enumerate(pendentes, 1):
        exibir_lead(lead, i, len(pendentes))

        while True:
            resposta = Prompt.ask(
                "[bold]Decisão[/bold]",
                choices=["s", "n", "p", "q"],
                default="p"
            ).lower()

            if resposta == "s":
                # Pede o e-mail se não tiver
                if not lead.get("email"):
                    email = Prompt.ask("  📧 E-mail do contato (deixe em branco para pular)")
                    if email:
                        lead["email"] = email.strip()

                lead["status_aprovacao"] = "aprovado"
                aprovados_sessao.append(lead)
                console.print("[green]  ✓ Lead aprovado![/green]\n")
                break

            elif resposta == "n":
                motivo = Prompt.ask("  Motivo da rejeição (opcional)", default="")
                lead["status_aprovacao"] = "rejeitado"
                lead["motivo_rejeicao"] = motivo
                rejeitados_sessao.append(lead)
                console.print("[red]  ✗ Lead rejeitado.[/red]\n")
                break

            elif resposta == "p":
                console.print("[dim]  → Pulado.[/dim]\n")
                break

            elif resposta == "q":
                console.print("\n[yellow]Sessão encerrada.[/yellow]")
                _salvar_decisoes(todos, path_triados, arquivo_aprovados, aprovados_sessao)
                _exibir_resumo(aprovados_sessao, rejeitados_sessao)
                return aprovados_sessao

    _salvar_decisoes(todos, path_triados, arquivo_aprovados, aprovados_sessao)
    _exibir_resumo(aprovados_sessao, rejeitados_sessao)
    return aprovados_sessao


def _salvar_decisoes(todos, path_triados, arquivo_aprovados, aprovados):
    """Persiste decisões de aprovação nos arquivos JSON."""
    with open(path_triados, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

    path_aprov = Path(arquivo_aprovados)
    path_aprov.parent.mkdir(exist_ok=True)

    existentes = []
    if path_aprov.exists():
        with open(path_aprov, "r", encoding="utf-8") as f:
            existentes = json.load(f)

    nomes_existentes = {l.get("nome", "").lower() for l in existentes}
    novos = [l for l in aprovados if l.get("nome", "").lower() not in nomes_existentes]

    with open(path_aprov, "w", encoding="utf-8") as f:
        json.dump(existentes + novos, f, ensure_ascii=False, indent=2)


def _exibir_resumo(aprovados, rejeitados):
    """Exibe resumo da sessão de aprovação."""
    console.print(f"\n[bold]📊 Resumo da sessão:[/bold]")
    console.print(f"  [green]Aprovados: {len(aprovados)}[/green]")
    console.print(f"  [red]Rejeitados: {len(rejeitados)}[/red]")

    if aprovados:
        console.print("\n[bold cyan]Leads aprovados aguardando envio:[/bold cyan]")
        for l in aprovados:
            email = l.get("email", "[sem e-mail]")
            console.print(f"  • {l.get('nome')} — {email}")


def listar_aprovados(arquivo_aprovados: str = "data/leads_aprovados.json"):
    """Lista todos os leads aprovados em formato de tabela."""
    path = Path(arquivo_aprovados)
    if not path.exists():
        console.print("[yellow]Nenhum lead aprovado ainda.[/yellow]")
        return

    with open(path, "r", encoding="utf-8") as f:
        leads = json.load(f)

    if not leads:
        console.print("[yellow]Lista de aprovados está vazia.[/yellow]")
        return

    table = Table(
        title="Leads Aprovados",
        box=box.ROUNDED,
        show_lines=True
    )
    table.add_column("Nome", style="bold white", max_width=30)
    table.add_column("Score", justify="center", style="cyan")
    table.add_column("Classif.", justify="center")
    table.add_column("E-mail", style="green")
    table.add_column("Status", justify="center")

    for lead in leads:
        classif = lead.get("classificacao", "?")
        cor = CORES_CLASSIFICACAO.get(classif, "white")
        status = lead.get("status_envio", "aguardando")

        table.add_row(
            lead.get("nome", "N/A")[:30],
            str(lead.get("score", "?")),
            f"[{cor}]{classif}[/{cor}]",
            lead.get("email", "—"),
            status
        )

    console.print(table)


if __name__ == "__main__":
    fluxo_aprovacao()
