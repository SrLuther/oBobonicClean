# bot.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import time 
import threading 
from flask import Flask 
import sys
from io import StringIO
import datetime # ✅ NOVO IMPORT: Para formatar data e hora

# --------------------
## 🛑 IMPLEMENTAÇÃO DO KEEP-ALIVE
# --------------------
# ... (NÃO HÁ ALTERAÇÕES NESTA SEÇÃO)

# --------------------
## 🛑 CÓDIGO DO BOT
# --------------------

# --- NOVO: CLASSE PARA CAPTURAR O LOG ---
class LogBuffer:
    # ... (NÃO HÁ ALTERAÇÕES NESTA CLASSE)
    # ...

log_catcher = LogBuffer()

# ... (código existente de carregamento de variáveis) ...

# 5. Evento on_ready 
@bot.event
async def on_ready():
    # 1. Parar a captura de logs
    log_catcher.stop_capture()
    deploy_log_content = log_catcher.get_log()
    
    print(f"\n🚀 Bot Logado como {bot.user} (ID: {bot.user.id})")
    
    # Executa o carregamento dos cogs, cujo log também está no buffer
    await load_cogs(bot) 

    # 2. Sincronização de comandos
    # ... (NÃO HÁ ALTERAÇÕES NESTA SEÇÃO) ...
        
    # 3. Envio do Log do Deploy para o Discord como arquivo
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    if canal_logs:
        try:
            # ➡️ GERAÇÃO DA MENSAGEM E ARQUIVO
            
            # Formata a data e hora atual no fuso local do servidor/Railway (UTC)
            agora = datetime.datetime.now()
            data_formatada = agora.strftime("%d/%m/%Y %H:%M:%S")

            # Cria o arquivo de log a partir do buffer
            log_file = discord.File(
                fp=StringIO(deploy_log_content), 
                filename=f"log_oBobonic.txt" # ✅ Nome do arquivo solicitado
            )
            
            # ✅ Mensagem Formatada
            mensagem_deploy = (
                f"🤖 **oBobonic** iniciado ou reiniciado em `{data_formatada}`. "
                f"Verifique o log completo no arquivo anexo abaixo:"
            )
            
            # Envia a mensagem e o arquivo
            await canal_logs.send(
                mensagem_deploy,
                file=log_file
            )

            # Envia a mensagem final do Bobonicado no canal
            await canal_logs.send(
                "🎩✨ **Bobonicado conferiu o inventário arcano...**\n"
                "Se até o impossível carregou, então foi coisa dele mesmo. 😎\n"
                "🚀 **Todos os cogs foram carregados com sucesso!**"
            )

        except Exception as e:
            print(f"❌ ERRO ao enviar arquivo de log para o Discord: {e}")
            
    print("✅ Bot pronto e rodando!")

# 6. Execução do Bot 
# ... (NÃO HÁ ALTERAÇÕES NESTA SEÇÃO) ...