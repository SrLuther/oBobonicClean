"""
Módulo para atualizar automaticamente o apelido (nickname) dos membros
baseado em cargos específicos.

Funciona com discord.py
"""

import asyncio
from typing import Optional

# Mapa de cargos e seus prefixos correspondentes
# Ordem de prioridade: DEV > ADM > GM > VIP
PREFIX_MAP = {
    '1440828410556321882': '[DEV]',
    '1476370938969980928': '[ADM]',
    '1440828412599210135': '[GM]',
    '1476371640244899963': '[VIP]'
}

# Ordem de prioridade dos cargos (do mais alto para o mais baixo)
PRIORITY_ORDER = [
    '1440828410556321882',  # DEV
    '1476370938969980928',  # ADM
    '1440828412599210135',  # GM
    '1476371640244899963'   # VIP
]


def get_highest_priority_prefix(member) -> Optional[str]:
    """
    Obtém o prefixo de maior prioridade que o membro possui.
    
    Args:
        member: Membro do servidor (discord.Member)
    
    Returns:
        Prefixo correspondente ou None se nenhum cargo for encontrado
    """
    for role_id_str in PRIORITY_ORDER:
        role_id = int(role_id_str)
        if member.get_role(role_id):
            return PREFIX_MAP[role_id_str]
    return None


def remove_prefix(nickname: str) -> str:
    """
    Remove o prefixo do nickname se existir.
    
    Args:
        nickname: Nickname atual do membro
    
    Returns:
        Nickname sem o prefixo
    """
    prefixes = list(PREFIX_MAP.values())
    for prefix in prefixes:
        if nickname.startswith(prefix + ' '):
            return nickname[len(prefix) + 1:]
    return nickname


def has_valid_prefix(nickname: str) -> bool:
    """
    Verifica se o nickname já começa com um prefixo válido.
    
    Args:
        nickname: Nickname a verificar
    
    Returns:
        True se já possui um prefixo válido
    """
    prefixes = list(PREFIX_MAP.values())
    return any(nickname.startswith(prefix + ' ') for prefix in prefixes)


async def update_member_nickname(member) -> bool:
    """
    Atualiza o apelido do membro com base em seus cargos.
    
    Args:
        member: Membro a atualizar (discord.Member)
    
    Returns:
        True se o nickname foi atualizado, False caso contrário
    """
    try:
        # Verificar permissões do bot
        if not member.guild.me.guild_permissions.manage_nicknames:
            print(f"[NicknameUpdater] ❌ Sem permissão para gerenciar apelidos")
            return False

        if not member.manageable:
            print(
                f"[NicknameUpdater] ⚠️ Não tenho permissão para gerenciar {member.name}"
            )
            return False

        # Bot não deve mudar a si mesmo
        if member == member.guild.me:
            return False

        # Bots não devem ter apelidos gerenciados
        if member.bot:
            return False

        highest_prefix = get_highest_priority_prefix(member)
        base_name = member.name
        current_nickname = member.nick or base_name

        if highest_prefix:
            # Membro tem um dos cargos especificados
            new_nickname = f"{highest_prefix} {base_name}"
        else:
            # Membro não tem nenhum dos cargos, usar apenas o nome original
            new_nickname = base_name

        # Atualizar apenas se o nickname for diferente
        if current_nickname != new_nickname:
            await member.edit(nick=new_nickname)
            print(
                f"[NicknameUpdater] ✅ Apelido atualizado: {base_name} → {new_nickname}"
            )
            return True
        
        return False

    except Exception as error:
        print(
            f"[NicknameUpdater] ❌ Erro ao atualizar apelido de {member.name}: {error}"
        )
        return False


async def sync_all_members_nicknames(guild) -> dict:
    """
    Sincroniza os apelidos de todos os membros do servidor.
    Útil para sincronizar membros existentes quando o bot inicia.
    
    Args:
        guild: Servidor (discord.Guild)
    
    Returns:
        Dicionário com estatísticas: {updated: int, skipped: int, failed: int}
    """
    try:
        print("[NicknameUpdater] 🔄 Iniciando sincronização de apelidos...")
        
        members = guild.members
        updated = 0
        skipped = 0
        failed = 0

        for member in members:
            try:
                if member.bot:
                    skipped += 1
                    continue

                if not member.manageable:
                    skipped += 1
                    continue

                highest_prefix = get_highest_priority_prefix(member)
                base_name = member.name
                current_nickname = member.nick or base_name

                if highest_prefix:
                    new_nickname = f"{highest_prefix} {base_name}"
                else:
                    new_nickname = base_name

                if current_nickname != new_nickname:
                    try:
                        await member.edit(nick=new_nickname)
                        updated += 1
                        print(
                            f"[NicknameUpdater] ✅ {base_name} → {new_nickname}"
                        )
                    except Exception as e:
                        failed += 1
                        print(
                            f"[NicknameUpdater] ❌ Erro ao sincronizar {base_name}: {e}"
                        )
                else:
                    skipped += 1

                # Pequeno delay para evitar rate limit
                await asyncio.sleep(0.1)

            except Exception as err:
                failed += 1
                print(f"[NicknameUpdater] ❌ Erro no loop: {err}")
                continue

        print(
            f"[NicknameUpdater] ✅ Sincronização concluída: "
            f"{updated} atualizados, {skipped} sem alterações, {failed} falhados"
        )
        
        return {
            'updated': updated,
            'skipped': skipped,
            'failed': failed
        }

    except Exception as error:
        print(f"[NicknameUpdater] ❌ Erro na sincronização geral: {error}")
        return {
            'updated': 0,
            'skipped': 0,
            'failed': 0
        }


def setup_nickname_updater(bot):
    """
    Configura o listener automático para o evento member_update.
    
    Args:
        bot: Cliente Discord (discord.Client ou commands.Bot)
    """
    @bot.event
    async def on_member_update(before, after):
        """
        Evento disparado quando um membro é atualizado (cargos, apelido, etc).
        """
        # Verificar se os cargos foram alterados
        roles_before = set(role.id for role in before.roles)
        roles_after = set(role.id for role in after.roles)
        
        roles_changed = roles_before != roles_after

        if not roles_changed:
            return

        await update_member_nickname(after)
    
    print("[NicknameUpdater] ✅ Listener de atualização de apelidos configurado!")
