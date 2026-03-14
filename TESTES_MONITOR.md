# TESTES - Sistema Inteligente de Monitoramento ARK

## 📋 O que foi desenvolvido

### 1. **server_monitor.py** - Engine de Monitoramento
- ✅ Cache inteligente de presença (quem tá online)
- ✅ Detecção automática de crashes (jogador sumiu por >5min)
- ✅ Histórico de ações (kicks, warnings)
- ✅ Dados persistentes em JSON

### 2. **Integração em ark.py**
- ✅ Background task que roda a cada 30 segundos
- ✅ Sincronização automática entre todos os servidores
- ✅ Log de presença em cache

### 3. **Novos Comandos**
- `!arkkick @user [motivo]` - Kick em TODOS os servidores + log
- `!arkhistorico @user` - Mostra histórico completo de ações
- `!arkatualizar` - Força atualização imediata do monitor
- `!arkmonitor` - Mostra stats gerais

---

## 🧪 COMO TESTAR

### Pré-requisitos
1. ✅ Arquivo servidor: `data/ark_links.json` (com vinculações)
2. ✅ Arquivo servidor: `data/player_monitor.json` (cache criado automaticamente)
3. ✅ Arquivo servidor: `data/player_actions.json` (histórico criado automaticamente)

### Teste 1: Monitor Detectando Players
```
1. Coloque o bot online
2. Rode em terminal: CTRL+J para ver logs
3. Você verá mensagens tipo:
   "[Monitor] ✅ Fjordur: 3 online"
   "[Monitor] ✅ TheIsland: 1 online"
```

### Teste 2: Comando de Kick
```
1. Digite: !arkkick @SeuNome Motion capture bug
2. Bot pede confirmação (botão ✅/❌)
3. Clique em ✅
4. Bot envia "KickPlayer <steam_id>" para TODOS os mapas
5. Resultado mostrado em embed
```

### Teste 3: Histórico
```
1. Digite: !arkhistorico @SeuNome
2. Mostra últimas 10 ações com timestamps
```

### Teste 4: Stats
```
1. Digite: !arkmonitor
2. Mostra:
   - Quantos online agora
   - Quantos crashes suspeitos
   - Total rastreado
   - Total de ações
```

### Teste 5: Atualizar Monitor
```
1. Digite: !arkatualizar
2. Força leitura imediata de TODOS os RCON
3. Mostra resultado
```

---

## 🔍 COMO FUNCIONA (Internamente)

### Loop de Monitoramento (a cada 30s)
```
1. Para cada mapa configurado:
   - Conecta via RCON
   - Executa: listplayers
   - Parse do output (extrai SteamIDs)
   - Atualiza em cache: steam_id → {"online": true, "server": "Fjordur"}

2. Detecta crashes:
   - Se player estava online mas sumiu há >5min
   - Marca como: "crash_suspected"

3. Salva tudo em:
   - data/player_monitor.json
   - data/player_actions.json
```

### Quando você executa !arkkick @user
```
1. Busca discord_id no ark_links.json
2. Extrai steam_id daquele discord
3. Pede confirmação com embed
4. Se confirmado:
   - Para CADA mapa:
     * Envia RCON: "KickPlayer <steam_id>"
   - Registra em data/player_actions.json
   - Mostra resultado com ✅/⏱️/❌
```

---

## 📊 Arquivos de Dados

### data/player_monitor.json
```json
{
  "76561198123456789": {
    "steam_id": "76561198123456789",
    "servers": {
      "Fjordur": {
        "last_online": "2026-03-14T15:30:45.123456",
        "last_offline": null,
        "crash_suspected": false
      },
      "TheIsland": {
        "last_online": "2026-03-14T15:35:21.654321",
        "last_offline": null,
        "crash_suspected": false
      }
    },
    "last_seen": "2026-03-14T15:35:21.654321",
    "status": "online",
    "first_seen": "2026-03-14T10:00:00"
  }
}
```

### data/player_actions.json
```json
{
  "76561198123456789": [
    {
      "timestamp": "2026-03-14T15:40:00.123456",
      "action": "kick",
      "reason": "Motion capture bug",
      "admin_id": 123456789,
      "extra": {
        "discord_user": "Ciano#0001",
        "servers_targeted": ["fjordur", "theisland", "extinction"],
        "results": {
          "Fjordur": {"status": "✅", "response": ""},
          "TheIsland": {"status": "✅", "response": ""},
          "Extinction": {"status": "⏱️", "response": "Timeout"}
        }
      }
    }
  ]
}
```

---

## ⚙️ Configurações (em cogs/ark.py)

```python
CRASH_DETECTION_TIMEOUT = 300  # 5 minutos = crash
MONITOR_CYCLE_SECONDS = 30     # Verifica a cada 30s
```

Ajuste conforme necessário!

---

## 🚨 Possíveis Problemas

### "Usuario nao está vinculado"
- ✅ Usuário precisa fazer `!vincular <steam_url>` primeiro

### Kicks não funcionam
- Verifique se RCON está respondendo: `!rcon fjordur broadcast teste`
- Cheque senha RCON em config.py

### Monitor muito lento
- Aumente `CRASH_DETECTION_TIMEOUT` para 600s (10min)
- Reduza `MONITOR_CYCLE_SECONDS` para 60s

### Cache fica stale
- Execute `!arkatualizar` manualmente
- Ou mude `MONITOR_CYCLE_SECONDS` para 15s

---

## 📝 PRÓXIMOS PASSOS (Sugestões)

1. **Auto-kick de crash** - Detecta crash e faz kick automático
2. **Timeout de inatividade** - Kick se player tiver >1h sem movimento
3. **Whitelist** - Players imunes a kick automático
4. **Appeals** - Sistema pra apelar de kicks
5. **Integração com roles Discord** - VIP players não sofrem kick automático

---

Teste tudo e me avisa qualquer problema! 🚀
