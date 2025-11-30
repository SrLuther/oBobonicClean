import os
import datetime
import config
import discord

TICKET_IDS_FILE = "tickets_ids.txt"

def ler_ticket_ids():
    if not os.path.exists(TICKET_IDS_FILE):
        with open(TICKET_IDS_FILE, "w") as f:
            f.write("0")
        return 0
    with open(TICKET_IDS_FILE, "r") as f:
        return int(f.read().strip())

def gerar_ticket_id():
    ticket_id = ler_ticket_ids() + 1
    with open(TICKET_IDS_FILE, "w") as f:
        f.write(str(ticket_id))
    return ticket_id

async def salvar_transcript(
    canal: discord.TextChannel,
    usuario: discord.Member,
    ticket_id: int | str,
    feedback: str,
) -> None:
    agora = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    nome_arquivo = f"ticket_{ticket_id}_{usuario.name}_{agora}.txt"
    caminho = os.path.join("tickets_transcripts", nome_arquivo)

    if not os.path.exists("tickets_transcripts"):
        os.makedirs("tickets_transcripts")

    async for msg in canal.history(limit=None):
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(f"[{msg.created_at}] {msg.author}: {msg.content}\n")

    with open(caminho, "a", encoding="utf-8") as f:
        f.write(f"\nFEEDBACK: {feedback}\n")

    # envia para canal de arquivos
    canal_arquivo = canal.guild.get_channel(config.CANAL_ARQUIVO_ID)
    if isinstance(canal_arquivo, discord.TextChannel):
        await canal_arquivo.send(file=discord.File(caminho))
