# utils/ark_monitor_state.py
# Gerenciador de estado de monitoramento ARK
# Rastreia: servidores online/offline, jogadores, dashboards message IDs, histórico

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)

class ArkMonitorState:
    """
    Gerencia estado persistente do sistema de monitoramento.
    
    Dados armazenados em JSON:
    - servers: {server_name: {status, player_count, last_check, online_players, message_id}}
    - events: histórico de eventos (player_joined, server_down, etc.)
    - dashboard_messages: IDs das mensagens dos 5 painéis
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        
        # Cria diretório se não existir
        try:
            os.makedirs(data_dir, exist_ok=True)
            logger.debug(f"[Monitor] Diretório de dados: {os.path.abspath(data_dir)}")
        except Exception as e:
            logger.error(f"[Monitor] Erro ao criar data_dir: {e}")
            raise
        
        self.state_file = os.path.join(data_dir, "rcon_monitor_state.json")
        self.log_file = os.path.join(data_dir, "rcon_monitor.log")
        
        logger.debug(f"[Monitor] State file: {os.path.abspath(self.state_file)}")
        logger.debug(f"[Monitor] Log file: {os.path.abspath(self.log_file)}")
        
        self.state: Dict = {
            "servers": {},
            "events": [],
            "dashboard_messages": {},
            "last_updated": None,
            "monitoring_started": datetime.now().isoformat()
        }
        
        self._load_state()
    
    def _load_state(self):
        """Carrega estado persistido."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.state.update(loaded)
                    logger.debug(f"[Monitor] Estado carregado de {self.state_file}")
        except Exception as e:
            logger.error(f"[Monitor] Erro ao carregar estado: {e}")
            self.state = {
                "servers": {},
                "events": [],
                "dashboard_messages": {},
                "last_updated": None,
                "monitoring_started": datetime.now().isoformat()
            }
    
    def _save_state(self):
        """Salva estado em JSON."""
        try:
            logger.debug(f"[Monitor] Salvando estado em {os.path.abspath(self.state_file)}")
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            logger.debug(f"[Monitor] Estado salvo com sucesso")
        except Exception as e:
            logger.error(f"[Monitor] Erro ao salvar estado em {self.state_file}: {e}", exc_info=True)
    
    def log_event(self, server_name: str, event_type: str, details: str = "", level: str = "INFO"):
        """
        Loga um evento.
        
        Args:
            server_name: Nome do servidor
            event_type: Tipo (player_joined, player_left, server_online, server_offline, etc.)
            details: Detalhes adicionais
            level: INFO, WARNING, ERROR
        """
        timestamp = datetime.now().isoformat()
        
        event = {
            "timestamp": timestamp,
            "server": server_name,
            "type": event_type,
            "details": details,
            "level": level
        }
        
        # Mantém apenas últimos 500 eventos em memória
        self.state["events"].append(event)
        if len(self.state["events"]) > 500:
            self.state["events"] = self.state["events"][-500:]
        
        # Log também em arquivo
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [{level}] {server_name} - {event_type}: {details}\n")
        except Exception as e:
            logger.error(f"[Monitor] Erro ao escrever log file: {e}")
        
        self._save_state()
    
    def update_server_status(
        self,
        server_name: str,
        is_online: bool,
        player_count: int = 0,
        online_players: Optional[List[str]] = None
    ):
        """
        Atualiza status de um servidor.
        
        Args:
            server_name: Nome do servidor
            is_online: True se online, False se offline
            player_count: Número de jogadores online
            online_players: Lista de Steam IDs dos players
        """
        if server_name not in self.state["servers"]:
            self.state["servers"][server_name] = {
                "status": "unknown",
                "player_count": 0,
                "online_players": [],
                "last_check": None,
                "last_online": None,
                "last_offline": None,
                "consecutive_timeouts": 0,
                "message_id": None
            }
        
        server_data = self.state["servers"][server_name]
        old_status = server_data.get("status")
        old_player_count = server_data.get("player_count", 0)
        old_players = set(server_data.get("online_players", []))
        
        now = datetime.now().isoformat()
        
        if is_online:
            server_data["status"] = "online"
            server_data["player_count"] = player_count
            server_data["online_players"] = online_players or []
            server_data["last_check"] = now
            server_data["last_online"] = now
            server_data["consecutive_timeouts"] = 0
            
            # Detecta mudanças de status
            if old_status != "online":
                self.log_event(server_name, "server_online", f"Servidor voltou online ({player_count} players)")
            
            # Detecta players que entraram
            new_players = set(online_players or []) - old_players
            for player_id in new_players:
                self.log_event(server_name, "player_joined", f"Player joined: {player_id}")
            
            # Detecta players que saíram
            left_players = old_players - set(online_players or [])
            for player_id in left_players:
                self.log_event(server_name, "player_left", f"Player left: {player_id}")
        
        else:
            server_data["status"] = "offline"
            server_data["player_count"] = 0
            server_data["online_players"] = []
            server_data["last_check"] = now
            server_data["last_offline"] = now
            server_data["consecutive_timeouts"] += 1
            
            # Detecta mudanças de status
            if old_status != "offline":
                self.log_event(
                    server_name,
                    "server_offline",
                    f"Servidor offline (era {old_player_count} players)"
                )
        
        self.state["last_updated"] = now
        self._save_state()
    
    def get_server_info(self, server_name: str) -> Optional[Dict]:
        """Retorna info atual do servidor."""
        return self.state["servers"].get(server_name)
    
    def get_all_servers(self) -> Dict:
        """Retorna info de todos os servidores."""
        return self.state["servers"]
    
    def set_dashboard_message_id(self, server_name: str, message_id: Optional[int]):
        """Salva ID da mensagem do painel para um servidor."""
        if message_id is None:
            self.state["dashboard_messages"].pop(server_name, None)
        else:
            self.state["dashboard_messages"][server_name] = message_id
        self._save_state()
    
    def get_dashboard_message_id(self, server_name: str) -> Optional[int]:
        """Retorna ID da mensagem do painel para um servidor."""
        msg_id = self.state["dashboard_messages"].get(server_name)
        return msg_id if isinstance(msg_id, int) else None
    
    def get_recent_events(self, count: int = 20, server_name: Optional[str] = None) -> List[Dict]:
        """
        Retorna eventos recentes.
        
        Args:
            count: Número de eventos a retornar
            server_name: Se especificado, filtra por servidor
        """
        events = self.state.get("events", [])
        
        if server_name:
            events = [e for e in events if e["server"] == server_name]
        
        return events[-count:] if count else events
    
    def get_crash_detection_status(self, server_name: str, timeout_seconds: int = 300) -> bool:
        """
        Verifica se servidor está em "crash suspected" mode.
        
        Critério: última resposta RCON foi há mais de timeout_seconds.
        """
        server_data = self.get_server_info(server_name)
        if not server_data:
            return False
        
        if server_data["status"] == "offline":
            return True  # Já marcado offline
        
        last_check_str = server_data.get("last_check")
        if not last_check_str:
            return False
        
        try:
            last_check = datetime.fromisoformat(last_check_str)
            time_since = datetime.now() - last_check
            
            if time_since > timedelta(seconds=timeout_seconds):
                return True  # Sem resposta por muito tempo
        except:
            pass
        
        return False
    
    def get_uptime_percentage(self, server_name: str, hours: int = 24) -> float:
        """
        Calcula uptime % nos últimas X horas.
        (Baseado no histórico de eventos)
        """
        events = self.get_recent_events(server_name=server_name)
        
        if not events:
            return 100.0
        
        # Conta mudanças de status
        up_time = timedelta(0)
        down_time = timedelta(0)
        
        current_status = "unknown"
        last_change_time = datetime.now()
        
        for event in reversed(events):
            try:
                event_time = datetime.fromisoformat(event["timestamp"])
                
                if event["type"] == "server_online":
                    time_delta = last_change_time - event_time
                    if current_status == "offline":
                        down_time += time_delta
                    current_status = "online"
                    last_change_time = event_time
                
                elif event["type"] == "server_offline":
                    time_delta = last_change_time - event_time
                    if current_status == "online":
                        up_time += time_delta
                    current_status = "offline"
                    last_change_time = event_time
            except:
                pass
        
        total = up_time + down_time
        if total.total_seconds() == 0:
            return 100.0
        
        return (up_time.total_seconds() / total.total_seconds()) * 100
    
    def clear_old_events(self, days: int = 7):
        """Remove eventos com mais de X dias."""
        cutoff = datetime.now() - timedelta(days=days)
        
        before = len(self.state["events"])
        self.state["events"] = [
            e for e in self.state["events"]
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]
        after = len(self.state["events"])
        
        logger.debug(f"[Monitor] Limpeza de eventos: removidos {before - after}")
        self._save_state()
    
    def get_status_summary(self) -> Dict:
        """Retorna resumo geral do status."""
        servers = self.state["servers"]
        
        total_servers = len(servers)
        online_count = sum(1 for s in servers.values() if s.get("status") == "online")
        total_players = sum(s.get("player_count", 0) for s in servers.values())
        
        return {
            "total_servers": total_servers,
            "online_servers": online_count,
            "offline_servers": total_servers - online_count,
            "total_players": total_players,
            "last_updated": self.state.get("last_updated"),
            "monitoring_started": self.state.get("monitoring_started")
        }
