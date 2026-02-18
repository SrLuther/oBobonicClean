"""
Utilitários otimizados para operações JSON com cache e batch operations.
"""
import json
import os
import asyncio
from typing import Dict, Any, Optional, Callable
from functools import wraps
import aiofiles

# Cache simples em memória para evitar múltiplas leituras
_json_cache: Dict[str, tuple[Any, float]] = {}
_cache_ttl = 5.0  # 5 segundos


async def load_json_async(file_path: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Carrega JSON de forma assíncrona com cache em memória.
    Usa aiofiles para não bloquear o event loop.
    """
    import time
    now = time.time()
    
    # Verifica cache
    if file_path in _json_cache:
        data, timestamp = _json_cache[file_path]
        if now - timestamp < _cache_ttl:
            return data
        del _json_cache[file_path]
    
    # Se não existe, retorna default
    if not os.path.exists(file_path):
        if default is None:
            default = {}
        _json_cache[file_path] = (default, now)
        return default
    
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            data = json.loads(content)
            _json_cache[file_path] = (data, now)
            return data
    except (json.JSONDecodeError, IOError):
        if default is None:
            default = {}
        _json_cache[file_path] = (default, now)
        return default


def load_json_sync(file_path: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Versão síncrona otimizada para uso em thread executor.
    """
    import time
    now = time.time()
    
    # Verifica cache
    if file_path in _json_cache:
        data, timestamp = _json_cache[file_path]
        if now - timestamp < _cache_ttl:
            return data
        del _json_cache[file_path]
    
    if not os.path.exists(file_path):
        if default is None:
            default = {}
        _json_cache[file_path] = (default, now)
        return default
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _json_cache[file_path] = (data, now)
            return data
    except (json.JSONDecodeError, IOError):
        if default is None:
            default = {}
        _json_cache[file_path] = (default, now)
        return default


async def save_json_async(file_path: str, data: Dict[str, Any], ensure_dir: bool = True) -> bool:
    """
    Salva JSON de forma assíncrona.
    """
    import time
    try:
        if ensure_dir:
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        
        # Atualiza cache
        now = time.time()
        _json_cache[file_path] = (data, now)
        return True
    except (IOError, OSError, TypeError) as e:
        print(f"❌ ERRO ao salvar JSON em {file_path}: {e}")
        return False


def save_json_sync(file_path: str, data: Dict[str, Any], ensure_dir: bool = True) -> bool:
    """
    Versão síncrona para uso em thread executor.
    """
    import time
    try:
        if ensure_dir:
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Atualiza cache
        now = time.time()
        _json_cache[file_path] = (data, now)
        return True
    except (IOError, OSError, TypeError) as e:
        print(f"❌ ERRO ao salvar JSON em {file_path}: {e}")
        return False


def invalidate_cache(file_path: str) -> None:
    """Invalida o cache de um arquivo."""
    _json_cache.pop(file_path, None)


def clear_all_cache() -> None:
    """Limpa todo o cache."""
    _json_cache.clear()

