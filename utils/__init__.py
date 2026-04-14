# Utilitários compartilhados do bot

from .server_monitor import PlayerMonitor, get_monitor, parse_rcon_listplayers
from .ark_monitor_state import ArkMonitorState

_ark_monitor_state_instance: "ArkMonitorState | None" = None

def get_ark_state() -> "ArkMonitorState":
    """Retorna a instância singleton do ArkMonitorState (data_dir='.bancos')."""
    global _ark_monitor_state_instance
    if _ark_monitor_state_instance is None:
        _ark_monitor_state_instance = ArkMonitorState(data_dir=".bancos")
    return _ark_monitor_state_instance

__all__ = ["PlayerMonitor", "get_monitor", "parse_rcon_listplayers", "ArkMonitorState", "get_ark_state"]

