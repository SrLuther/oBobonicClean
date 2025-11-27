# cogs/tickets/modals/feedback_modal.py
import discord
import asyncio
from discord import ui
import config

class FeedbackModal(ui.Modal):
    def __init__(self, channel, closed_by, bot):
        super().__init__(title="Feedback do Ticket")
        self.channel = channel
        self.closed_by = closed_by
        self.bot = bot

        self.feedback = ui.TextInput(
            label="Escreva seu feedback:",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1024,
            placeholder="Como foi seu atendimento?"
        )
        self.add_item(self.feedback)

    async def on_submit(self, interaction: discord.Interaction):
        # resposta imediata ao usuário que submeteu o modal
        await interaction.response.send_message("✅ Feedback recebido. Encerrando ticket...", ephemeral=True)

        cog = self.bot.get_cog("TicketsCog")
        if not cog:
            return

        # Cria transcript
        transcript_file = await cog.create_transcript(
            self.channel,
            feedback=self.feedback.value,
            closed_by=self.closed_by.display_name
        )

        # Envia transcript para canal do ticket
        try:
            await self.channel.send(f"✅ Ticket fechado por {self.closed_by.mention} com feedback enviado.", file=transcript_file)
        except Exception:
            # se envio falhar, ainda tenta arquivar e logar
            pass

        # Arquiva e bloqueia o ticket (renomear + bloquear)
        try:
            await self.channel.edit(name=f"closed-{self.channel.name}", reason=f"Fechado por {self.closed_by.display_name}")
            # bloquear: setar perms padrão (somente leitura) - alternativa dependendo da necessidade
            await self.channel.set_permissions(self.channel.guild.default_role, view_channel=False)
            await self.channel.send("🔒 Este ticket foi fechado e bloqueado.")
        except Exception:
            pass

        # Mover para categoria de arquivo, se existir
        archive_category = self.channel.guild.get_channel(config.TICKET_ARCHIVE_CHANNEL_ID)
        if archive_category:
            try:
                await self.channel.edit(category=archive_category)
            except Exception:
                pass

        # Envia transcript para canal de arquivo (se existir)
        archive_channel = self.channel.guild.get_channel(config.TICKET_ARCHIVE_CHANNEL_ID)
        if archive_channel:
            try:
                await archive_channel.send(f"📜 Transcript do ticket {self.channel.name}", file=transcript_file)
            except Exception:
                pass

        # Log
        await cog.send_log("Ticket Fechado", self.channel, self.closed_by)
