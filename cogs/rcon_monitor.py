# cogs/rcon_monitor.py
# Sistema de monitoramento RCON automático + Painéis informativos
# Polling a cada 30s, alertas em Discord, auto-recovery

import discord
from discord.ext import commands, tasks
from discord.ext.tasks import Loop
import asyncio
import os
from datetime import datetime
from typing import Dict, Optional, List, Any
import logging

import config
from utils.rcon_client import rcon_execute_with_retry
from utils.ark_monitor_state import ArkMonitorState

logger = logging.getLogger(__name__)
logger.info("[Monitor] 🎯 Módulo rcon_monitor.py importado com sucesso")

# ─────────────────────────────────────────────────────────────
# MONITORES E DASHBOARDS
# ─────────────────────────────────────────────────────────────

class RconMonitor(commands.Cog):
    """Monitora servidores ARK em tempo real com painéis automáticos."""
    
    def __init__(self, bot: commands.Bot):
        print(f"[Monitor] 🔧 RconMonitor.__init__() chamado")
        self.bot = bot
        # Usa .bancos para consistência com outros cogs
        self.state = ArkMonitorState(data_dir=".bancos")
        
        # Mapa de servidores (carregado de config)
        self.servers: Dict[str, Dict] = {}
        self.load_server_config()
        
        # Controle do loop
        self.monitoring_active = False
        self.last_poll_time = None
        # Flag para sincronizar startup: after-loop aguarda que isso seja True
        self.startup_cleanup_completed = False
        
        # Type hint para discord.py task loop
        self.monitor_loop: Loop[Any]
        self.auto_recovery_loop: Loop[Any]
        print(f"[Monitor] ✅ RconMonitor.__init__() concluído")
    
    def load_server_config(self):
        """Carrega configuração dos servidores de config.ARK_MAPS."""
        self.servers = {}
        
        for map_key, map_info in config.ARK_MAPS.items():
            server_name = map_info.get("name", map_key)
            
            self.servers[server_name] = {
                "name": server_name,
                "host": map_info.get("host", config.ARK_DEFAULT_HOST),
                "port": map_info.get("port"),
                "password": map_info.get("password", config.ARK_DEFAULT_PASSWORD),
                "service": map_info.get("service", ""),
                "max_players": map_info.get("max_players", 50)  # Carrega max_players
            }
        
        logger.info(f"[Monitor] {len(self.servers)} servidor(es) carregado(s)")
        print(f"[Monitor] {len(self.servers)} servidor(es) carregado(s): {', '.join(self.servers.keys())}")
    
    async def cog_load(self) -> None:
        """Executado quando o cog é carregado."""
        print(f"[Monitor] ⚙️ cog_load() chamado")
        logger.info("[Monitor] 🎯 RconMonitor Cog carregado!")
        logger.info(f"[Monitor] 📡 Servidores configurados: {', '.join(self.servers.keys())}")
        logger.info("[Monitor] ⏳ Iniciando loop de monitoramento...")
        
        if config.RCON_MONITOR_ENABLED:
            print(f"[Monitor] 🔄 Iniciando monitor_loop...")
            self.monitor_loop.start()
            print(f"[Monitor] ✅ monitor_loop iniciado!")
            logger.info("[Monitor] ✅ Monitor loop iniciado!")
        else:
            print(f"[Monitor] ⚠️ Monitor desabilitado em config")
            logger.warning("[Monitor] ⚠️ Monitor desabilitado em config")
    
    async def cog_unload(self) -> None:
        """Executado quando o cog é descarregado."""
        print(f"[Monitor] ⚙️ cog_unload() chamado")
        logger.info("[Monitor] Parando loop de monitoramento...")
        if self.monitor_loop.is_running():
            self.monitor_loop.cancel()
        print(f"[Monitor] ✅ cog_unload() concluído")
    
    # ─────────────────────────────────────────────────────────────
    # MONITOR LOOP — Polling Automático
    # ─────────────────────────────────────────────────────────────
    
    @tasks.loop(seconds=config.RCON_MONITOR_INTERVAL_SECONDS)
    async def monitor_loop(self):
        """Loop principal: a cada 30s, poll todos os servidores."""
        if not config.RCON_MONITOR_ENABLED:
            return
        
        # ⏸️ IMPEDE race condition: não executa enquanto startup não termina
        if not self.startup_cleanup_completed:
            print(f"[Monitor] ⏸️  Monitor aguardando conclusão do startup...")
            return
        
        try:
            self.last_poll_time = datetime.now()
            print(f"[Monitor] 🔄 Iniciando poll de {len(self.servers)} servidor(es)...")
            logger.debug(f"[Monitor] Iniciando poll de {len(self.servers)} servidor(es)...")
            
            # Poll todos em paralelo
            tasks = [
                self._poll_single_server(server_name, server_info)
                for server_name, server_info in self.servers.items()
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Atualiza painéis
            print(f"[Monitor] 📊 Atualizando painéis...")
            await self._update_all_dashboards()
            print(f"[Monitor] ✅ Ciclo concluído")
            
        except Exception as e:
            print(f"[Monitor] ❌ Erro: {e}")
            logger.error(f"[Monitor] Erro no monitor loop: {e}")
    
    @monitor_loop.before_loop
    async def before_monitor_loop(self):
        """Aguarda bot estar pronto, limpa canal completamente e recria todos os painéis."""
        print(f"[Monitor] ⏳ before_monitor_loop: Aguardando bot ficar pronto...")
        await self.bot.wait_until_ready()
        print(f"[Monitor] ✅ before_monitor_loop: Bot pronto! Limpando canal de dashboards...")
        logger.info("[Monitor] Bot pronto! Limpando canal de dashboards...")
        
        # ANTES DE QUALQUER COISA: Limpa TODOS os IDs antigos do estado
        print(f"\n[Monitor] 🔍 ESTADO ANTERIOR (IDs que estavam salvos):")
        old_ids = self.state.state.get("dashboard_messages", {})
        if old_ids:
            for server, msg_id in old_ids.items():
                print(f"[Monitor]   • {server}: {msg_id}")
        else:
            print(f"[Monitor]   • (nenhum ID salvo anteriormente)")
        
        # LIMPA CANAL COMPLETAMENTE
        try:
            channel_id = config.RCON_DASHBOARDS_CHANNEL_ID
            print(f"\n[Monitor] 🔍 Procurando canal ID: {channel_id}")
            channel = self.bot.get_channel(channel_id)
            
            if not isinstance(channel, discord.TextChannel):
                print(f"[Monitor] ❌ Canal {channel_id} não encontrado ou inválido")
                logger.error(f"[Monitor] Canal {channel_id} não encontrado ou inválido")
                return
            
            print(f"[Monitor] 🧹 Deletando TODAS as mensagens do canal: {channel.name}")
            logger.info(f"[Monitor] 🧹 Deletando TODAS as mensagens do canal: {channel.name}")
            
            deleted_total = 0
            # Continua deletando até não haver mais mensagens (sem limite)
            while True:
                batch_deleted = 0
                async for msg in channel.history(limit=100):  # Pega 100 por vez
                    try:
                        await msg.delete()
                        batch_deleted += 1
                        deleted_total += 1
                        # ⏸️ IMPORTANTE: Aguarda para evitar rate limit do Discord
                        # Discord permite ~5 deletes por 5 segundos
                        await asyncio.sleep(0.2)  # 200ms entre cada delete
                    except discord.errors.NotFound:
                        # Mensagem já foi deletada
                        pass
                    except discord.errors.HTTPException as e:
                        if e.status == 429:  # Rate limited
                            print(f"[Monitor] ⏱️ Rate limited! Esperando 5 segundos...")
                            await asyncio.sleep(5)
                        else:
                            logger.warning(f"[Monitor] Erro ao deletar mensagem: {e}")
                    except Exception as e:
                        logger.warning(f"[Monitor] Erro ao deletar mensagem: {e}")
                
                # Se não deletou nada neste lote, não há mais mensagens
                if batch_deleted == 0:
                    break
                
                print(f"[Monitor]   → Lote: deletadas {batch_deleted} mensagens (total: {deleted_total})")
                await asyncio.sleep(1)  # 1 segundo entre lotes
            
            print(f"[Monitor] ✅ {deleted_total} mensagem(ns) deletada(s) NO TOTAL")
            if deleted_total > 0:
                logger.info(f"[Monitor] ✅ {deleted_total} mensagem(ns) deletada(s) NO TOTAL")
            else:
                print(f"[Monitor] ✅ Canal já estava vazio")
            
            # Aguarda um pouco para garantir que Discord processou as deleções
            await asyncio.sleep(2)
            
            # INICIALIZA ESTADO DE TODOS OS SERVIDORES
            print(f"\n[Monitor] 📊 Inicializando {len(self.servers)} servidor(es)...")
            logger.info(f"[Monitor] 📊 Inicializando {len(self.servers)} servidor(es)...")
            for server_name in self.servers.keys():
                self.state.update_server_status(server_name, is_online=False)
                self.state.set_dashboard_message_id(server_name, None)  # Limpa IDs antigos
                print(f"[Monitor]   → {server_name}: ID resetado para None")
            
            print(f"[Monitor] ✅ Estado limpo - nenhum ID de painel ativo")
            
            # Verifica que está limpo
            print(f"\n[Monitor] 🔍 ESTADO APÓS LIMPEZA (deve estar vazio):")
            new_ids = self.state.state.get("dashboard_messages", {})
            if new_ids:
                print(f"[Monitor] ⚠️  IDs AINDA PRESENTES (não deveria!)")
                for server, msg_id in new_ids.items():
                    print(f"[Monitor]   • {server}: {msg_id}")
            else:
                print(f"[Monitor]   • (vazio - correto!)")
            
            # FAZ POLL ÚNICO PARA PREENCHER ESTADOS
            print(f"\n[Monitor] 📡 Fazendo poll inicial para preencher informações...")
            logger.info("[Monitor] 📡 Fazendo poll inicial para preencher informações...")
            tasks = [
                self._poll_single_server(server_name, server_info)
                for server_name, server_info in self.servers.items()
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # RECRIA TODOS OS PAINÉIS
            print(f"\n[Monitor] 🎨 Recriando todos os painéis...")
            logger.info("[Monitor] 🎨 Recriando todos os painéis...")
            await self._update_all_dashboards()
            
            print(f"\n[Monitor] ✅ PAINÉIS RECRIADOS COM SUCESSO!")
            logger.info("[Monitor] ✅ PAINÉIS RECRIADOS COM SUCESSO!")
            
            # Verifica IDs criados
            print(f"\n[Monitor] 🔍 ESTADO FINAL (IDs dos novos painéis):")
            final_ids = self.state.state.get("dashboard_messages", {})
            if final_ids:
                for server, msg_id in final_ids.items():
                    print(f"[Monitor]   • {server}: {msg_id}")
            else:
                print(f"[Monitor]   • (vazio - pode haver erro na criação)")
            
            # ✅ MARCA QUE STARTUP TERMINOU - monitor_loop pode começar!
            self.startup_cleanup_completed = True
            print(f"\n[Monitor] 🚀 STARTUP CONCLUÍDO - monitor_loop liberado para iniciar!")
            logger.info("[Monitor] 🚀 STARTUP CONCLUÍDO - monitor_loop liberado para iniciar!")
            
        except Exception as e:
            print(f"[Monitor] ❌ Erro: {e}")
            logger.error(f"[Monitor] Erro ao limpar/recriar painéis: {e}", exc_info=True)
            # Mesmo com erro, marca como completo para evitar travamento
            self.startup_cleanup_completed = True
        
        print(f"[Monitor] ✅ Iniciando monitor_loop")
        logger.info("[Monitor] ✅ Iniciando monitor_loop")
    
    async def _poll_single_server(self, server_name: str, server_info: Dict):
        """Poll um servidor específico: executa listplayers, getgameinfo."""
        try:
            # Executa listplayers
            response = await rcon_execute_with_retry(
                host=server_info["host"],
                port=server_info["port"],
                password=server_info["password"],
                command="listplayers",
                max_retries=2,
                timeout=20.0
            )
            
            if response is None:
                # Timeout/falha
                self.state.update_server_status(server_name, is_online=False)
                logger.warning(f"[Monitor] {server_name}: OFFLINE (timeout)")
                return
            
            # Parse resposta
            player_list = self._parse_listplayers(response)
            player_count = len(player_list)
            
            # Atualiza estado
            self.state.update_server_status(
                server_name,
                is_online=True,
                player_count=player_count,
                online_players=player_list
            )
            
            logger.debug(f"[Monitor] {server_name}: ONLINE ({player_count} players)")
            
            # Se online, pode fazer health check adicional
            
        except Exception as e:
            logger.error(f"[Monitor] Erro ao fazer poll de {server_name}: {e}")
            self.state.update_server_status(server_name, is_online=False)
    
    def _parse_listplayers(self, response: str) -> List[str]:
        """
        Parse da resposta RCON 'listplayers'.
        
        Formato real:
         0. PROPL@YER013, 76561198133059796
         1. AnotherPlayer, 76561198987654321
        
        Extrai o NOME do jogador (parte antes da vírgula).
        """
        player_names = []
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:  # Ignora linhas vazias
                continue
            
            # Tenta encontrar padrão: "N. NAME, STEAMID" ou com "SteamID:" label
            try:
                # Se tem vírgula, tenta extrair Nome e validar SteamID
                if "," in line:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        # Nome é a primeira parte antes da vírgula
                        # Formato: "0. PROPL@YER013" -> remover "0. "
                        name_part = parts[0].strip()
                        
                        # Remove índice do começo (ex: "0. " ou "123. ")
                        if ". " in name_part:
                            name_part = name_part.split(". ", 1)[1].strip()
                        
                        # Última parte pode ser "SteamID: 76561..."  ou só "76561..."
                        steam_part = parts[-1].strip()
                        
                        # Remove "SteamID:" prefix se existir
                        if steam_part.startswith("SteamID:"):
                            steam_id = steam_part.replace("SteamID:", "").strip()
                        else:
                            steam_id = steam_part
                        
                        # Extrai apenas números (ignora possível ", Tribe: ..." no final)
                        steam_id = "".join(c for c in steam_id if c.isdigit())
                        
                        # Válido SteamID tem 17 dígitos, e nome não vazio
                        if len(steam_id) == 17 and name_part:
                            player_names.append(name_part)
                            logger.debug(f"[Monitor] Jogador encontrado: {name_part} ({steam_id})")
            except Exception as e:
                logger.debug(f"[Monitor] Erro ao parsear linha: {repr(line)} - {e}")
        
        return player_names
    
    # ─────────────────────────────────────────────────────────────
    # DASHBOARDS — Painéis Informativos
    # ─────────────────────────────────────────────────────────────
    
    async def _update_all_dashboards(self):
        """Atualiza um ÚNICO painel combinado com todos os servidores."""
        print(f"[Monitor] 🎯 Atualizando painel único combinado para {len(self.servers)} servidor(es)")
        channel = self.bot.get_channel(config.RCON_DASHBOARDS_CHANNEL_ID)
        
        if not channel or not isinstance(channel, discord.TextChannel):
            print(f"[Monitor] ❌ Canal {config.RCON_DASHBOARDS_CHANNEL_ID} não encontrado ou inválido!")
            logger.error(f"[Monitor] Canal {config.RCON_DASHBOARDS_CHANNEL_ID} não encontrado ou inválido!")
            return
        
        print(f"[Monitor] 📝 Atualizando painel em: {channel.name}")
        
        # Cria embed combinado com todos os servidores
        embed = self._create_combined_dashboard_embed()
        
        # Tenta editar mensagem existente
        message_id = self.state.get_dashboard_message_id("__COMBINED__")  # Chave especial
        
        try:
            if message_id:
                try:
                    # Tenta buscar e editar
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed)
                    print(f"[Monitor] ✅ Painel EDITADO (ID: {message_id})")
                    return
                except discord.NotFound:
                    print(f"[Monitor] - Mensagem antiga não encontrada, criando nova...")
            
            # Cria nova mensagem
            print(f"[Monitor] - Criando novo painel combinado...")
            message = await channel.send(embed=embed)
            print(f"[Monitor] ✅ Painel CRIADO (ID: {message.id})")
            
            # Salva ID para próximas edições
            self.state.set_dashboard_message_id("__COMBINED__", message.id)
            
        except Exception as e:
            print(f"[Monitor] ❌ Erro ao atualizar painel: {e}")
            logger.error(f"[Monitor] Erro ao atualizar painel combinado: {e}", exc_info=True)
    
    def _create_combined_dashboard_embed(self) -> discord.Embed:
        """Cria um único embed com TODOS os servidores em seções bem organizadas."""
        embed = discord.Embed(
            title="🎮 ARK SERVERS - STATUS GERAL",
            description="Monitoramento em tempo real de todos os servidores",
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )
        
        # Separa por tipo: Omega vs Cross
        omega_servers = []
        cross_servers = []
        
        for server_name in sorted(self.servers.keys()):
            # Classifica servidores
            if "Omega" in server_name:
                omega_servers.append(server_name)
            else:
                cross_servers.append(server_name)
        
        # ═══════════════════════════════════════════════════
        # OMEGA SERVERS
        # ═══════════════════════════════════════════════════
        
        if omega_servers:
            embed.add_field(
                name="🔴 ⚔️ OMEGA SERVERS",
                value="━━━━━━━━━━━━━━━━━━━━━━━━━",
                inline=False
            )
            
            for server_name in omega_servers:
                server_info = self.state.get_server_info(server_name)
                if not server_info:
                    continue
                
                status = server_info.get("status", "unknown")
                player_count = server_info.get("player_count", 0)
                online_players = server_info.get("online_players", [])
                
                status_emoji = "🟢" if status == "online" else "🔴"
                server_conf = self.servers.get(server_name, {})
                max_players = server_conf.get("max_players", 50)
                host = server_conf.get("host", "?")
                port = server_conf.get("port", "?")
                
                # Build player list
                player_info = ""
                if online_players and len(online_players) > 0:
                    player_info = "👨‍👩‍👧‍👦 **Conectados:**\n"
                    for idx, player in enumerate(online_players, 1):
                        player_info += f"  {idx}. {player}\n"
                else:
                    player_info = "👨‍👩‍👧‍👦 Vazio"
                
                # Tempo de atualização
                last_check = server_info.get("last_check", "?")
                if last_check and last_check != "?":
                    try:
                        check_time = datetime.fromisoformat(last_check)
                        ago = datetime.now() - check_time
                        segundos = int(ago.total_seconds())
                        time_str = f"{segundos}s" if segundos < 60 else f"{segundos // 60}m"
                    except:
                        time_str = "?"
                else:
                    time_str = "?"
                
                info = f"""```
{status_emoji} {status.upper()}
👥 {player_count}/{max_players} players
🌐 {host}:{port}
🔄 {time_str} atrás
```
{player_info}"""
                
                embed.add_field(
                    name=f"⚔️ {server_name}",
                    value=info,
                    inline=False
                )
        
        # ═══════════════════════════════════════════════════
        # CROSS SERVERS
        # ═══════════════════════════════════════════════════
        
        if cross_servers:
            embed.add_field(
                name="🟢 🛡️ CROSS SERVERS",
                value="━━━━━━━━━━━━━━━━━━━━━━━━━",
                inline=False
            )
            
            for server_name in cross_servers:
                server_info = self.state.get_server_info(server_name)
                if not server_info:
                    continue
                
                status = server_info.get("status", "unknown")
                player_count = server_info.get("player_count", 0)
                online_players = server_info.get("online_players", [])
                
                status_emoji = "🟢" if status == "online" else "🔴"
                server_conf = self.servers.get(server_name, {})
                max_players = server_conf.get("max_players", 50)
                host = server_conf.get("host", "?")
                port = server_conf.get("port", "?")
                
                # Build player list
                player_info = ""
                if online_players and len(online_players) > 0:
                    player_info = "👨‍👩‍👧‍👦 **Conectados:**\n"
                    for idx, player in enumerate(online_players, 1):
                        player_info += f"  {idx}. {player}\n"
                else:
                    player_info = "👨‍👩‍👧‍👦 Vazio"
                
                # Tempo de atualização
                last_check = server_info.get("last_check", "?")
                if last_check and last_check != "?":
                    try:
                        check_time = datetime.fromisoformat(last_check)
                        ago = datetime.now() - check_time
                        segundos = int(ago.total_seconds())
                        time_str = f"{segundos}s" if segundos < 60 else f"{segundos // 60}m"
                    except:
                        time_str = "?"
                else:
                    time_str = "?"
                
                info = f"""```
{status_emoji} {status.upper()}
👥 {player_count}/{max_players} players
🌐 {host}:{port}
🔄 {time_str} atrás
```
{player_info}"""
                
                embed.add_field(
                    name=f"🛡️ {server_name}",
                    value=info,
                    inline=False
                )
        
        embed.set_footer(text="Auto-atualiza a cada 30s • Monitoramento RCON")
        return embed
    
    def _create_dashboard_embed(self, server_name: str, server_info: Dict) -> tuple:
        """Cria embed informativo do servidor + View com botão de conexão."""
        status = server_info.get("status", "unknown")
        player_count = server_info.get("player_count", 0)
        online_players = server_info.get("online_players", [])
        
        # Cor por status
        if status == "online":
            color = discord.Color.green()
            status_emoji = "🟢"
        elif status == "offline":
            color = discord.Color.red()
            status_emoji = "🔴"
        else:
            color = discord.Color.greyple()
            status_emoji = "⚪"
        
        # Título
        title = f"{status_emoji} {server_name}"
        
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now()
        )
        
        # Campos
        embed.add_field(
            name="Status",
            value=status.upper(),
            inline=True
        )
        
        # Obtém servidor config e capacidade máxima
        server_conf = self.servers.get(server_name, {})
        max_players = server_conf.get("max_players", 50)
        
        embed.add_field(
            name="👥 Jogadores",
            value=f"{player_count}/{max_players} conectados",
            inline=True
        )
        
        # IP:Port
        host = server_conf.get("host", "?")
        port = server_conf.get("port", "?")
        
        embed.add_field(
            name="🌐 Servidor",
            value=f"{host}:{port}",
            inline=False
        )
        
        # Lista de jogadores
        if online_players and len(online_players) > 0:
            player_list = "\n".join(f"• {player}" for player in online_players)
            embed.add_field(
                name="👨‍👩‍👧‍👦 Conectados",
                value=player_list if len(player_list) < 1024 else f"{len(online_players)} jogadores conectados",
                inline=False
            )
        else:
            embed.add_field(
                name="👨‍👩‍👧‍👦 Conectados",
                value="Ninguém no servidor",
                inline=False
            )
        
        # Últimas mudanças
        last_check = server_info.get("last_check", "?")
        if last_check and last_check != "?":
            try:
                check_time = datetime.fromisoformat(last_check)
                ago = datetime.now() - check_time
                segundos = int(ago.total_seconds())
                if segundos < 60:
                    time_str = f"há {segundos}s"
                else:
                    mins = segundos // 60
                    time_str = f"há {mins}m"
            except:
                time_str = "?"
        else:
            time_str = "?"
        
        embed.add_field(
            name="🔄 Última atualização",
            value=time_str,
            inline=True
        )
        
        embed.set_footer(text="Monitoramento RCON • Auto-atualiza a cada 30s")
        
        # Sem botão de conexão - apenas visual
        view = None
        
        return embed, view
    
    # ─────────────────────────────────────────────────────────────
    # AUTO-RECOVERY — Reinicia servidor se cair
    # ─────────────────────────────────────────────────────────────
    
    @tasks.loop(minutes=1)
    async def auto_recovery_loop(self):
        """A cada 1min, verifica se precisa fazer auto-recovery."""
        if not config.RCON_AUTO_RECOVERY_ENABLED:
            return
        
        try:
            for server_name, server_info in self.servers.items():
                await self._check_and_recover(server_name, server_info)
        except Exception as e:
            logger.error(f"[Monitor] Erro no auto-recovery loop: {e}")
    
    @auto_recovery_loop.before_loop
    async def before_auto_recovery_loop(self):
        await self.bot.wait_until_ready()
    
    async def _check_and_recover(self, server_name: str, server_info: Dict):
        """Verifica se servidor precisa recovery e executa se necessário."""
        server_data = self.state.get_server_info(server_name)
        
        if not server_data:
            return
        
        # Se offline por muito tempo, tenta reiniciar
        if server_data.get("status") == "offline" and server_data.get("consecutive_timeouts", 0) >= 10:
            service_name = server_info.get("service", "")
            
            if not service_name:
                logger.warning(f"[Monitor] {server_name}: Sem service configurado, não posso fazer recovery")
                return
            
            logger.warning(f"[Monitor] Iniciando AUTO-RECOVERY para {server_name} (service: {service_name})")
            
            # Tenta reiniciar
            try:
                os.system(f"systemctl restart {service_name}")
                
                self.state.log_event(
                    server_name,
                    "auto_recovery",
                    f"Tentado restart de {service_name}"
                )
                
                # Aguarda 30s e refaz poll
                await asyncio.sleep(30)
                await self._poll_single_server(server_name, server_info)
                
            except Exception as e:
                logger.error(f"[Monitor] Erro no auto-recovery de {server_name}: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # COMANDOS ADMIN
    # ─────────────────────────────────────────────────────────────
    
    @commands.command(aliases=["monitorstatus", "monitoring"])
    @commands.has_permissions(administrator=True)
    async def monitor_status(self, ctx: commands.Context):
        """Mostra status do monitoramento e últimas mudanças."""
        summary = self.state.get_status_summary()
        
        embed = discord.Embed(
            title="📊 Status do Monitoramento RCON",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Servidores Online",
            value=f"{summary['online_servers']}/{summary['total_servers']}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Total de Jogadores",
            value=str(summary['total_players']),
            inline=True
        )
        
        embed.add_field(
            name="Última atualização",
            value=summary['last_updated'] or "Ainda não fez poll",
            inline=False
        )
        
        # Lista servidores
        server_list = ""
        for server_name, server_data in self.state.get_all_servers().items():
            status_emoji = "🟢" if server_data["status"] == "online" else "🔴"
            count = server_data.get("player_count", 0)
            server_list += f"{status_emoji} {server_name}: {count} players\n"
        
        embed.add_field(
            name="Detalhes",
            value=server_list or "_Nenhum servidor_",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=["monitorlog"])
    @commands.has_permissions(administrator=True)
    async def monitor_log(self, ctx: commands.Context, server_name: Optional[str] = None, count: int = 20):
        """Mostra últimos eventos do monitoramento."""
        events = self.state.get_recent_events(count=count, server_name=server_name)
        
        if not events:
            await ctx.send("❌ Nenhum evento encontrado")
            return
        
        embed = discord.Embed(
            title="📜 Log de Monitoramento",
            color=discord.Color.greyple(),
            timestamp=datetime.now()
        )
        
        log_text = ""
        for event in events:
            timestamp = event["timestamp"][-8:]  # HH:MM:SS
            server = event["server"]
            event_type = event["type"]
            details = event.get("details", "")
            
            log_text += f"`[{timestamp}] {server}` **{event_type}** — {details}\n"
        
        # Split em múltiplos fields se muito grande
        if len(log_text) > 1024:
            parts = [log_text[i:i+1020] for i in range(0, len(log_text), 1020)]
            for i, part in enumerate(parts):
                embed.add_field(
                    name=f"Eventos (parte {i+1})",
                    value=part,
                    inline=False
                )
        else:
            embed.add_field(name="Eventos", value=log_text, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_monitor(self, ctx: commands.Context):
        """Setup: cria painéis iniciais no canal configurado."""
        channel = self.bot.get_channel(config.RCON_DASHBOARDS_CHANNEL_ID)
        
        if not channel or not isinstance(channel, discord.TextChannel):
            await ctx.send(f"❌ Canal {config.RCON_DASHBOARDS_CHANNEL_ID} não existe ou é inválido!")
            return
        
        await ctx.send(f"🔄 Criando painéis no canal {channel.mention}...")
        
        # Inicializa estado de todos os servidores
        for server_name in self.servers.keys():
            self.state.update_server_status(server_name, is_online=False)
        
        # Faz poll uma vez
        tasks = [
            self._poll_single_server(server_name, server_info)
            for server_name, server_info in self.servers.items()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Atualiza painéis
        await self._update_all_dashboards()
        
        await ctx.send(f"✅ Painéis criados no canal {channel.mention}!")


async def setup(bot: commands.Bot):
    """Setup function para carregamento do cog."""
    print(f"[Monitor] 🚀 setup() chamado")
    try:
        logger.info("[Monitor] 📦 Iniciando setup do RconMonitor...")
        print(f"[Monitor] 📦 Iniciando setup do RconMonitor...")
        cog = RconMonitor(bot)
        await bot.add_cog(cog)
        logger.info("[Monitor] ✅ RconMonitor Cog adicionado ao bot!")
        print(f"[Monitor] ✅ RconMonitor Cog adicionado ao bot!")
    except Exception as e:
        logger.error(f"[Monitor] ❌ Erro ao adicionar cog: {e}", exc_info=True)
        raise
    logger.info("[Cog] RconMonitor carregado")
