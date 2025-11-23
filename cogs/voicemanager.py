# cogs/voicemanager.py
import discord
from discord.ext import commands
import config

class VoiceManager(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        # pega lobby do config
        self.lobby_id = config.LOBBY_CHANNEL_ID
        self.temp_channels = {}

        if self.lobby_id == 0:
            print("⚠️ [VoiceManager] LOBBY_CHANNEL_ID não configurado. O Cog não funcionará.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # CRIAÇÃO
        if after.channel and after.channel.id == self.lobby_id:
            category = after.channel.category
            if not category:
                print(f"❌ [VoiceManager] O canal Lobby (ID: {self.lobby_id}) precisa estar em uma categoria.")
                try:
                    await member.move_to(None)
                except:
                    pass
                return

            channel_name = f"Sala de 🗣️ {member.display_name}"

            new_channel = await category.create_voice_channel(
                name=channel_name,
                user_limit=5,
                reason=f"Canal temporário criado por {member.display_name}"
            )

            try:
                await member.move_to(new_channel)
                self.temp_channels[new_channel.id] = member.id
                print(f"✅ [VoiceManager] Canal temporário '{channel_name}' criado e membro movido.")
            except Exception as e:
                print(f"❌ [VoiceManager] Erro ao mover membro ou criar canal: {e}")

        # EXCLUSÃO
        if before.channel and before.channel.id != self.lobby_id:
            old_channel = before.channel
            if old_channel.id in self.temp_channels:
                if len(old_channel.members) == 0:
                    try:
                        await old_channel.delete(reason="Canal temporário vazio.")
                        del self.temp_channels[old_channel.id]
                        print(f"🗑️ [VoiceManager] Canal temporário '{old_channel.name}' deletado.")
                    except Exception as e:
                        print(f"❌ [VoiceManager] Erro ao deletar canal: {e}")

async def setup(bot):
    await bot.add_cog(VoiceManager(bot))

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
