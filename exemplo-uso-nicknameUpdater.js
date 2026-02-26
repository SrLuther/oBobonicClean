/**
 * Exemplo de uso do nicknameUpdater
 * 
 * Adicione isto ao seu arquivo principal de bot (ex: bot.js ou main.js)
 */

const { Client, GatewayIntentBits } = require('discord.js');
const { setupNicknameUpdater, syncAllMembersNicknames } = require('./nicknameUpdater');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildModeration,
    GatewayIntentBits.DirectMessages
  ]
});

// Quando o ClientBot está pronto
client.once('ready', () => {
  console.log(`✅ Bot conectado como ${client.user.tag}`);
  
  // Configurar o listener de atualização de apelidos
  setupNicknameUpdater(client);
  
  // Opcional: Sincronizar todos os membros existentes quando o bot inicia
  // Descomente a linha abaixo se quiser sincronizar membros existentes
  // const guild = client.guilds.cache.first();
  // if (guild) {
  //   syncAllMembersNicknames(guild);
  // }
});

// Comando para sincronizar manualmente (opcional)
client.on('messageCreate', async (message) => {
  if (message.content === '!sync-nicknames') {
    if (!message.member.permissions.has('Administrator')) {
      return message.reply('❌ Você precisa ser administrador para usar este comando.');
    }

    await message.reply('🔄 Sincronizando apelidos dos membros...');
    await syncAllMembersNicknames(message.guild);
    await message.reply('✅ Sincronização concluída!');
  }
});

client.login(process.env.TOKEN);

/**
 * INSTRUÇÕES DE USO:
 * 
 * 1. Instale discord.js v14:
 *    npm install discord.js@14
 * 
 * 2. Importe o módulo nicknameUpdater no seu bot principal
 * 
 * 3. Chame setupNicknameUpdater(client) quando o bot estiver pronto
 * 
 * 4. Certifique-se de que o bot tem as seguintes permissões:
 *    - Gerenciar apelidos (Manage Nicknames)
 *    - Ler membros do servidor (Read Members)
 * 
 * 5. O bot deve estar mais alto que os cargos que deseja gerenciar
 * 
 * 6. Variáveis de ambiente necessárias:
 *    - TOKEN: seu token do bot Discord
 */
