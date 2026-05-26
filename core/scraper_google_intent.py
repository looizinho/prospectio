"""
Google Intent Scraper - Coleta leads por intenção de busca (Google Trends + SERP).
Interface 100% TUI (Rich), sem argumentos de CLI.
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Set

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich import box

try:
    from pytrends.request import TrendReq
    HAS_PYTRENDS = True
except ImportError:
    HAS_PYTRENDS = False

from core.scraper import salvar_leads

console = Console()

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

KEYWORDS_PADRAO = [
    "streaming evento",
    "audiovisual corporativo",
    "produção evento online",
    "conferência virtual",
    "evento híbrido"
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

TIMEOUT_URL = 5
DELAY_BUSCA_GOOGLE = 10
MAX_BUSCAS_GOOGLE = 10

DATA_DIR = Path("data")
LEADS_RAW_FILE = DATA_DIR / "leads_raw.json"


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def get_trending_keywords() -> List[str]:
    """
    Busca keywords em alta demanda usando pytrends (últimos 7 dias).
    Retorna top 5 keywords ou keywords padrão se falhar.
    """
    if not HAS_PYTRENDS:
        console.print(
            "[yellow]⚠️  pytrends não instalado. Usando keywords padrão.[/yellow]"
        )
        return KEYWORDS_PADRAO

    try:
        with console.status("[cyan]Buscando keywords em tendência...[/cyan]"):
            pytrends = TrendReq(hl="pt-BR", tz=360)

            # Busca interesse de cada keyword
            interesse = {}
            for keyword in KEYWORDS_PADRAO:
                try:
                    pytrends.build_payload(
                        [keyword],
                        cat=0,
                        timeframe="today 7-d",
                        geo="BR"
                    )
                    dados = pytrends.interest_over_time()
                    if not dados.empty:
                        crescimento = float(dados.iloc[-1, 0] - dados.iloc[0, 0])
                        interesse[keyword] = crescimento
                    else:
                        interesse[keyword] = 0
                except Exception as e:
                    console.print(f"[yellow]Erro ao buscar '{keyword}': {e}[/yellow]")
                    interesse[keyword] = 0

                time.sleep(1)

            # Retorna top 5 ordenado por crescimento (decrescente)
            top_5 = sorted(
                interesse.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            return [kw for kw, _ in top_5]

    except Exception as e:
        console.print(
            f"[yellow]⚠️  Erro ao buscar trends: {e}. Usando keywords padrão.[/yellow]"
        )
        return KEYWORDS_PADRAO


def scrape_google_serp(keyword: str, max_results: int = 5) -> List[str]:
    """
    Scrapa Google SERP para uma keyword e extrai URLs dos primeiros resultados.
    Retorna lista de URLs (máximo max_results).
    """
    headers = {"User-Agent": USER_AGENT}

    try:
        # Google com delay e parâmetros seguros
        params = {
            "q": keyword,
            "num": max_results,
            "hl": "pt-BR"
        }

        response = requests.get(
            "https://www.google.com/search",
            params=params,
            headers=headers,
            timeout=TIMEOUT_URL
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        urls = []

        # Extrai URLs dos resultados (divs com classe 'g')
        for g in soup.find_all("div", class_="g")[:max_results]:
            try:
                link = g.find("a", href=True)
                if link and link["href"].startswith("http"):
                    url = link["href"]
                    # Remove parâmetros de rastreamento do Google
                    url = url.split("&")[0] if "&" in url else url
                    if url not in urls:
                        urls.append(url)
            except (AttributeError, KeyError):
                continue

        return urls

    except requests.Timeout:
        console.print(f"[yellow]⚠️  Timeout ao buscar '{keyword}'[/yellow]")
        return []
    except Exception as e:
        console.print(f"[yellow]⚠️  Erro ao scraper SERP '{keyword}': {e}[/yellow]")
        return []


def extract_contacts_from_url(url: str) -> Optional[Dict]:
    """
    Extrai contatos (emails, telefones) e informações de empresa da URL.
    Retorna dict com {url, empresa, emails[], telefones[], titulo}
    ou None se falhar.
    """
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        text = response.text

        # Extrai emails (padrão: \w+@\w+\.\w+)
        emails = set()
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        for match in re.finditer(email_pattern, text):
            email = match.group(0)
            # Filtra spam patterns
            if not any(x in email.lower() for x in ["noreply", "notification", "no-reply"]):
                emails.add(email)

        # Extrai telefones brasileiros: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
        telefones = set()
        telefone_pattern = r"\(\d{2}\)\s?9?\d{4}-\d{4}"
        for match in re.finditer(telefone_pattern, text):
            telefones.add(match.group(0))

        # Extrai nome da empresa
        empresa = None

        # Tenta H1
        h1 = soup.find("h1")
        if h1:
            empresa = h1.get_text(strip=True)

        # Tenta title tag
        if not empresa and soup.find("title"):
            empresa = soup.find("title").get_text(strip=True)

        # Tenta og:site_name
        if not empresa:
            og_site = soup.find("meta", property="og:site_name")
            if og_site and og_site.get("content"):
                empresa = og_site["content"]

        # Se ainda não tem, usa domínio
        if not empresa:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            empresa = parsed.netloc.replace("www.", "")

        # Apenas retorna se encontrou contatos
        if emails or telefones:
            return {
                "url": url,
                "empresa": empresa,
                "emails": list(emails),
                "telefones": list(telefones),
                "titulo": soup.find("title").get_text(strip=True) if soup.find("title") else empresa
            }

        return None

    except requests.Timeout:
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        return None
    except Exception as e:
        return None


def carregar_urls_existentes() -> Set[str]:
    """Carrega URLs já presentes em leads_raw.json para deduplicação."""
    if not LEADS_RAW_FILE.exists():
        return set()

    try:
        with open(LEADS_RAW_FILE, "r", encoding="utf-8") as f:
            leads = json.load(f)
            if isinstance(leads, list):
                return {lead.get("website") for lead in leads if "website" in lead}
            return set()
    except Exception:
        return set()


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL COM TUI
# ═══════════════════════════════════════════════════════════════════════════════

def fluxo_coleta_por_intent():
    """
    Fluxo principal de coleta por intenção de busca (TUI com Rich).
    Menu interativo, progress bars, resultado final com painel.
    """

    console.clear()
    console.print(
        Panel(
            "[cyan bold]🔍  Coleta por Intenção de Busca[/cyan bold]\n"
            "[dim]Busca keywords em alta demanda + scraping Google SERP[/dim]",
            expand=False,
            border_style="cyan"
        )
    )

    # ───────────────────────────────────────────────────────────────────────────
    # MENU: Escolher fonte de keywords
    # ───────────────────────────────────────────────────────────────────────────

    console.print("\n[bold]Escolha a fonte de keywords:[/bold]")
    console.print("  [1] Usar keywords em tendência (Google Trends)")
    console.print("  [2] Inserir keywords customizadas")
    console.print("  [3] Cancelar")

    while True:
        escolha = Prompt.ask("Opção", choices=["1", "2", "3"], default="1")

        if escolha == "3":
            console.print("[yellow]Operação cancelada.[/yellow]")
            return

        if escolha == "1":
            keywords = get_trending_keywords()

            # Exibe tabela de keywords
            table = Table(title="Top 5 Keywords em Tendência", box=box.ROUNDED)
            table.add_column("Posição", style="cyan")
            table.add_column("Keyword", style="green")

            for i, kw in enumerate(keywords, 1):
                table.add_row(str(i), kw)

            console.print(table)

            if not Confirm.ask("[bold]Usar estas keywords?[/bold]", default=True):
                console.print("[yellow]Retornando ao menu...[/yellow]\n")
                continue

            break

        elif escolha == "2":
            input_kw = Prompt.ask(
                "Digite keywords",
                default="streaming evento, audiovisual corporativo"
            )
            keywords = [kw.strip() for kw in input_kw.split(",")]
            keywords = [kw for kw in keywords if kw]

            if not keywords:
                console.print("[red]Nenhuma keyword fornecida![/red]")
                continue

            console.print(f"[green]✓ {len(keywords)} keyword(s) carregadas.[/green]")
            break

    # ───────────────────────────────────────────────────────────────────────────
    # PERGUNTA: Quantos resultados Google por keyword?
    # ───────────────────────────────────────────────────────────────────────────

    while True:
        try:
            max_results_str = Prompt.ask(
                "Quantos resultados Google por keyword? (1-10)",
                default="5"
            )
            max_results = int(max_results_str)
            if 1 <= max_results <= 10:
                break
            console.print("[red]Digite um número entre 1 e 10![/red]")
        except ValueError:
            console.print("[red]Entrada inválida![/red]")

    # ───────────────────────────────────────────────────────────────────────────
    # COLETA
    # ───────────────────────────────────────────────────────────────────────────

    urls_existentes = carregar_urls_existentes()
    leads_coletados = []
    erros = []
    buscas_realizadas = 0

    console.print(f"\n[bold cyan]Iniciando coleta com {len(keywords)} keyword(s)...[/bold cyan]\n")

    for kw_idx, keyword in enumerate(keywords, 1):
        if buscas_realizadas >= MAX_BUSCAS_GOOGLE:
            console.print(
                f"\n[yellow]⚠️  Limite de {MAX_BUSCAS_GOOGLE} buscas Google atingido.[/yellow]"
            )
            break

        # Busca SERP
        console.print(
            f"\n[cyan]Keyword {kw_idx}/{len(keywords)}: '{keyword}'[/cyan]"
        )

        with console.status(f"[cyan]Buscando resultados Google...[/cyan]"):
            urls = scrape_google_serp(keyword, max_results)
            buscas_realizadas += 1

        if not urls:
            console.print(f"  [yellow]⚠️  Nenhuma URL encontrada[/yellow]")
            continue

        console.print(f"  [green]✓ {len(urls)} URL(s) encontrada(s)[/green]")

        # Extrai contatos de cada URL
        for url in urls:
            # Deduplicação
            if url in urls_existentes:
                console.print(f"    [dim]⊘ {url[:60]} (já existe)[/dim]")
                continue

            with console.status(f"[cyan]Extraindo contatos de {url[:50]}...[/cyan]"):
                contatos = extract_contacts_from_url(url)

            if contatos:
                console.print(
                    f"    [green]✓ {url[:60]}[/green] "
                    f"({len(contatos['emails'])} email(s), {len(contatos['telefones'])} fone(s))"
                )

                # Cria lead
                lead = {
                    "nome": contatos["empresa"],
                    "website": url,
                    "emails": contatos["emails"],
                    "telefones": contatos["telefones"],
                    "categoria": "Audiovisual / Eventos",
                    "endereco": "—",
                    "rating": "—",
                    "fonte": "Google Intent",
                    "keyword_origem": keyword,
                    "status": "pendente"
                }

                leads_coletados.append(lead)
                urls_existentes.add(url)
            else:
                console.print(f"    [yellow]⚠️  {url[:60]} (sem contatos)[/yellow]")
                erros.append((url, "Sem contatos"))

        # Delay entre buscas
        if buscas_realizadas < MAX_BUSCAS_GOOGLE and kw_idx < len(keywords):
            time.sleep(DELAY_BUSCA_GOOGLE)

    # ───────────────────────────────────────────────────────────────────────────
    # PAINEL DE RESULTADO FINAL
    # ───────────────────────────────────────────────────────────────────────────

    resumo_texto = (
        f"[cyan]Keywords processadas:[/cyan] {len(keywords)}\n"
        f"[cyan]Buscas Google realizadas:[/cyan] {buscas_realizadas}\n"
        f"[cyan]Leads novos coletados:[/cyan] [green]{len(leads_coletados)}[/green]\n"
        f"[cyan]Erros/timeouts:[/cyan] {len(erros)}"
    )

    console.print(
        Panel(
            resumo_texto,
            title="[bold]📊 Resultado Final[/bold]",
            border_style="green",
            expand=False
        )
    )

    if not leads_coletados:
        console.print("[yellow]Nenhum lead novo para salvar.[/yellow]")
        return

    # ───────────────────────────────────────────────────────────────────────────
    # CONFIRMAÇÃO E SALVAMENTO
    # ───────────────────────────────────────────────────────────────────────────

    if Confirm.ask("\n[bold]Confirmar e salvar leads?[/bold]", default=True):
        try:
            # Chama salvar_leads do scraper.py
            salvar_leads(leads_coletados)
            console.print(
                f"\n[green]✓ {len(leads_coletados)} lead(s) novo(s) "
                f"salvos em leads_raw.json[/green]"
            )
        except Exception as e:
            console.print(f"[red]Erro ao salvar leads: {e}[/red]")
    else:
        console.print("[yellow]Leads descartados.[/yellow]")


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    fluxo_coleta_por_intent()
