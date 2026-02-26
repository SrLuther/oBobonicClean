const { Events } = require('discord.js');

/**
 * Mapa de cargos e seus prefixos correspondentes
 * Ordem de prioridade: DEV > ADM > GM > VIP
 */
const PREFIX_MAP = {
  '1440828410556321882': '[DEV]',
  '1476370938969980928': '[ADM]',
  '1440828412599210135': '[GM]',
  '1476371640244899963': '[VIP]'
};

/**
 * Ordem de prioridade dos cargos (do mais alto para o mais baixo)
 */
const PRIORITY_ORDER = [
  '1440828410556321882', // DEV
  '1476370938969980928', // ADM
  '1440828412599210135', // GM
  '1476371640244899963'  // VIP
];

/**
 * Obtém o prefixo de maior prioridade que o membro possui
 * @param {GuildMember} member - Membro do servidor
 * @returns {string|null} Prefixo correspondente ou null se nenhum cargo for encontrado
 */
function getHighestPriorityPrefix(member) {
  for (const roleId of PRIORITY_ORDER) {
    if (member.roles.cache.has(roleId)) {
      return PREFIX_MAP[roleId];
    }
  }
  return null;
}

/**
 * Remove o prefixo do nickname se existir
 * @param {string} nickname - Nickname atual do membro
 * @returns {string} Nickname sem o prefixo
 */
function removePrefix(nickname) {
  const prefixes = Object.values(PREFIX_MAP);
  for (const prefix of prefixes) {
    if (nickname.startsWith(prefix + ' ')) {
      return nickname.slice(prefix.length + 1);
    }
  }
  return nickname;
}

/**
 * Verifica se o nickname já começa com um prefixo válido
 * @param {string} nickname - Nickname a verificar
 * @returns {boolean} True se já possui um prefixo válido
 */
function hasValidPrefix(nickname) {
  const prefixes = Object.values(PREFIX_MAP);
  return prefixes.some(prefix => nickname.startsWith(prefix + ' '));
}

/**
 * Atualiza o apelido do membro com base em seus cargos
 * @param {GuildMember} newMember - Membro atualizado
 */
async function updateMemberNickname(newMember) {
  try {
    // Verificar permissões do bot
    if (!newMember.manageable) {
      console.warn(
        `[NicknameUpdater] Não tenho permissão para gerenciar ${newMember.user.username}`
      );
      return;
    }

    const highestPrefix = getHighestPriorityPrefix(newMember);
    const baseName = newMember.user.username;
    let newNickname;

    if (highestPrefix) {
      // Membro tem um dos cargos especificados
      newNickname = `${highestPrefix} ${baseName}`;
    } else {
      // Membro não tem nenhum dos cargos, usar apenas o nome original
      newNickname = baseName;
    }

    const currentNickname = newMember.nickname || baseName;

    // Atualizar apenas se o nickname for diferente
    if (currentNickname !== newNickname) {
      await newMember.setNickname(newNickname);
      console.log(
        `[NicknameUpdater] Apelido atualizado: ${baseName} → ${newNickname}`
      );
    }
  } catch (error) {
    console.error(
      `[NicknameUpdater] Erro ao atualizar apelido de ${newMember.user.username}:`,
      error.message
    );
  }
}

/**
 * Configura o listener para o evento guildMemberUpdate
 * @param {Client} client - Cliente Discord.js
 */
function setupNicknameUpdater(client) {
  client.on(Events.GuildMemberUpdate, async (oldMember, newMember) => {
    // Verificar se os cargos foram alterados
    const oldRoles = oldMember.roles.cache.map(role => role.id);
    const newRoles = newMember.roles.cache.map(role => role.id);
    
    const rolesChanged = !oldRoles.every(id => newRoles.includes(id)) ||
                         !newRoles.every(id => oldRoles.includes(id));

    if (!rolesChanged) return;

    await updateMemberNickname(newMember);
  });
}

/**
 * Atualiza o apelido manualmente (útil para sincronizar membros existentes)
 * @param {Guild} guild - Servidor
 */
async function syncAllMembersNicknames(guild) {
  try {
    const members = await guild.members.fetch();
    let updated = 0;
    let skipped = 0;

    for (const [, member] of members) {
      try {
        if (member.user.bot) {
          skipped++;
          continue;
        }

        const highestPrefix = getHighestPriorityPrefix(member);
        const baseName = member.user.username;
        let newNickname;

        if (highestPrefix) {
          newNickname = `${highestPrefix} ${baseName}`;
        } else {
          newNickname = baseName;
        }

        const currentNickname = member.nickname || baseName;

        if (currentNickname !== newNickname && member.manageable) {
          await member.setNickname(newNickname);
          updated++;
        }
      } catch (err) {
        console.error(`Erro ao sincronizar ${member.user.username}:`, err.message);
      }
    }

    console.log(
      `[NicknameUpdater] Sincronização concluída: ${updated} atualizados, ${skipped} ignorados`
    );
  } catch (error) {
    console.error('[NicknameUpdater] Erro na sincronização geral:', error.message);
  }
}

module.exports = {
  setupNicknameUpdater,
  updateMemberNickname,
  syncAllMembersNicknames,
  getHighestPriorityPrefix,
  PREFIX_MAP,
  PRIORITY_ORDER
};
