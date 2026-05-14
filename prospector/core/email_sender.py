"""
email_sender.py — Geração de e-mail personalizado por IA e disparo via SMTP
"""

import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from dotenv import load_dotenv

load_dotenv()

console = Console()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "")
EMAIL_SENHA_APP = os.getenv("EMAIL_SENHA_APP", "")
EMAIL_NOME_REMETENTE = os.getenv("EMAIL_NOME_REMETENTE", "Luiz Neto")


def gerar_email_personalizado(lead: dict) -> dict:
    """
    Usa IA para gerar assunto e corpo de e-mail personalizado para o lead.
    """
    prompt = f"""
Você é um assistente de vendas de Luiz Neto, especialista em audiovisual para eventos 
com 27 anos de experiência. Luiz oferece:
- Projetos, consultoria e operação técnica em AV para eventos
- Desenvolvimento de software/apps customizados para eventos
- Streaming e conferências online
- Integração completa: áudio, vídeo, informática — tudo em uma única entrega

Escreva um e-mail de primeiro contato para este potencial cliente:

Nome da empresa: {lead.get('nome', 'N/A')}
Categoria: {lead.get('categoria', 'N/A')}
Localização: {lead.get('endereco', 'N/A')}
Site: {lead.get('website', 'N/A')}
Dor provável identificada: {lead.get('dor_provavel', 'N/A')}
Abordagem sugerida: {lead.get('abordagem_sugerida', 'N/A')}

REGRAS DO E-MAIL:
- Tom: profissional mas humano, não robótico, não bajulador
- Tamanho: curto (máximo 5 parágrafos)
- NÃO use frases genéricas como "espero que este e-mail te encontre bem"
- Mencione especificamente o tipo de negócio deles
- Deixe claro o diferencial de integração total de Luiz
- Inclua call-to-action para uma conversa rápida (15-20 min)
- Assine como: Luiz Neto | AV & Tech Solutions

Responda APENAS em JSON válido:
{{
  "assunto": "<assunto do e-mail>",
  "corpo_html": "<corpo em HTML simples, use <p>, <b>, <br> apenas>",
  "corpo_texto": "<versão em texto puro para fallback>"
}}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        texto = response.content[0].text.strip()
        if "```" in texto:
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]

        return json.loads(texto)

    except Exception as e:
        console.print(f"[red]Erro ao gerar e-mail: {e}[/red]")
        return {
            "assunto": f"Soluções em AV e Tecnologia para Eventos — {lead.get('nome', '')}",
            "corpo_texto": f"Olá,\n\nMeu nome é Luiz Neto, sou especialista em soluções técnicas para eventos...",
            "corpo_html": "<p>Olá,</p><p>Meu nome é Luiz Neto...</p>"
        }


def enviar_email(destinatario: str, assunto: str, corpo_html: str, corpo_texto: str) -> bool:
    """
    Envia e-mail via Gmail SMTP com App Password.
    """
    if not EMAIL_REMETENTE or not EMAIL_SENHA_APP:
        console.print("[red]Credenciais de e-mail não configuradas no .env[/red]")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{EMAIL_NOME_REMETENTE} <{EMAIL_REMETENTE}>"
    msg["To"] = destinatario
    msg["Subject"] = assunto

    msg.attach(MIMEText(corpo_texto, "plain", "utf-8"))
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
            server.send_message(msg)
        return True

    except Exception as e:
        console.print(f"[red]Erro ao enviar e-mail: {e}[/red]")
        return False


def processar_fila_envio(
    arquivo_aprovados: str = "data/leads_aprovados.json",
    dry_run: bool = False
):
    """
    Processa todos os leads aprovados com e-mail, gera mensagem personalizada e envia.
    dry_run=True apenas mostra o e-mail sem enviar.
    """
    path = Path(arquivo_aprovados)
    if not path.exists():
        console.print("[red]Arquivo de aprovados não encontrado.[/red]")
        return

    with open(path, "r", encoding="utf-8") as f:
        leads = json.load(f)

    fila = [
        l for l in leads
        if l.get("email") and l.get("status_envio") not in ("enviado", "erro")
    ]

    if not fila:
        console.print("[yellow]Nenhum lead com e-mail aguardando envio.[/yellow]")
        return

    console.print(f"\n[bold cyan]📧 {len(fila)} e-mails para enviar[/bold cyan]")

    enviados = 0
    erros = 0

    for lead in fila:
        console.print(f"\n[bold]→ {lead.get('nome')}[/bold] ({lead.get('email')})")

        # Gera e-mail personalizado
        console.print("  Gerando e-mail personalizado com IA...")
        email_data = gerar_email_personalizado(lead)

        # Preview
        console.print(Panel(
            f"[bold]Assunto:[/bold] {email_data['assunto']}\n\n"
            f"[dim]{email_data['corpo_texto'][:400]}...[/dim]",
            title="Preview do E-mail",
            border_style="cyan",
            padding=(1, 2)
        ))

        if dry_run:
            console.print("[yellow]  [DRY RUN] E-mail NÃO enviado.[/yellow]")
            continue

        confirmar = Confirm.ask("  Enviar este e-mail?", default=True)

        if confirmar:
            sucesso = enviar_email(
                destinatario=lead["email"],
                assunto=email_data["assunto"],
                corpo_html=email_data["corpo_html"],
                corpo_texto=email_data["corpo_texto"]
            )

            if sucesso:
                lead["status_envio"] = "enviado"
                lead["email_assunto"] = email_data["assunto"]
                enviados += 1
                console.print("[green]  ✓ E-mail enviado![/green]")
            else:
                lead["status_envio"] = "erro"
                erros += 1
        else:
            console.print("[dim]  Pulado.[/dim]")

    # Persiste status atualizado
    with open(path, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

    console.print(f"\n[bold]📊 Resultado:[/bold]")
    console.print(f"  [green]Enviados: {enviados}[/green]")
    console.print(f"  [red]Erros: {erros}[/red]")


def enviar_email_teste(destinatario: str = "luizzinho@gmail.com") -> bool:
    """
    Envia um e-mail de teste para validar configuração SMTP.
    """
    if not EMAIL_REMETENTE or not EMAIL_SENHA_APP:
        console.print("[red]Credenciais de e-mail não configuradas no .env[/red]")
        return False

    assunto = "Email de Teste — Prospector"
    corpo_texto = f"""Olá,

Este é um e-mail de teste do Prospector.

Se você recebeu esta mensagem, a configuração SMTP está funcionando corretamente.

Data/Hora: {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Remetente: {EMAIL_REMETENTE}

---
Prospector — Sistema de Prospecção
Luiz Neto | AV & Tech Solutions"""

    corpo_html = f"""<html>
  <body style="font-family: Arial, sans-serif;">
    <p>Olá,</p>
    <p>Este é um <strong>e-mail de teste</strong> do Prospector.</p>
    <p>Se você recebeu esta mensagem, a configuração SMTP está funcionando corretamente.</p>
    <p style="margin-top: 20px; color: #666; font-size: 12px;">
      Data/Hora: {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br>
      Remetente: {EMAIL_REMETENTE}
    </p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #999; font-size: 12px;">
      Prospector — Sistema de Prospecção<br>
      Luiz Neto | AV & Tech Solutions
    </p>
  </body>
</html>"""

    return enviar_email(destinatario, assunto, corpo_html, corpo_texto)


if __name__ == "__main__":
    processar_fila_envio(dry_run=True)
