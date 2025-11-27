# cogs/tickets/utils/transcript.py
import io
import discord
from typing import List

async def build_transcript(channel: discord.TextChannel, feedback: str = None, closed_by: str = None) -> discord.File:
    """
    Constrói a transcrição do canal e retorna discord.File (texto).
    Mantém anexo de URLs no texto.
    """
    header = (
        f"Transcript do Ticket: {channel.name}\n"
        f"Criado em: {channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Fechado por: {closed_by or 'N/A'}\n"
        f"Feedback: {feedback or 'N/A'}\n\n"
    )
    transcript = header
    messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
    for msg in messages:
        # created_at pode ser None em casos raros, usar str segura
        timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if msg.created_at else "N/A"
        content = msg.content or ""
        transcript += f"[{timestamp}] {msg.author.display_name}: {content}\n"
        for attachment in msg.attachments:
            transcript += f"  (Anexo: {attachment.url})\n"

    file = discord.File(io.StringIO(transcript), filename=f"transcript-{channel.name}.txt")
    return file
