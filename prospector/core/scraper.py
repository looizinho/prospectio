"""
scraper.py — Coleta leads do Google Maps via Playwright
"""

import asyncio
import json
import time
import random
from pathlib import Path
from playwright.async_api import async_playwright
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


QUERIES = [
    "empresa organizadora de eventos",
    "produtora de eventos corporativos",
    "locadora de equipamentos audiovisuais",
    "empresa de eventos empresariais",
    "produção de eventos São Paulo",
    "produção de eventos Rio de Janeiro",
    "produção de eventos Belo Horizonte",
    "produção de eventos Brasília",
    "produção de eventos Curitiba",
    "produção de eventos Porto Alegre",
]


async def scrape_google_maps(query: str, max_results: int = 10) -> list[dict]:
    """
    Faz scraping de leads no Google Maps para uma query específica.
    Retorna lista de dicts com dados do negócio.
    """
    leads = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(2)

        # Rola o painel lateral para carregar mais resultados
        try:
            panel = page.locator('div[role="feed"]')
            for _ in range(5):
                await panel.evaluate("el => el.scrollTop += 800")
                await asyncio.sleep(1.5)
        except Exception:
            pass

        # Coleta todos os cards de resultado
        cards = await page.query_selector_all('div[jsaction*="mouseover:pane"]')

        for card in cards[:max_results]:
            try:
                await card.click()
                await asyncio.sleep(2)

                lead = await _extrair_dados_do_painel(page)
                if lead and lead.get("nome"):
                    leads.append(lead)

            except Exception as e:
                console.print(f"[yellow]Aviso ao processar card: {e}[/yellow]")
                continue

        await browser.close()

    return leads


async def _extrair_dados_do_painel(page) -> dict:
    """
    Extrai dados do painel lateral do Google Maps após clicar num resultado.
    """
    lead = {}

    try:
        # Nome
        nome_el = await page.query_selector('h1.DUwDvf')
        if nome_el:
            lead["nome"] = (await nome_el.inner_text()).strip()

        # Categoria / tipo de negócio
        cat_el = await page.query_selector('button.DkEaL')
        if cat_el:
            lead["categoria"] = (await cat_el.inner_text()).strip()

        # Endereço
        addr_el = await page.query_selector('button[data-item-id="address"]')
        if addr_el:
            lead["endereco"] = (await addr_el.inner_text()).strip()

        # Telefone
        tel_el = await page.query_selector('button[data-item-id^="phone"]')
        if tel_el:
            lead["telefone"] = (await tel_el.inner_text()).strip()

        # Website
        web_el = await page.query_selector('a[data-item-id="authority"]')
        if web_el:
            lead["website"] = await web_el.get_attribute("href")

        # Rating
        rating_el = await page.query_selector('div.F7nice span[aria-hidden="true"]')
        if rating_el:
            lead["rating"] = (await rating_el.inner_text()).strip()

        lead["fonte"] = "Google Maps"
        lead["status"] = "pendente"

    except Exception as e:
        console.print(f"[yellow]Erro ao extrair dados: {e}[/yellow]")

    return lead


def salvar_leads(leads: list[dict], arquivo: str = "data/leads_raw.json"):
    """
    Salva leads coletados no arquivo JSON, evitando duplicatas por nome.
    """
    path = Path(arquivo)
    path.parent.mkdir(exist_ok=True)

    existentes = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            existentes = json.load(f)

    nomes_existentes = {l.get("nome", "").lower() for l in existentes}
    novos = [l for l in leads if l.get("nome", "").lower() not in nomes_existentes]

    todos = existentes + novos

    with open(path, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

    return len(novos), len(todos)


async def executar_coleta(query: str = None, max_results: int = 10):
    """
    Ponto de entrada para coleta. Usa query fornecida ou escolhe aleatoriamente.
    """
    q = query or random.choice(QUERIES)

    console.print(f"\n[bold cyan]🔍 Buscando:[/bold cyan] {q}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Coletando dados do Google Maps...", total=None)
        leads = await scrape_google_maps(q, max_results)

    novos, total = salvar_leads(leads)

    console.print(f"[green]✓[/green] {len(leads)} resultados encontrados")
    console.print(f"[green]✓[/green] {novos} leads novos salvos (total acumulado: {total})")

    return leads


if __name__ == "__main__":
    asyncio.run(executar_coleta())
