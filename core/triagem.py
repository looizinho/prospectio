"""
triagem.py — Usa IA (Claude) para avaliar e qualificar leads coletados
"""

import json
import os
from pathlib import Path
from anthropic import Anthropic
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()

console = Console()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


PERFIL_LUIZ = """
Você está ajudando Luiz Neto, profissional com 27 anos de experiência em:
- Serviços técnicos em audiovisual para eventos (projetos, consultoria, operação)
- Desenvolvimento de soluções em software customizado para eventos
- Streaming e conferências online
- Integração entre áudio, vídeo e informática em eventos

SEU DIFERENCIAL: Capacidade de integrar TODOS os setores técnicos de um evento 
numa única entrega, incluindo apps dedicados ao evento.

CLIENTES IDEAIS:
- Empresas organizadoras de eventos (qualquer porte)
- Produtoras de eventos corporativos
- Locadoras de equipamentos que precisam terceirizar serviços fora do escopo delas
- Empresas que organizam eventos mas não têm equipe técnica AV própria
- Empresas que fazem eventos híbridos (presencial + online)

CLIENTES NÃO IDEAIS:
- Festas pessoais, casamentos, eventos sociais sem viés corporativo
- Empresas que já têm equipe técnica AV interna completa
"""


def avaliar_lead(lead: dict) -> dict:
    """
    Usa IA para avaliar a relevância de um lead e gerar contexto de abordagem.
    Retorna o lead enriquecido com score, justificativa e sugestão de abordagem.
    """
    prompt = f"""
{PERFIL_LUIZ}

Analise este lead e responda APENAS em JSON válido, sem texto fora do JSON:

LEAD:
- Nome: {lead.get('nome', 'N/A')}
- Categoria: {lead.get('categoria', 'N/A')}
- Endereço: {lead.get('endereco', 'N/A')}
- Website: {lead.get('website', 'N/A')}
- Rating: {lead.get('rating', 'N/A')}

Retorne exatamente este JSON:
{{
  "score": <número de 1 a 10 indicando relevância como cliente potencial>,
  "classificacao": "<QUENTE | MORNO | FRIO>",
  "justificativa": "<por que esse lead é ou não é relevante, em 1-2 frases>",
  "dor_provavel": "<qual problema esse cliente provavelmente tem que Luiz resolve>",
  "abordagem_sugerida": "<como Luiz deveria se apresentar para esse cliente específico, em 1-2 frases>",
  "recomendacao": "<APROVAR | DESCARTAR>"
}}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        texto = response.content[0].text.strip()

        # Limpa possível markdown
        if "```" in texto:
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]

        avaliacao = json.loads(texto)
        lead_enriquecido = {**lead, **avaliacao}
        return lead_enriquecido

    except Exception as e:
        console.print(f"[yellow]Erro ao avaliar lead '{lead.get('nome')}': {e}[/yellow]")
        lead["score"] = 5
        lead["classificacao"] = "MORNO"
        lead["justificativa"] = "Avaliação automática falhou — revisar manualmente"
        lead["dor_provavel"] = "Desconhecida"
        lead["abordagem_sugerida"] = "Apresentação geral dos serviços"
        lead["recomendacao"] = "APROVAR"
        return lead


def triar_leads_pendentes(
    arquivo_raw: str = "data/leads_raw.json",
    arquivo_triados: str = "data/leads_triados.json"
):
    """
    Lê leads com status 'pendente', avalia todos com IA e salva triados.
    """
    path_raw = Path(arquivo_raw)
    if not path_raw.exists():
        console.print("[red]Arquivo de leads não encontrado. Execute o scraper primeiro.[/red]")
        return []

    with open(path_raw, "r", encoding="utf-8") as f:
        todos = json.load(f)

    pendentes = [l for l in todos if l.get("status") == "pendente"]

    if not pendentes:
        console.print("[yellow]Nenhum lead pendente para triar.[/yellow]")
        return []

    console.print(f"\n[bold cyan]🤖 Triando {len(pendentes)} leads com IA...[/bold cyan]")

    triados = []
    for i, lead in enumerate(pendentes, 1):
        console.print(f"  [{i}/{len(pendentes)}] Avaliando: {lead.get('nome', 'N/A')}...")
        avaliado = avaliar_lead(lead)
        triados.append(avaliado)

        # Atualiza status no arquivo raw
        for l in todos:
            if l.get("nome") == lead.get("nome"):
                l["status"] = "triado"

    # Salva leads triados
    path_triados = Path(arquivo_triados)
    path_triados.parent.mkdir(exist_ok=True)

    existentes_triados = []
    if path_triados.exists():
        with open(path_triados, "r", encoding="utf-8") as f:
            existentes_triados = json.load(f)

    nomes_existentes = {l.get("nome", "").lower() for l in existentes_triados}
    novos_triados = [l for l in triados if l.get("nome", "").lower() not in nomes_existentes]

    todos_triados = existentes_triados + novos_triados

    # Ordena por score decrescente
    todos_triados.sort(key=lambda x: x.get("score", 0), reverse=True)

    with open(path_triados, "w", encoding="utf-8") as f:
        json.dump(todos_triados, f, ensure_ascii=False, indent=2)

    # Atualiza arquivo raw
    with open(path_raw, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

    quentes = len([l for l in triados if l.get("classificacao") == "QUENTE"])
    mornos = len([l for l in triados if l.get("classificacao") == "MORNO"])
    frios = len([l for l in triados if l.get("classificacao") == "FRIO"])

    console.print(f"\n[green]✓ Triagem concluída:[/green]")
    console.print(f"  🔥 Quentes: {quentes}")
    console.print(f"  🌡  Mornos:  {mornos}")
    console.print(f"  ❄️  Frios:   {frios}")

    return todos_triados


if __name__ == "__main__":
    triar_leads_pendentes()
