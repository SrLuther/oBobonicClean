# utils/server_monitor.py
# Sistema inteligente de monitoramento de jogadores ARK
# Detecta crashes, gerencia presença e ações de admin

import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import re

# ─────────────────────────────────────────────────────────────
# CACHE E PERSISTÊNCIA
# ─────────────────────────────────────────────────────────────

class PlayerMonitor:
    """
    Monitora presença de jogadores em tempo real.
    
    Dados armazenados:
    - last_seen: último momento que vimos o player online
    - servers: lista de servidores onde tá online
    - status: "online", "crash_suspected", "offline"
    - actions: histórico de kicks/warnings
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.monitor_file = os.path.join(data_dir, "player_monitor.json")
        self.actions_file = os.path.join(data_dir, "player_actions.json")
        
        self.monitor_data: Dict = {}
        self.actions_data: Dict = {}
        
        self._load_data()
    
    def _load_data(self):
        """Carrega dados do JSON"""
        try:
            if os.path.exists(self.monitor_file):
                with open(self.monitor_file, "r", encoding="utf-8") as f:
                    self.monitor_data = json.load(f)
        except:
            self.monitor_data = {}
        
        try:
            if os.path.exists(self.actions_file):
                with open(self.actions_file, "r", encoding="utf-8") as f:
                    self.actions_data = json.load(f)
        except:
            self.actions_data = {}
    
    def _save_data(self):
        """Salva dados em JSON"""
        try:
            with open(self.monitor_file, "w", encoding="utf-8") as f:
                json.dump(self.monitor_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Monitor] ❌ Erro ao salvar monitor_data: {e}")
        
        try:
            with open(self.actions_file, "w", encoding="utf-8") as f:
                json.dump(self.actions_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Monitor] ❌ Erro ao salvar actions_data: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # MONITORAMENTO DE PRESENÇA
    # ─────────────────────────────────────────────────────────────
    
    def update_player_presence(self, steam_id: str, server_name: str, online: bool):
        """
        Atualiza presença de um jogador.
        
        Args:
            steam_id: ID Steam (17 dígitos)
            server_name: Nome do mapa/servidor
            online: True se online, False se offline
        """
        if steam_id not in self.monitor_data:
            self.monitor_data[steam_id] = {
                "steam_id": steam_id,
                "servers": {},
                "last_seen": None,
                "status": "offline",
                "first_seen": datetime.now().isoformat()
            }
        
        data = self.monitor_data[steam_id]
        
        if online:
            # Jogador online
            if server_name not in data["servers"]:
                data["servers"][server_name] = {
                    "last_online": datetime.now().isoformat(),
                    "last_offline": None,
                    "crash_suspected": False
                }
            else:
                # Atualiza tempo de presença
                data["servers"][server_name]["last_online"] = datetime.now().isoformat()
                data["servers"][server_name]["crash_suspected"] = False
            
            data["last_seen"] = datetime.now().isoformat()
            data["status"] = "online"
        else:
            # Jogador offline
            if server_name in data["servers"]:
                data["servers"][server_name]["last_offline"] = datetime.now().isoformat()
            
            # Verifica se tá online em OUTRO servidor
            still_online = any(
                srv for srv_name, srv in data["servers"].items()
                if srv_name != server_name and srv["last_online"]
            )
            
            if not still_online:
                data["status"] = "offline"
        
        self._save_data()
    
    def mark_crash_suspected(self, steam_id: str, server_name: str, timeout_seconds: int = 300):
        """
        Marca crash suspeito (jogador estava online mas desapareceu).
        
        Args:
            steam_id: ID Steam
            server_name: Nome do servidor
            timeout_seconds: Tempo sem resposta do RCON = crash
        """
        if steam_id not in self.monitor_data:
            return False
        
        data = self.monitor_data[steam_id]
        
        if server_name not in data["servers"]:
            return False
        
        # Verifica se foi visto recently
        last_online = datetime.fromisoformat(data["servers"][server_name]["last_online"])
        time_since = datetime.now() - last_online
        
        if time_since > timedelta(seconds=timeout_seconds):
            data["servers"][server_name]["crash_suspected"] = True
            data["status"] = "crash_suspected"
            self._save_data()
            return True
        
        return False
    
    def get_crashed_players(self, server_name: str, timeout_seconds: int = 300) -> List[str]:
        """Retorna lista de steamIDs de jogadores que provavelmente crasharam."""
        crashed = []
        now = datetime.now()
        
        for steam_id, data in self.monitor_data.items():
            if server_name not in data["servers"]:
                continue
            
            srv_data = data["servers"][server_name]
            
            if srv_data["crash_suspected"]:
                continue  # Já marcado
            
            last_online_str = srv_data.get("last_online")
            if not last_online_str:
                continue
            
            try:
                last_online = datetime.fromisoformat(last_online_str)
                time_since = now - last_online
                
                if time_since > timedelta(seconds=timeout_seconds):
                    crashed.append(steam_id)
            except:
                pass
        
        return crashed
    
    def get_players_on_server(self, server_name: str) -> Dict[str, dict]:
        """Retorna todos os players online em um servidor específico."""
        online_players = {}
        
        for steam_id, data in self.monitor_data.items():
            if server_name in data["servers"]:
                srv_data = data["servers"][server_name]
                if not srv_data.get("crash_suspected"):
                    online_players[steam_id] = {
                        "steam_id": steam_id,
                        "last_online": srv_data.get("last_online"),
                        "status": data.get("status")
                    }
        
        return online_players
    
    def get_player_info(self, steam_id: str) -> Optional[dict]:
        """Retorna informações sobre um jogador."""
        return self.monitor_data.get(steam_id)
    
    def get_player_by_discord(self, discord_id: str, links_db: dict) -> Optional[str]:
        """
        Busca steam_id pelo discord_id usando o arquivo de links.
        
        Args:
            discord_id: ID do Discord
            links_db: Dicionário carregado do ark_links.json
        
        Returns:
            steam_id ou None
        """
        discord_id_str = str(discord_id)
        link = links_db.get(discord_id_str)
        
        if link and link.get("steam_id"):
            return link["steam_id"]
        
        return None
    
    # ─────────────────────────────────────────────────────────────
    # HISTÓRICO DE AÇÕES
    # ─────────────────────────────────────────────────────────────
    
    def log_action(self, steam_id: str, action: str, reason: str, admin_id: Optional[int] = None, extra: Optional[dict] = None):
        """
        Registra uma ação (kick, warn, etc).
        
        Args:
            steam_id: ID Steam do alvo
            action: "kick", "warn", "auto_kick_crash", etc
            reason: Motivo
            admin_id: ID do Discord do admin que executou (None se automático)
            extra: Dados extras (servidores afetados, etc)
        """
        if steam_id not in self.actions_data:
            self.actions_data[steam_id] = []
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "reason": reason,
            "admin_id": admin_id,
            "extra": extra or {}
        }
        
        self.actions_data[steam_id].append(record)
        
        # Mantém apenas últimas 100 ações por jogador
        if len(self.actions_data[steam_id]) > 100:
            self.actions_data[steam_id] = self.actions_data[steam_id][-100:]
        
        self._save_data()
    
    def get_player_history(self, steam_id: str, limit: int = 20) -> List[dict]:
        """Retorna histórico de ações de um jogador."""
        if steam_id not in self.actions_data:
            return []
        
        return self.actions_data[steam_id][-limit:]
    
    def get_recent_kicks(self, steam_id: str, hours: int = 24) -> List[dict]:
        """Retorna kicks recentes de um jogador."""
        history = self.get_player_history(steam_id)
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_kicks = []
        for action in history:
            if action["action"] == "kick":
                try:
                    action_time = datetime.fromisoformat(action["timestamp"])
                    if action_time > cutoff:
                        recent_kicks.append(action)
                except:
                    pass
        
        return recent_kicks
    
    def clear_server_cache(self, server_name: str):
        """Limpa cache de um servidor específico (útil pra forçar atualização)."""
        for steam_id in self.monitor_data:
            if server_name in self.monitor_data[steam_id]["servers"]:
                self.monitor_data[steam_id]["servers"][server_name] = {
                    "last_online": None,
                    "last_offline": None,
                    "crash_suspected": False
                }
        
        self._save_data()
    
    def get_stats(self) -> dict:
        """Retorna estatísticas gerais."""
        total_players = len(self.monitor_data)
        online_now = sum(1 for p in self.monitor_data.values() if p["status"] == "online")
        crash_suspected = sum(1 for p in self.monitor_data.values() if p["status"] == "crash_suspected")
        
        return {
            "total_players_tracked": total_players,
            "online_now": online_now,
            "crash_suspected": crash_suspected,
            "offline": total_players - online_now - crash_suspected,
            "total_actions_logged": sum(len(actions) for actions in self.actions_data.values())
        }


# ─────────────────────────────────────────────────────────────
# HELPER: Parse RCON output
# ─────────────────────────────────────────────────────────────

def parse_rcon_listplayers(response: str) -> List[tuple[str, str]]:
    """
    Parse da resposta RCON 'listplayers'.

    Retorna: [(steam_id, player_name), ...]

    Formato real do ARK:
        0. sergeismitt, 76561198858224963
        1. PROPL@YER013, 76561198133059796
    """
    players = []

    for line in response.splitlines():
        line = line.strip()
        if not line:
            continue
        # Padrão: "N. Nome, 76561XXXXXXXXXXXXXXXXX"
        m = re.match(r"\d+\.\s+(.+?),\s*(\d{17})", line)
        if m:
            name = m.group(1).strip()
            steam_id = m.group(2)
            players.append((steam_id, name))

    return players


# ─────────────────────────────────────────────────────────────
# SINGLETON
# ─────────────────────────────────────────────────────────────

_monitor_instance: Optional[PlayerMonitor] = None

def get_monitor(data_dir: str = "data") -> PlayerMonitor:
    """Retorna instância singleton do monitor."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PlayerMonitor(data_dir)
    return _monitor_instance
