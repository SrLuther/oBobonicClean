# cogs/voicemanager.py
import discord
from discord.ext import commands

class VoiceManager(commands.Cog):
    
    def __init__(self, bot, lobby_channel_id: int):
        self.bot = bot
        self.lobby_id = lobby_channel_id
        # Dicionário para rastrear canais temporários criados pelo bot
        self.temp_channels = {} 
        
        if self.lobby_id == 0:
            print("⚠️ [VoiceManager] LOBBY_CHANNEL_ID não configurado. O Cog não funcionará.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        
        # --- 1. LÓGICA DE CRIAÇÃO ---
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
                print(f"✅ [VoiceManager] Canal temporário '{channel_name}' criado e usuário movido.")
            except Exception as e:
                print(f"❌ [VoiceManager] Erro ao mover membro ou criar canal: {e}")
                
        # --- 2. LÓGICA DE EXCLUSÃO ---
        if before.channel and before.channel.id != self.lobby_id:
            old_channel = before.channel
            
            if old_channel.id in self.temp_channels:
                
                # Verifica se o canal ficou vazio (0 membros)
                if len(old_channel.members) == 0:
                    
                    try:
                        await old_channel.delete(reason="Canal temporário ficou vazio.")
                        del self.temp_channels[old_channel.id] 
                        print(f"🗑️ [VoiceManager] Canal temporário '{old_channel.name}' deletado.")
                    except Exception as e:
                        print(f"❌ [VoiceManager] Erro ao deletar o canal: {e}")

# Função de setup para o cog (Recebe o ID como keyword argument)
async def setup(bot, **kwargs):
    if 'lobby_channel_id' in kwargs:
        await bot.add_cog(VoiceManager(bot, lobby_channel_id=kwargs['lobby_channel_id']))
    else:
        print("❌ ERRO: 'lobby_channel_id' não foi fornecido para o cog voicemanager.py.")