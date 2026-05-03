# cogs/events.py
# Sistema de broadcasts automáticos para servidores ARK

import discord
from discord.ext import commands, tasks
from datetime import datetime
from typing import Optional, Dict, Any
import logging
import random

import config
from utils.rcon_client import rcon_execute_with_retry

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────

TIMEOUT_RCON = 20
RCON_MAX_RETRIES = 2


class EventsCog(commands.Cog):
    """Sistema de broadcasts automáticos com dicas e informações."""
    
    # Mensagens de broadcast para todos os mapas
    BROADCAST_MESSAGES = [
        "Loja disponível! Aperte F2 para acessar e comprar itens exclusivos!",
        "Dica: Sempre desconecte sem itens importantes em seu personagem.",
        "Dica: Traga seus amigos e seja recompensado, confira o sistema de indicações no discord para mais detalhes!",
        "Dica: Construa uma base fechada, algumas estruturas ficam abertas e outros players podem acessar inventários. Garanta segurança.",
        "Entre no nosso Discord para dicas exclusivas, suporte e comunidade! Acesse pela loja (F2)",
        "Dica: Utilize o sistema de upload, /up /dow no chat do game",
        "Dica: Para esconder seu chat automaticamente pressione a tecla que fica ao lado do Z no teclado.",
        "Dica: Vincule seu game ao servidor discord para resgatar pontos diariamente e utilizar autokick",
        "Aviso: Os servidores reiniciam todos os dias de madrugada para manutenção. Prepare-se!",
        "Dica: Você pode se manter conectado farmando pontos! Não existe kick por tempo de inatividade.",
        "VIP: Membros VIP recebem múltiplos bônus! Compre VIP na loja e desbloqueie vantagens exclusivas.",
        "O nível máximo do personagem está configurado em 215. 115 comum + 100 de ascensão. Planeje seu progresso e evolução com cuidado!",
        "VIP ASSINATURA: Temos um sistema de assinatura VIP mensal onde você define o valor que quer contribuir, compre na loja e aproveite bônus exclusivos enquanto sua assinatura estiver ativa.",
    ]
    
    # Mapas para enviar broadcasts (apenas os habilitados no .env)
    ALL_MAPS = ["ragnarok omega", "rotativo", "genesis 2", "alps"]
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_message_index = -1  # Rastreia qual foi a última mensagem enviada
        try:
            self.broadcast_loop.start()  # type: ignore
            logger.info("[EVENTS] Sistema de broadcasts iniciado com sucesso")
        except Exception as e:
            logger.error(f"[EVENTS] Erro ao iniciar broadcast_loop: {e}")
    
    def cog_unload(self):
        """Cancela as tasks quando o cog é descarregado."""
        self.broadcast_loop.cancel()  # type: ignore
        logger.info("[EVENTS] Loop de broadcasts cancelado")
    
    # ─────────────────────────────────────────────────────────────
    # LOOP DE BROADCASTS AUTOMÁTICOS
    # ─────────────────────────────────────────────────────────────
    
    @tasks.loop(hours=1)
    async def broadcast_loop(self):
        """Envia mensagens aleatórias a cada 30 minutos em todos os mapas."""
        try:
            # Seleciona uma mensagem aleatória diferente da anterior
            available_indices = [i for i in range(len(self.BROADCAST_MESSAGES)) if i != self.last_message_index]
            message_index = random.choice(available_indices)
            self.last_message_index = message_index
            
            message = self.BROADCAST_MESSAGES[message_index]
            
            logger.info(f"[EVENTS] Enviando broadcast: {message}")
            
            # Envia em todos os mapas
            for map_name in self.ALL_MAPS:
                map_info = self._resolve_map(map_name)
                if not map_info:
                    logger.warning(f"[EVENTS] Mapa não encontrado: {map_name}")
                    continue
                
                host = map_info.get("host", config.ARK_DEFAULT_HOST)
                port = map_info.get("port")
                password = map_info.get("password", config.ARK_DEFAULT_PASSWORD)
                
                if not port:
                    logger.warning(f"[EVENTS] Porta RCON não configurada para {map_name}")
                    continue
                
                broadcast_cmd = f"broadcast {message}"
                
                result = await rcon_execute_with_retry(
                    host, port, password, broadcast_cmd,
                    max_retries=RCON_MAX_RETRIES, timeout=TIMEOUT_RCON
                )
                
                if result is None:
                    logger.warning(f"[EVENTS] Falha ao enviar broadcast em {map_name}")
                else:
                    logger.info(f"[EVENTS] Broadcast enviado com sucesso em {map_name}")
        
        except Exception as e:
            logger.error(f"[EVENTS] Erro no loop de broadcasts: {e}")
    
    @broadcast_loop.before_loop
    async def before_broadcast(self):
        """Aguarda o bot estar pronto antes de iniciar os broadcasts."""
        await self.bot.wait_until_ready()
        logger.info("[EVENTS] Bot pronto! Loop de broadcasts iniciado")
    
    # ─────────────────────────────────────────────────────────────
    # UTILITÁRIOS
    # ─────────────────────────────────────────────────────────────
    
    def _resolve_map(self, map_name: str) -> Optional[Dict[str, Any]]:
        """Resolve informações do mapa baseado no ARK_MAPS do config."""
        if not hasattr(config, 'ARK_MAPS') or not config.ARK_MAPS:
            return None
        
        map_key = map_name.lower()
        return config.ARK_MAPS.get(map_key)


async def setup(bot):
    """Carrega o cog."""
    await bot.add_cog(EventsCog(bot))
