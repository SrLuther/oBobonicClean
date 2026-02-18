"""
Sistema de cache para otimizar acesso a objetos Discord e dados.
"""
from typing import Optional, Dict, Any, TypeVar, Callable
from functools import wraps
import time

T = TypeVar('T')

class ChannelCache:
    """Cache para canais do Discord."""
    
    def __init__(self, ttl: float = 300.0):  # 5 minutos por padrão
        self._cache: Dict[int, tuple[Any, float]] = {}
        self.ttl = ttl
    
    def get(self, bot: Any, channel_id: int) -> Optional[Any]:
        """Obtém canal do cache ou busca e armazena."""
        now = time.time()
        
        # Verifica cache
        if channel_id in self._cache:
            obj, timestamp = self._cache[channel_id]
            if now - timestamp < self.ttl:
                return obj
            # Cache expirado
            del self._cache[channel_id]
        
        # Busca novo
        channel = bot.get_channel(channel_id)
        if channel:
            self._cache[channel_id] = (channel, now)
        
        return channel
    
    def invalidate(self, channel_id: int) -> None:
        """Remove item do cache."""
        self._cache.pop(channel_id, None)
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()


class RoleCache:
    """Cache para roles do Discord."""
    
    def __init__(self, ttl: float = 600.0):  # 10 minutos
        self._cache: Dict[int, Dict[int, tuple[Any, float]]] = {}
        self.ttl = ttl
    
    def get(self, guild: Any, role_id: int) -> Optional[Any]:
        """Obtém role do cache ou busca e armazena."""
        if not guild:
            return None
            
        guild_id = guild.id
        now = time.time()
        
        # Verifica cache da guild
        if guild_id not in self._cache:
            self._cache[guild_id] = {}
        
        guild_cache = self._cache[guild_id]
        
        # Verifica cache
        if role_id in guild_cache:
            obj, timestamp = guild_cache[role_id]
            if now - timestamp < self.ttl:
                return obj
            # Cache expirado
            del guild_cache[role_id]
        
        # Busca novo
        role = guild.get_role(role_id)
        if role:
            guild_cache[role_id] = (role, now)
        
        return role
    
    def invalidate_guild(self, guild_id: int) -> None:
        """Remove cache de uma guild."""
        self._cache.pop(guild_id, None)
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()


class DataCache:
    """Cache genérico para dados JSON e similares."""
    
    def __init__(self, ttl: float = 30.0):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self.ttl = ttl
    
    def get(self, key: str, loader: Callable[[], T]) -> T:
        """Obtém do cache ou carrega usando a função loader."""
        now = time.time()
        
        if key in self._cache:
            data, timestamp = self._cache[key]
            if now - timestamp < self.ttl:
                return data
            # Cache expirado
            del self._cache[key]
        
        # Carrega novo
        data = loader()
        self._cache[key] = (data, now)
        return data
    
    def invalidate(self, key: str) -> None:
        """Remove item do cache."""
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()


# Instâncias globais (podem ser compartilhadas entre cogs)
channel_cache = ChannelCache()
role_cache = RoleCache()
data_cache = DataCache()

