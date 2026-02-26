# Nickname Updater - Documentação

## 📋 Descrição
Módulo Discord.js v14 que atualiza automaticamente o apelido (nickname) dos membros com base em cargos específicos.

## 🎯 Funcionalidades

### Cargos Suportados
- `1440828410556321882` → `[DEV]`
- `1476370938969980928` → `[ADM]`
- `1440828412599210135` → `[GM]`
- `1476371640244899963` → `[VIP]`

### Ordem de Prioridade
1. **DEV** (alta prioridade)
2. **ADM**
3. **GM**
4. **VIP** (baixa prioridade)

Se um membro tiver múltiplos cargos, o prefixo de maior prioridade será aplicado.

## 🚀 Como Usar

### Instalação
```bash
npm install discord.js@14
```

### Importar e Inicializar
```javascript
const { setupNicknameUpdater } = require('./nicknameUpdater');

client.once('ready', () => {
  setupNicknameUpdater(client);
  console.log('✅ Nickname Updater ativado');
});
```

### Funções Exportadas

#### `setupNicknameUpdater(client)`
Configura o listener automático para o evento `guildMemberUpdate`.

```javascript
setupNicknameUpdater(client);
```

#### `updateMemberNickname(newMember)`
Atualiza o apelido de um membro manualmente.

```javascript
await updateMemberNickname(member);
```

#### `syncAllMembersNicknames(guild)`
Sincroniza os apelidos de todos os membros do servidor (útil ao iniciar o bot).

```javascript
await syncAllMembersNicknames(guild);
```

#### `getHighestPriorityPrefix(member)`
Retorna o prefixo de maior prioridade do membro.

```javascript
const prefix = getHighestPriorityPrefix(member);
console.log(prefix); // [DEV], [ADM], [GM], [VIP] ou null
```

## 📋 Exemplo Completo

```javascript
const { Client, GatewayIntentBits } = require('discord.js');
const { setupNicknameUpdater, syncAllMembersNicknames } = require('./nicknameUpdater');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildModeration
  ]
});

client.once('ready', () => {
  console.log(`✅ Bot conectado como ${client.user.tag}`);
  setupNicknameUpdater(client);
  
  // Sincronizar membros existentes
  const guild = client.guilds.cache.first();
  if (guild) {
    syncAllMembersNicknames(guild);
  }
});

client.login(process.env.TOKEN);
```

## ✅ Comportamento

| Situação | Resultado |
|----------|-----------|
| Membro recebe cargo DEV | `[DEV] username` |
| Membro perde cargo DEV, tem ADM | `[ADM] username` |
| Membro perde todos os cargos | `username` |
| Apelido já correto | Sem alteração |
| Bot sem permissão | Log de aviso |

## 🔒 Permissões Necessárias

O bot deve ter as seguintes permissões no servidor:
- ✅ Gerenciar apelidos (`Manage Nicknames`)
- ✅ Ler membros do servidor (`Read Members`)
- ✅ Estar acima dos cargos a gerenciar (na hierarquia de cargos)

## ⚙️ Objetos Exportados

### `PREFIX_MAP`
Objeto mapeando IDs de cargo para prefixos.

```javascript
{
  '1440828410556321882': '[DEV]',
  '1476370938969980928': '[ADM]',
  '1440828412599210135': '[GM]',
  '1476371640244899963': '[VIP]'
}
```

### `PRIORITY_ORDER`
Array definindo a ordem de prioridade dos cargos.

## 📝 Logs

O módulo fornece logs informativos:

```
[NicknameUpdater] Apelido atualizado: Ciano → [DEV] Ciano
[NicknameUpdater] Sincronização concluída: 42 atualizados, 8 ignorados
[NicknameUpdater] Erro ao atualizar apelido de João: Missing Permissions
```

## 🐛 Tratamento de Erros

Todos os erros são capturados e logados:
- Falta de permissões
- Erros de API do Discord
- Exceções gerais

## 💡 Dicas

1. **Sincronização na Inicialização**: Chame `syncAllMembersNicknames()` quando o bot inicia para garantir que todos os membros tenham os nicknames corretos.

2. **Hierarquia de Cargos**: Verifique que o cargo do bot está acima dos cargos que deseja gerenciar.

3. **Intents**: Certifique-se de incluir `GatewayIntentBits.GuildMembers` no seu cliente.

4. **Rate Limiting**: Discord tem limites de rate limiting. Para sincronizar todos os membros, adicione delays se necessário.
