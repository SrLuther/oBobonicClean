# Acesso VPS — oBobonicClean

## ✅ SSH totalmente funcional e não-interativo

Todo acesso remoto ao bot deve ser feito via alias SSH configurado, sem senha ou passphrase.

---

## 🎯 Alias SSH

```bash
ssh multimax "comando"
```

Configurado em `C:\Users\Ciano\.ssh\config` com:

- **Usuário:** multimax
- **Host:** www.multimax.tec.br
- **Chave:** `id_ed25519_nopass` (sem passphrase)
- **KeepAlive:** ativo
- **Host checking:** desabilitado

> ⚠️ Nunca usar `ssh root@...`, `ssh usuario@IP` ou qualquer outro formato — esses ignoram a chave correta e falham na automação.

---

## 📁 Caminhos na VPS

| O quê | Caminho |
|---|---|
| Projeto | `/opt/obobonicclean` |
| Bot principal | `/opt/obobonicclean/bot.py` |
| Venv Python | `/opt/obobonicclean/venv/bin/python` |
| Dados (JSON, logs) | `/opt/obobonicclean/data/` |
| Logs do bot | `/opt/obobonicclean/bot.log` |

Exemplo de uso:

```bash
ssh multimax "cd /opt/obobonicclean && <comando>"
```

---

## ⚙️ Serviço systemd

O bot roda como serviço gerenciado pelo systemd:

- **Nome do serviço:** `obobonic.service`
- **Reinício automático:** sempre (5 segundos de delay)
- **Usuário que executa:** `multimax`

### Comandos úteis

```bash
# Ver status do bot
ssh multimax "systemctl status obobonic"

# Reiniciar o bot
ssh multimax "systemctl restart obobonic"

# Parar o bot
ssh multimax "systemctl stop obobonic"

# Ver logs em tempo real
ssh multimax "journalctl -u obobonic -f"

# Ver últimas 50 linhas de log
ssh multimax "journalctl -u obobonic -n 50 --no-pager"
```

---

## 🔄 Deploy / Atualização de código

```bash
# Atualizar código do repositório
ssh multimax "cd /opt/obobonicclean && git pull"

# Atualizar dependências
ssh multimax "cd /opt/obobonicclean && venv/bin/pip install -r requirements.txt"

# Atualizar código + dependências + reiniciar
ssh multimax "cd /opt/obobonicclean && git pull && venv/bin/pip install -r requirements.txt && systemctl restart obobonic"
```

---

## 🔍 Verificações rápidas

```bash
# Verificar se o processo está rodando
ssh multimax "pgrep -a python | grep bot.py"

# Ver uso de memória/CPU do bot
ssh multimax "systemctl status obobonic --no-pager"
```
