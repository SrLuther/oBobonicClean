# utils/rcon_client.py
# Cliente RCON Customizado — Implementa Valve RCON Binary Protocol (SRCDS)
# Evita timeout issues da biblioteca rcon, oferece controle total

import socket
import struct
import asyncio
from datetime import datetime
from typing import Optional
import logging

# Logger para debug
logger = logging.getLogger(__name__)

class RconClient:
    """
    Cliente RCON customizado para ARK: Survival Evolved (usa Valve RCON Protocol).
    
    Protocol:
    - TCP socket connection
    - Auth: Send ID=0, Type=3 (SERVERDATA_AUTH), body=password
    - Command: Send ID=arbitrary, Type=2 (SERVERDATA_EXECCOMMAND), body=command
    - Response: Receive packets with Type=0 (SERVERDATA_RESPONSE_VALUE) or Type=1 (SERVERDATA_AUTH_RESPONSE)
    
    Packet structure (32-bit):
    [Size(4 bytes) | ID(4 bytes) | Type(4 bytes) | Body(variable) | Null terminator(2 bytes)]
    """
    
    # Packet types
    TYPE_AUTH_RESPONSE = 2
    TYPE_EXECCOMMAND_RESPONSE = 0
    TYPE_AUTH = 3
    TYPE_EXECCOMMAND = 2
    
    def __init__(self, host: str, port: int, password: str, timeout: float = 30.0):
        """
        Inicializa cliente RCON.
        
        Args:
            host: IP/hostname do servidor ARK
            port: Porta RCON
            password: Senha RCON
            timeout: Timeout de socket em segundos
        """
        self.host = host
        self.port = port
        self.password = password
        self.socket_timeout = timeout
        
        self.socket: Optional[socket.socket] = None
        self.authenticated = False
        
        self._request_id = 0
        self._last_action = ""
        self._last_error = ""
    
    def _get_next_request_id(self) -> int:
        """Genera ID único para cada request."""
        self._request_id += 1
        return self._request_id
    
    def _pack_packet(self, request_id: int, packet_type: int, body: str) -> bytes:
        """
        Cria um pacote RCON.
        
        Format: [Size][ID][Type][Body][Null][Null]
        """
        body_bytes = body.encode('utf-8')
        # Size = ID(4) + Type(4) + Body + 2 null terminators
        size = 4 + 4 + len(body_bytes) + 2
        
        packet = struct.pack('<I', size)  # Size (little-endian)
        packet += struct.pack('<I', request_id)  # Request ID
        packet += struct.pack('<I', packet_type)  # Packet type
        packet += body_bytes  # Body
        packet += b'\x00\x00'  # Null terminators
        
        return packet
    
    def _unpack_packet(self, raw_data: bytes) -> tuple[int, int, str]:
        """
        Parse um pacote RCON recebido.
        
        Returns: (request_id, packet_type, body)
        """
        if len(raw_data) < 12:
            raise ValueError(f"Pacote RCON muito pequeno: {len(raw_data)} bytes")
        
        size = struct.unpack('<I', raw_data[0:4])[0]
        request_id = struct.unpack('<I', raw_data[4:8])[0]
        packet_type = struct.unpack('<I', raw_data[8:12])[0]
        
        body = raw_data[12:-2].decode('utf-8', errors='ignore')
        
        return request_id, packet_type, body
    
    async def connect(self) -> bool:
        """Conecta ao servidor RCON via TCP."""
        try:
            logger.debug(f"[RCON] Conectando a {self.host}:{self.port}")
            self._last_action = "connect"
            
            # Cria socket em thread separada (asyncio)
            loop = asyncio.get_event_loop()
            self.socket = await loop.run_in_executor(
                None,
                lambda: self._create_socket()
            )
            
            logger.debug(f"[RCON] ✅ Socket criado, autenticando...")
            return True
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"[RCON] ❌ Falha ao conectar: {e}")
            return False
    
    def _create_socket(self) -> socket.socket:
        """Cria e conecta socket TCP (executado em thread)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.socket_timeout)
        sock.connect((self.host, self.port))
        return sock
    
    async def authenticate(self) -> bool:
        """Autentica no servidor RCON (envia senha)."""
        if not self.socket:
            self._last_error = "Socket não inicializado"
            logger.error(f"[RCON] ❌ {self._last_error}")
            return False
        
        try:
            self._last_action = "authenticate"
            logger.debug(f"[RCON] Enviando autenticação...")
            
            # Cria packet AUTH
            auth_id = self._get_next_request_id()
            auth_packet = self._pack_packet(auth_id, self.TYPE_AUTH, self.password)
            
            # Envia em thread
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.socket.sendall, auth_packet)
            
            # Recebe resposta
            response = await self._receive_packet()
            
            if response is None:
                self._last_error = "Timeout na resposta de autenticação"
                logger.error(f"[RCON] ❌ {self._last_error}")
                return False
            
            resp_id, resp_type, resp_body = response
            
            # ARK retorna ID=-1 se falha autenticação
            if resp_id == -1:
                self._last_error = "Autenticação falhou — senha incorreta"
                logger.error(f"[RCON] ❌ {self._last_error}")
                return False
            
            if resp_type != self.TYPE_AUTH_RESPONSE:
                self._last_error = f"Resposta inesperada type={resp_type}"
                logger.error(f"[RCON] ❌ {self._last_error}")
                return False
            
            self.authenticated = True
            logger.debug(f"[RCON] ✅ Autenticado com sucesso")
            return True
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"[RCON] ❌ Erro na autenticação: {e}")
            return False
    
    async def _receive_packet(self) -> Optional[tuple[int, int, str]]:
        """Recebe um pacote RCON completo (com timeout) - garante receber tudo."""
        if not self.socket:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            
            # Recebe header (12 bytes: size + id + type)
            header = b''
            while len(header) < 12:
                chunk = await asyncio.wait_for(
                    loop.run_in_executor(None, self.socket.recv, 12 - len(header)),
                    timeout=self.socket_timeout
                )
                if not chunk:
                    raise ConnectionError("Conexão perdida durante receive header")
                header += chunk
            
            if len(header) < 12:
                raise ConnectionError("Header incompleto")
            
            size = struct.unpack('<I', header[0:4])[0]
            
            # SIZE inclui ID(4) + Type(4) + body + null(2), já lemos ID+Type no header
            # Bytes restantes = size - 8
            body_size = size - 8
            body = b''
            while len(body) < body_size:
                remaining = body_size - len(body)
                chunk = await asyncio.wait_for(
                    loop.run_in_executor(None, self.socket.recv, remaining),
                    timeout=self.socket_timeout
                )
                if not chunk:
                    raise ConnectionError(f"Conexão perdida durante receive body (recebeu {len(body)}/{body_size})")
                body += chunk
            
            full_packet = header + body
            return self._unpack_packet(full_packet)
            
        except asyncio.TimeoutError:
            self._last_error = f"Timeout no receive ({self.socket_timeout}s)"
            logger.warning(f"[RCON] ⏱️ {self._last_error}")
            return None
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"[RCON] ❌ Erro no receive: {e}")
            return None
    
    async def execute(self, command: str) -> Optional[str]:
        """
        Executa comando RCON e retorna resposta.
        
        Args:
            command: Comando a executar (ex: "listplayers", "broadcast Hello")
        
        Returns:
            String com resposta, ou None se erro
        """
        if not self.authenticated:
            self._last_error = "Não autenticado"
            logger.error(f"[RCON] ❌ {self._last_error}")
            return None
        
        if not self.socket:
            self._last_error = "Socket fechado"
            logger.error(f"[RCON] ❌ {self._last_error}")
            return None
        
        try:
            self._last_action = f"execute: {command[:30]}"
            logger.debug(f"[RCON] Executando: {command[:50]}")
            
            # Cria packet EXECCOMMAND
            cmd_id = self._get_next_request_id()
            cmd_packet = self._pack_packet(cmd_id, self.TYPE_EXECCOMMAND, command)
            
            # Envia
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.socket.sendall, cmd_packet)
            
            # Recebe resposta — ARK pode enviar múltiplos packets
            full_response = ""
            while True:
                response = await self._receive_packet()
                
                if response is None:
                    logger.warning(f"[RCON] Timeout ao receber resposta")
                    break
                
                resp_id, resp_type, resp_body = response
                
                # Tipo 0 = response value
                if resp_type == self.TYPE_EXECCOMMAND_RESPONSE:
                    full_response += resp_body
                    # Se recebemos o mesmo ID que enviamos, fim da resposta
                    if resp_id == cmd_id:
                        break
                else:
                    logger.debug(f"[RCON] Tipo desconhecido: {resp_type}")
                    break
            
            logger.debug(f"[RCON] ✅ Resposta recebida: {len(full_response)} chars")
            self._last_error = ""
            return full_response
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"[RCON] ❌ Erro na execução: {e}")
            return None
    
    async def disconnect(self):
        """Fecha conexão RCON."""
        if self.socket:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.socket.close)
                logger.debug(f"[RCON] Socket fechado")
            except Exception as e:
                logger.error(f"[RCON] Erro ao fechar socket: {e}")
            finally:
                self.socket = None
                self.authenticated = False
    
    async def health_check(self) -> bool:
        """
        Verifica se conexão está viva.
        Executa comando trivial (getgameinfo) como heartbeat.
        """
        try:
            response = await self.execute("GetGameInfo")
            return response is not None and len(response) > 0
        except Exception as e:
            logger.error(f"[RCON] Health check falhou: {e}")
            return False
    
    def get_status_info(self) -> dict:
        """Retorna info de status para debug."""
        return {
            "host": self.host,
            "port": self.port,
            "connected": self.socket is not None,
            "authenticated": self.authenticated,
            "last_action": self._last_action,
            "last_error": self._last_error,
            "timestamp": datetime.now().isoformat()
        }


# ─────────────────────────────────────────────────────────────
# HELPER: Executar RCON com retry automático
# ─────────────────────────────────────────────────────────────

async def rcon_execute_with_retry(
    host: str,
    port: int,
    password: str,
    command: str,
    max_retries: int = 3,
    timeout: float = 30.0
) -> Optional[str]:
    """
    Executa comando RCON com retry automático.
    
    Retry logic:
    1. Tenta conectar
    2. Se falha, aguarda 1s e tenta novamente
    3. Máximo 3 tentativas
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"[RCON] Tentativa {attempt}/{max_retries}")
            
            client = RconClient(host, port, password, timeout)
            
            # Conecta
            if not await client.connect():
                logger.warning(f"[RCON] Falha na conexão (tentativa {attempt})")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                continue
            
            # Autentica
            if not await client.authenticate():
                logger.warning(f"[RCON] Falha na autenticação (tentativa {attempt})")
                await client.disconnect()
                if attempt < max_retries:
                    await asyncio.sleep(1)
                continue
            
            # Executa
            response = await client.execute(command)
            await client.disconnect()
            
            if response is None:
                logger.warning(f"[RCON] Falha na execução (tentativa {attempt})")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                continue
            
            logger.debug(f"[RCON] ✅ Sucesso na tentativa {attempt}")
            return response
        
        except Exception as e:
            logger.error(f"[RCON] Exceção na tentativa {attempt}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(1)
    
    logger.error(f"[RCON] ❌ Todas as {max_retries} tentativas falharam")
    return None
