# cogs/autoloop.py
import discord
from discord.ext import commands, tasks
import json
import random
import os
from typing import Any
import asyncio

# Configurações
LOOP_MESSAGES_FILE = "data/loop_messages.json"
TARGET_CHANNEL_ID = 1440828454164631736
TARGET_ROLE_ID = 1440828415103074356

class AutoLoopCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.current_messages = []
        self.used_messages = []
        self.last_sent_index = -1
        
        # Carrega as mensagens ao iniciar
        self.load_messages()
        
        # Inicia a task de envio automático
        if not self.auto_send_message.is_running():
            self.auto_send_message.start()
    
    def cog_unload(self):
        """Cancela a task quando o cog é descarregado"""
        if self.auto_send_message.is_running():
            self.auto_send_message.cancel()
    
    def load_messages(self):
        """Carrega as mensagens do arquivo JSON"""
        try:
            if os.path.exists(LOOP_MESSAGES_FILE):
                with open(LOOP_MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_messages = data.get("messages", [])
                    self.used_messages = data.get("used_messages", [])
            else:
                self.current_messages = []
                self.used_messages = []
                self.save_messages()
        except Exception as e:
            print(f"[AUTOLOOP] Erro ao carregar mensagens: {e}")
            self.current_messages = []
            self.used_messages = []
    
    def save_messages(self):
        """Salva as mensagens no arquivo JSON"""
        try:
            os.makedirs(os.path.dirname(LOOP_MESSAGES_FILE), exist_ok=True)
            with open(LOOP_MESSAGES_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "messages": self.current_messages,
                    "used_messages": self.used_messages
                }, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[AUTOLOOP] Erro ao salvar mensagens: {e}")
    
    def get_next_message(self) -> str | None:
        """
        Retorna a próxima mensagem a ser enviada.
        Se todas foram usadas, reseta e começa novamente.
        """
        if not self.current_messages:
            return None
        
        # Se todas as mensagens foram usadas, reseta
        if len(self.used_messages) >= len(self.current_messages):
            self.used_messages = []
        
        # Encontra uma mensagem que ainda não foi usada
        available_messages = [m for m in self.current_messages if m not in self.used_messages]
        
        if not available_messages:
            self.used_messages = []
            available_messages = self.current_messages
        
        # Seleciona aleatoriamente
        message = random.choice(available_messages)
        self.used_messages.append(message)
        self.save_messages()
        
        return message
    
    @tasks.loop(hours=6)
    async def auto_send_message(self):
        """Task que envia uma mensagem a cada 6 horas"""
        try:
            channel = self.bot.get_channel(TARGET_CHANNEL_ID)
            role = discord.utils.get(self.bot.guilds[0].roles, id=TARGET_ROLE_ID)
            
            if not channel:
                print(f"[AUTOLOOP] Canal {TARGET_CHANNEL_ID} não encontrado")
                return
            
            message_content = self.get_next_message()
            
            if not message_content:
                print("[AUTOLOOP] Nenhuma mensagem disponível para enviar")
                return
            
            # Monta o embed com cor chamativa
            embed = discord.Embed(
                title="📢 Aviso Importante",
                description=message_content,
                color=discord.Color.from_rgb(255, 69, 0)  # Vermelho-laranja chamativo (OrangeRed)
            )
            embed.set_footer(text="Sistema de Notificações Automáticas")
            embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user else None)
            
            # Monta a mensagem com menção ao cargo
            role_mention = role.mention if role else f"<@&{TARGET_ROLE_ID}>"
            
            await channel.send(role_mention, embed=embed)
            print(f"[AUTOLOOP] Mensagem enviada com sucesso no canal {TARGET_CHANNEL_ID}")
        
        except Exception as e:
            print(f"[AUTOLOOP] Erro ao enviar mensagem automática: {e}")
    
    @auto_send_message.before_loop
    async def before_auto_send(self):
        """Aguarda o bot estar pronto antes de iniciar a task"""
        await self.bot.wait_until_ready()
    
    @commands.command(name="cadloop")
    async def add_loop_message(self, ctx: commands.Context[Any]):
        """
        Adiciona uma mensagem para ser enviada automaticamente a cada 6 horas.
        Uso: !cadloop sua mensagem aqui
        
        Apenas administradores podem usar este comando.
        """
        # Verifica se o usuário é administrador
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Apenas administradores podem usar este comando!")
            return
        
        if not ctx.message.content.startswith("!cadloop "):
            await ctx.send("❌ Uso correto: `!cadloop sua mensagem aqui`")
            return
        
        # Extrai a mensagem (tudo após "!cadloop ")
        message_content = ctx.message.content[9:].strip()
        
        if not message_content:
            await ctx.send("❌ Você precisa fornecer uma mensagem!")
            return
        
        # Adiciona a mensagem
        self.current_messages.append(message_content)
        self.save_messages()
        
        # Responde com sucesso
        await ctx.send(f"✅ Mensagem adicionada com sucesso!\n\n**Mensagem:** {message_content}\n\n**Total de mensagens:** {len(self.current_messages)}")
        
        print(f"[AUTOLOOP] Nova mensagem adicionada por {ctx.author} ({ctx.author.id}): {message_content}")
    
    @commands.command(name="listarloop")
    async def list_loop_messages(self, ctx: commands.Context[Any]):
        """Lista todas as mensagens que serão enviadas automaticamente."""
        # Verifica permissão
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Apenas administradores podem usar este comando!")
            return
        
        if not self.current_messages:
            await ctx.send("📭 Nenhuma mensagem cadastrada no loop!")
            return
        
        # Cria embed com as mensagens
        embed = discord.Embed(
            title="📋 Mensagens do AutoLoop",
            description=f"Total: {len(self.current_messages)} mensagens",
            color=discord.Color.blue()
        )
        
        # Adiciona as mensagens em blocos (máximo 10 por linhas)
        for i, msg in enumerate(self.current_messages, 1):
            preview = msg[:100] + "..." if len(msg) > 100 else msg
            embed.add_field(
                name=f"#{i}",
                value=f"```{preview}```",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="removerloop")
    async def remove_loop_message(self, ctx: commands.Context[Any]):
        """Remove uma mensagem do loop por índice."""
        # Verifica permissão
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Apenas administradores podem usar este comando!")
            return
        
        if not ctx.message.content.startswith("!removerloop "):
            await ctx.send("❌ Uso correto: `!removerloop <número>`")
            return
        
        try:
            index = int(ctx.message.content[13:].strip()) - 1
            
            if index < 0 or index >= len(self.current_messages):
                await ctx.send(f"❌ Índice inválido! Use um número entre 1 e {len(self.current_messages)}")
                return
            
            removed_message = self.current_messages.pop(index)
            
            # Remove dos usados também
            if removed_message in self.used_messages:
                self.used_messages.remove(removed_message)
            
            self.save_messages()
            
            await ctx.send(f"✅ Mensagem #{index + 1} removida com sucesso!\n\n**Mensagem removida:** {removed_message}")
            print(f"[AUTOLOOP] Mensagem removida por {ctx.author} ({ctx.author.id})")
        
        except ValueError:
            await ctx.send("❌ Você deve fornecer um número válido!")
    
    @commands.command(name="limparloop")
    async def clear_loop_messages(self, ctx: commands.Context[Any]):
        """Remove TODAS as mensagens do loop (requer confirmação)."""
        # Verifica permissão
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Apenas administradores podem usar este comando!")
            return
        
        if not self.current_messages:
            await ctx.send("📭 Não há mensagens para limpar!")
            return
        
        # Pede confirmação
        embed = discord.Embed(
            title="⚠️ Confirmação Necessária",
            description=f"Você está prestes a apagar {len(self.current_messages)} mensagens do loop.\n\nReaja com ✅ para confirmar ou ❌ para cancelar.",
            color=discord.Color.red()
        )
        
        msg = await ctx.send(embed=embed)
        
        # Adiciona reações
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                self.current_messages = []
                self.used_messages = []
                self.save_messages()
                await ctx.send("✅ Todas as mensagens foram removidas do loop!")
                print(f"[AUTOLOOP] Loop limpo por {ctx.author} ({ctx.author.id})")
            else:
                await ctx.send("❌ Operação cancelada!")
        
        except asyncio.TimeoutError:
            await ctx.send("⏰ Tempo esgotado! Operação cancelada.")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoLoopCog(bot))
