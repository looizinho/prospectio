"""
Bot Telegram para integração com sistema Prospectio.
Permite disparar operações remotamente via Telegram.
"""

import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from rich.console import Console

console = Console()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def handle_teste_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para o comando /teste_email."""
    chat_id = update.effective_chat.id
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not telegram_chat_id:
        console.print("[red]❌ Erro: TELEGRAM_CHAT_ID não configurado em .env[/red]")
        await update.message.reply_text("❌ Bot não configurado corretamente.")
        return

    # Validar chat ID
    try:
        configured_chat_id = int(telegram_chat_id)
    except ValueError:
        console.print("[red]❌ Erro: TELEGRAM_CHAT_ID deve ser um número[/red]")
        await update.message.reply_text("❌ Bot não configurado corretamente.")
        return

    if chat_id != configured_chat_id:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.warning(f"[{timestamp}] Acesso negado - Chat ID inválido: {chat_id}")
        await update.message.reply_text("❌ Acesso negado.")
        return

    # Enviar email de teste
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        from core.email_sender import enviar_email_teste

        sucesso = enviar_email_teste()

        if sucesso:
            logger.info(f"[{timestamp}] ✓ E-mail de teste enviado com sucesso")
            await update.message.reply_text("📧 E-mail de teste enviado para luizzinho@gmail.com!")
        else:
            logger.error(f"[{timestamp}] ✗ Falha ao enviar e-mail de teste")
            await update.message.reply_text("❌ Erro ao enviar. Verifique credenciais no .env")
    except Exception as e:
        logger.error(f"[{timestamp}] ✗ Exceção ao enviar e-mail: {str(e)}")
        await update.message.reply_text("❌ Erro ao enviar. Verifique credenciais no .env")


async def start_bot_async() -> None:
    """Inicia o bot Telegram com polling."""
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        console.print("[red]❌ Erro: TELEGRAM_BOT_TOKEN não configurado em .env[/red]")
        return

    if not chat_id:
        console.print("[red]❌ Erro: TELEGRAM_CHAT_ID não configurado em .env[/red]")
        return

    # Criar aplicação
    application = Application.builder().token(token).build()

    # Registrar handler
    application.add_handler(CommandHandler("teste_email", handle_teste_email))

    console.print("[bold cyan]🤖 Bot Telegram iniciado[/bold cyan]")
    console.print(f"[dim]Chat ID autorizado: {chat_id}[/dim]")
    console.print("[dim]Pressione Ctrl+C para parar[/dim]\n")

    # Inicializar, iniciar e começar polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    try:
        # Manter o bot rodando indefinidamente
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        console.print("\n[yellow]⏸️  Bot Telegram parado[/yellow]")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
