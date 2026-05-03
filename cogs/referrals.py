"""
🎫 Sistema de Indicação - Cog para Discord Bot
Permite que membros gerem códigos de indicação únicos e ganhem pontos
"""

import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import asyncio
import random
import string
import traceback
import calendar
from typing import Optional

# Importa configurações
from config import (
    REFERRALS_GENERATE_ID_CHANNEL_ID,
    REFERRALS_FORM_CHANNEL_ID,
    REFERRALS_PENDING_CHANNEL_ID,
    REFERRALS_APPROVED_CHANNEL_ID,
    REFERRALS_LOGS_CHANNEL_ID,
    REFERRALS_RANKING_CHANNEL_ID,
    REFERRALS_ADMIN_ROLE_IDS,
    GUILD_ID,
    MOD_ROLE_IDS
)

# Constantes
REFERRAL_POINTS_REFERRER = 75    # Pontos para quem indicou
REFERRAL_POINTS_REFERRED = 50    # Pontos para quem foi indicado
REFERRALS_FILE = ".bancos/referrals.json"
RANKING_PRIZES_FILE = "data/ranking_prizes.json"  # Histórico de prêmios distribuídos

# Prêmios por posição
RANKING_PRIZES = {
    1: 1000,  # 1º lugar
    2: 750,   # 2º lugar
    3: 500    # 3º lugar
}

# ====================
# FUNÇÕES AUXILIARES
# ====================

def load_referral_data():
    """Carrega dados de indicações do JSON com validação."""
    default_data = {
        "referral_codes": {},      # {code: {discord_id, username, created_at, referrals_count, total_earned_pending, total_earned_paid}}
        "referrals": [],           # [{ referrer_id, referred_id, code, status, created_at, approved_at }]
        "used_ids": [],            # [id1, id2, id3] - para evitar duplicações
        "history": {}              # {month_key: {ranking_data, timestamp}} - histórico de meses anteriores
    }
    
    # Garante que o diretório existe
    os.makedirs(os.path.dirname(REFERRALS_FILE) or ".", exist_ok=True)
    
    if not os.path.exists(REFERRALS_FILE):
        print(f"[Referrals] 📝 Arquivo de referrals não encontrado. Criando novo: {REFERRALS_FILE}")
        save_referral_data(default_data)
        return default_data
    
    try:
        with open(REFERRALS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"[Referrals] ⚠️ Arquivo {REFERRALS_FILE} vazio! Restaurando estrutura padrão...")
                save_referral_data(default_data)
                return default_data
            
            data = json.loads(content)
            
            # Valida estrutura
            if "referral_codes" not in data:
                data["referral_codes"] = {}
            if "referrals" not in data:
                data["referrals"] = []
            if "used_ids" not in data:
                data["used_ids"] = []
            if "history" not in data:
                data["history"] = {}
            
            print(f"[Referrals] ✅ Dados carregados: {len(data['referral_codes'])} códigos, {len(data['referrals'])} indicações, {len(data['history'])} meses arquivados")
            return data
            
    except json.JSONDecodeError as e:
        print(f"[Referrals] ❌ ERRO CRÍTICO: JSON inválido em {REFERRALS_FILE}: {e}")
        print(f"[Referrals] 🔧 Criando backup e restaurando estrutura padrão...")
        
        try:
            backup_file = REFERRALS_FILE + ".bak"
            if os.path.exists(REFERRALS_FILE):
                os.rename(REFERRALS_FILE, backup_file)
                print(f"[Referrals] 💾 Backup salvo em: {backup_file}")
        except Exception as backup_e:
            print(f"[Referrals] ⚠️ Erro ao criar backup: {backup_e}")
        
        save_referral_data(default_data)
        return default_data
        
    except Exception as e:
        print(f"[Referrals] ❌ Erro ao carregar JSON: {e}")
        traceback.print_exc()
        return default_data

def save_referral_data(data):
    """Salva dados de indicações no JSON com validação."""
    try:
        os.makedirs(os.path.dirname(REFERRALS_FILE) or ".", exist_ok=True)
        
        # Valida dados antes de salvar
        if not isinstance(data, dict):
            print(f"[Referrals] ❌ Erro: dados não é dicionário!")
            return False
        
        # Garante estrutura mínima
        if "referral_codes" not in data:
            data["referral_codes"] = {}
        if "referrals" not in data:
            data["referrals"] = []
        if "used_ids" not in data:
            data["used_ids"] = []
        
        # Salva com encoding UTF-8 e indentação
        with open(REFERRALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print(f"[Referrals] ✅ Dados salvos com sucesso!")
        return True
        
    except Exception as e:
        print(f"[Referrals] ❌ ERRO CRÍTICO ao salvar JSON: {e}")
        traceback.print_exc()
        return False

def generate_unique_referral_code():
    """Gera código único no formato A1234."""
    data = load_referral_data()
    used_ids = data.get("used_ids", [])
    
    while True:
        letter = random.choice(string.ascii_uppercase)
        numbers = ''.join(random.choices(string.digits, k=4))
        code = f"{letter}{numbers}"
        
        if code not in used_ids:
            return code

def is_admin_or_mod(user_id: int) -> bool:
    """Verifica se usuário é admin ou mod."""
    # Você pode expandir esta lógica conforme necessário
    return user_id in MOD_ROLE_IDS or user_id in REFERRALS_ADMIN_ROLE_IDS

def get_referral_code(user_id: int):
    """Obtém código de indicação do usuário."""
    data = load_referral_data()
    
    for code, info in data.get("referral_codes", {}).items():
        if info.get("discord_id") == user_id:
            return code
    
    return None

def get_referrer_stats(user_id: int):
    """Obtém estatísticas do referidor."""
    data = load_referral_data()
    
    for code, info in data.get("referral_codes", {}).items():
        if info.get("discord_id") == user_id:
            return {
                "code": code,
                "referrals_count": info.get("referrals_count", 0),
                "pending_points": info.get("total_earned_pending", 0),
                "approved_points": info.get("total_earned_paid", 0)
            }
    
    return None

def get_referred_stats(user_id: int):
    """Obtém estatísticas de quem foi indicado."""
    data = load_referral_data()
    
    pending_points = 0
    approved_points = 0
    
    for referral in data.get("referrals", []):
        if referral.get("referred_id") == user_id:
            if referral.get("status") == "pending":
                pending_points += REFERRAL_POINTS_REFERRED
            elif referral.get("status") == "approved":
                approved_points += REFERRAL_POINTS_REFERRED
    
    return {
        "pending_points": pending_points,
        "approved_points": approved_points
    }

def has_referral_code(user_id: int) -> bool:
    """Verifica se usuário já tem código."""
    return get_referral_code(user_id) is not None

def validate_referral_submission(user_id: int, code_value: str, data: dict) -> tuple[bool, str]:
    """
    Valida se um usuário pode enviar uma indicação.
    
    Regras:
    1. Cada pessoa só pode ser indicada UMA VEZ
    2. Cada pessoa só pode enviar UMA indicação
    3. Não pode usar seu próprio código
    
    Returns:
        (is_valid, error_message)
    """
    
    # Regra 1: Verifica se a pessoa já foi indicada antes
    for referral in data.get("referrals", []):
        if referral.get("referred_id") == user_id:
            existing_referrer = referral.get("referrer_name", "Desconhecido")
            status = referral.get("status", "pending")
            return False, f"JÁ_INDICADO|{existing_referrer}|{status}"
    
    # Regra 2: Verifica se a pessoa já enviou uma indicação antes
    user_as_referred = any(r.get("referred_id") == user_id for r in data.get("referrals", []))
    user_as_referrer = any(r.get("referrer_id") == user_id for r in data.get("referrals", []))
    
    if user_as_referred and not user_as_referrer:
        return False, "JÁ_ENVIOU|INDICADO_APENAS"
    
    # Regra 3: Verifica se está tentando usar seu próprio código
    if code_value in data.get("referral_codes", {}):
        code_info = data["referral_codes"][code_value]
        referrer_id = code_info.get("discord_id")
        
        if referrer_id == user_id:
            return False, "PROPRIO_CODIGO"
    
    return True, "OK"

def get_top_referrers(limit: int = 10) -> list:
    """
    Obtém o ranking dos top N indicadores com mais indicações aprovadas NO MÊS ATUAL.
    
    Returns:
        Lista de tuplas: [(username, referrer_id, approved_count, approved_points), ...]
    """
    from datetime import datetime
    
    data = load_referral_data()
    referrers_stats = {}
    
    # Pega mês/ano atual
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # Conta indicações aprovadas por referidor APENAS DO MÊS ATUAL
    for referral in data.get("referrals", []):
        if referral.get("status") == "approved":
            # Verifica se é do mês atual
            approved_at = referral.get("approved_at")
            if approved_at:
                try:
                    approval_date = datetime.fromisoformat(approved_at)
                    # Se não for do mês atual, pula
                    if approval_date.month != current_month or approval_date.year != current_year:
                        continue
                except:
                    pass  # Se não conseguir fazer parse, ignora
            
            referrer_id = referral.get("referrer_id")
            referrer_name = referral.get("referrer_name", "Desconhecido")
            
            if referrer_id not in referrers_stats:
                referrers_stats[referrer_id] = {
                    "name": referrer_name,
                    "approved_count": 0,
                    "approved_points": 0
                }
            
            referrers_stats[referrer_id]["approved_count"] += 1
            referrers_stats[referrer_id]["approved_points"] += REFERRAL_POINTS_REFERRER
    
    # Ordena por número de aprovações (depois por pontos)
    sorted_referrers = sorted(
        referrers_stats.items(),
        key=lambda x: (x[1]["approved_count"], x[1]["approved_points"]),
        reverse=True
    )[:limit]
    
    return sorted_referrers

def create_ranking_view(bot: commands.Bot) -> discord.ui.View:
    """Cria a view com botões para o ranking de indicadores."""
    
    class RankingControlsView(discord.ui.View):
        def __init__(self, bot_instance):
            super().__init__(timeout=None)  # Timeout None = permanente
            self.bot_instance = bot_instance
        
        @discord.ui.button(label="🔄 Finalizar Mês", style=discord.ButtonStyle.danger, emoji="🔄")
        async def reset_month_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """Botão de reset - apenas para admins"""
            
            # Verifica permissão
            if not is_admin_or_mod(interaction.user.id):
                await interaction.response.send_message("❌ Apenas administradores podem fazer isso!", ephemeral=True)
                return
            
            await interaction.response.defer(thinking=True)
            
            try:
                data = load_referral_data()
                now = datetime.now()
                current_month_key = f"{now.year}-{now.month:02d}"
                
                # Calcula top 10 do mês atual ANTES de mover
                top_referrers = get_top_referrers(10)
                ranking_data = []
                for referrer_id, stats in top_referrers:
                    ranking_data.append({
                        "position": len(ranking_data) + 1,
                        "referrer_id": referrer_id,
                        "referrer_name": stats['name'],
                        "approved_count": stats['approved_count'],
                        "approved_points": stats['approved_points']
                    })
                
                # Arquiva dados do mês atual
                if "history" not in data:
                    data["history"] = {}
                
                data["history"][current_month_key] = {
                    "archived_at": datetime.now().isoformat(),
                    "archived_by": str(interaction.user),
                    "ranking": ranking_data,
                    "total_approved": len([r for r in data.get("referrals", []) if r.get("status") == "approved"]),
                    "month_name": now.strftime("%B de %Y")
                }
                
                # Remove APENAS as indicações aprovadas do mês atual
                data["referrals"] = [
                    r for r in data.get("referrals", [])
                    if r.get("status") != "approved"
                ]
                
                # Salva dados
                save_referral_data(data)
                
                result_embed = discord.Embed(
                    title="✅ Mês Finalizado com Sucesso!",
                    description=(
                        f"📅 **Mês Finalizado:** {current_month_key}\n\n"
                        f"✨ O ranking foi arquivado para histórico!\n"
                    ),
                    color=discord.Color.green()
                )
                
                # Mostra top 3
                if ranking_data:
                    if result_embed.description is None:
                        result_embed.description = ""
                    result_embed.description += f"🎊 **Top 3:**\n"
                    if len(ranking_data) >= 1:
                        result_embed.description += f"🥇 {ranking_data[0]['referrer_name']} - {ranking_data[0]['approved_count']} indicações\n"
                    if len(ranking_data) >= 2:
                        result_embed.description += f"🥈 {ranking_data[1]['referrer_name']} - {ranking_data[1]['approved_count']} indicações\n"
                    if len(ranking_data) >= 3:
                        result_embed.description += f"🥉 {ranking_data[2]['referrer_name']} - {ranking_data[2]['approved_count']} indicações\n"
                
                result_embed.add_field(
                    name="📊 Estatísticas",
                    value=(
                        f"✅ **Indicações aprovadas:** {data['history'][current_month_key]['total_approved']}\n"
                        f"🔄 **Novo mês iniciado!**"
                    ),
                    inline=False
                )
                
                result_embed.set_footer(text=f"Finalizado por: {interaction.user}")
                result_embed.timestamp = datetime.now()
                
                await interaction.followup.send(embed=result_embed)
                
                # Log no canal de logs
                try:
                    log_channel = self.bot_instance.get_channel(REFERRALS_LOGS_CHANNEL_ID)
                    if log_channel and isinstance(log_channel, discord.TextChannel):
                        await log_channel.send(embed=result_embed)
                except:
                    pass
                
            except Exception as e:
                print(f"[Referrals] ❌ Erro ao finalizar mês: {e}")
                traceback.print_exc()
                await interaction.followup.send(f"❌ Erro: {str(e)[:100]}", ephemeral=True)
        
        @discord.ui.button(label="📁 Ver Histórico", style=discord.ButtonStyle.primary, emoji="📁")
        async def view_history_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            """Botão para ver histórico de rankings anteriores"""
            
            await interaction.response.defer(thinking=True)
            
            try:
                data = load_referral_data()
                history = data.get("history", {})
                
                if not history:
                    empty_embed = discord.Embed(
                        title="📁 Histórico de Rankings",
                        description="Ainda não há meses arquivados.",
                        color=discord.Color.greyple()
                    )
                    await interaction.followup.send(embed=empty_embed, ephemeral=True)
                    return
                
                # Cria dropdown com meses disponíveis
                class RankingHistorySelect(discord.ui.Select):
                    def __init__(self, history_data):
                        self.history_data = history_data
                        
                        options = []
                        for month_key in sorted(history_data.keys(), reverse=True):
                            month_info = history_data[month_key]
                            top_name = month_info.get("ranking", [{}])[0].get("referrer_name", "N/A") if month_info.get("ranking") else "N/A"
                            label = f"{month_key} - 🥇 {top_name}"
                            options.append(
                                discord.SelectOption(
                                    label=label[:100],
                                    value=month_key,
                                    description=f"{month_info.get('total_approved', 0)} indicações aprovadas"
                                )
                            )
                        
                        super().__init__(
                            placeholder="Escolha um mês para visualizar...",
                            options=options[:25]
                        )
                    
                    async def callback(self, select_interaction: discord.Interaction):
                        await select_interaction.response.defer()
                        
                        selected_month = self.values[0]
                        month_data = self.history_data[selected_month]
                        
                        # Cria embed com ranking do mês selecionado
                        embed = discord.Embed(
                            title=f"🏆 Ranking - {month_data.get('month_name', selected_month)}",
                            color=discord.Color.gold()
                        )
                        
                        embed.description = (
                            f"📅 **Período:** {selected_month}\n"
                            f"📊 **Total de indicações aprovadas:** {month_data.get('total_approved', 0)}"
                        )
                        
                        ranking_text = ""
                        medals = ["🥇", "🥈", "🥉"]
                        for i, entry in enumerate(month_data.get("ranking", [])):
                            medal = medals[i] if i < 3 else f"{i+1}️⃣"
                            ranking_text += (
                                f"{medal} **{entry['position']}º** - {entry['referrer_name']}\n"
                                f"   📊 {entry['approved_count']} indicações • 💰 {entry['approved_points']} pontos\n\n"
                            )
                        
                        if ranking_text:
                            embed.add_field(
                                name="🏆 Ranking",
                                value=ranking_text.strip(),
                                inline=False
                            )
                        else:
                            embed.description += "\n\n*Nenhum dado de ranking para este mês.*"
                        
                        embed.add_field(
                            name="📌 Informações",
                            value=(
                                f"🔐 **Arquivado por:** {month_data.get('archived_by', 'Sistema')}\n"
                                f"⏰ **Data:** {month_data.get('archived_at', 'N/A')[:10]}"
                            ),
                            inline=False
                        )
                        
                        embed.set_footer(text="Histórico de rankings - Dados preservados para consulta")
                        embed.timestamp = datetime.now()
                        
                        await select_interaction.followup.send(embed=embed, ephemeral=False)
                
                class RankingHistoryView(discord.ui.View):
                    def __init__(self, history_data):
                        super().__init__()
                        self.add_item(RankingHistorySelect(history_data))
                
                info_embed = discord.Embed(
                    title="📁 Histórico de Rankings",
                    description="Selecione um mês no dropdown abaixo para visualizar o ranking histórico:",
                    color=discord.Color.blue()
                )
                info_embed.add_field(
                    name="📊 Meses Disponíveis",
                    value=f"Total: **{len(history)}** mês(es) arquivado(s)",
                    inline=False
                )
                
                view = RankingHistoryView(history)
                await interaction.followup.send(embed=info_embed, view=view, ephemeral=True)
                
            except Exception as e:
                print(f"[Referrals] ❌ Erro ao exibir histórico: {e}")
                traceback.print_exc()
                await interaction.followup.send(f"❌ Erro: {str(e)[:100]}", ephemeral=True)
    
    return RankingControlsView(bot)

def create_ranking_embed(bot: commands.Bot) -> discord.Embed:
    """Cria o embed do ranking de indicadores com design melhorado (apenas mês atual)."""
    from datetime import datetime, timedelta
    
    top_referrers = get_top_referrers(10)
    
    # Determina o último dia do mês
    today = datetime.now()
    last_day = calendar.monthrange(today.year, today.month)[1]
    days_until_end = last_day - today.day
    
    # Formato do mês
    month_name = today.strftime('%B de %Y')  # Ex: "April de 2026"
    
    embed = discord.Embed(
        title="🏆 TOP 10 INDICADORES",
        color=discord.Color.gold()
    )
    
    # Descrição com informações do mês
    embed.description = f"📅 **Ranking de {month_name}**\n💰 Apenas indicações aprovadas neste mês contam"
    
    if not top_referrers:
        # Mensagem motivacional quando não há dados
        embed.description = (
            f"📅 **Ranking de {month_name}**\n\n"
            "✨ **Seja o Primeiro!** ✨\n\n"
            "Ainda não há ninguém no ranking... essa é sua chance! 🚀\n\n"
            "📢 **Como funciona:**\n"
            f"• Gere seu código único 🎫 ➜ <#{REFERRALS_GENERATE_ID_CHANNEL_ID}>\n"
            "• Compartilhe com amigos 👥\n"
            "• Indique seus colegas 🤝\n"
            "• Suba no ranking 📈\n\n"
            "🎁 **Prêmio Especial:**\n"
            f"Quem estiver em **1º lugar no último dia do mês** ganha:\n"
            "🎉 **1.000 PONTOS NA LOJA** 🎉\n"
        )
        embed.add_field(
            name="🌟 Comece Agora!",
            value=(
                "Acesse o **Gerador de ID de Indicação** e clique em 🎫 para criar seu código.\n"
                "Depois compartilhe com seus amigos! Quanto mais indicações, maior sua chance de ganhar! 🏅"
            ),
            inline=False
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1000000000000000000/1000000000000000000/rocket.png")
        
    else:
        # Ranking com dados
        ranking_text = ""
        medals = ["🥇", "🥈", "🥉"]
        stars = ["⭐", "⭐⭐", "⭐⭐⭐"]
        
        for idx, (referrer_id, stats) in enumerate(top_referrers, 1):
            medal = medals[idx - 1] if idx <= 3 else f"#{idx}"
            approved_count = stats["approved_count"]
            approved_points = stats["approved_points"]
            name = stats["name"]
            
            # Tenta obter menção do Discord
            try:
                user = bot.get_user(referrer_id)
                mention = user.mention if user else f"@{name}"
            except:
                mention = f"@{name}"
            
            # Adiciona estrelas para os top 3
            star_display = stars[idx - 1] if idx <= 3 else ""
            ranking_text += f"{medal} {mention} {star_display}\n"
            ranking_text += f"   📊 {approved_count} indicações • 💰 {approved_points} pontos\n\n"
        
        embed.description = (
            "🔥 **Veja quem lidera o mês!** 🔥\n"
            "Os melhores indicadores ganham reconhecimento e prêmios! 🎁"
        )
        
        embed.add_field(
            name="🏆 Ranking",
            value=ranking_text.strip(),
            inline=False
        )
        
        # Informação do top 1
        if top_referrers:
            top_user_id, top_stats = top_referrers[0]
            try:
                top_user = bot.get_user(top_user_id)
                top_mention = top_user.mention if top_user else f"@{top_stats['name']}"
            except:
                top_mention = f"@{top_stats['name']}"
            
            embed.add_field(
                name="👑 Líder do Mês",
                value=f"{top_mention} está arrasando com {top_stats['approved_count']} indicações! 🚀",
                inline=False
            )
    
    # Informação do prêmio sempre visível
    prize_text = (
        f"🎊 **PRÊMIO ESPECIAL DO MÊS** 🎊\n"
        f"─────────────────────────────────\n"
        f"💎 Quem terminar em **1º lugar** no último dia do mês recebe:\n"
        f"✨ **1.000 PONTOS NA LOJA** ✨\n"
        f"─────────────────────────────────\n"
        f"⏰ Restam apenas **{max(0, days_until_end)} dias** neste mês!\n\n"
        f"🎯 **Não perca a chance de ser um lendário!** 🎯"
    )
    
    embed.add_field(
        name="🎁 RECOMPENSA DO MÊS",
        value=prize_text,
        inline=False
    )
    
    # Footer motivacional com info sobre reset
    motivational_messages = [
        "🚀 Quanto mais indicações, melhor! Bora indicar!",
        "💪 Seu código é seu superpoder! Compartilhe!",
        "🌟 Seja lendário! Indique seus amigos!",
        "🎯 O último dia do mês tá chegando! Corre!",
        "🏅 Grande responsabilidade, grande recompensa!",
        "🎮 Indique como se fosse um game! Ganhe pontos!",
    ]
    
    import random
    footer_message = random.choice(motivational_messages)
    
    # Adiciona info sobre reset
    embed.add_field(
        name="🔄 Ranking Mensal",
        value=(
            f"Este ranking considera **APENAS o mês atual** ({today.strftime('%B de %Y')}).\n\n"
            f"✨ **No próximo mês:**\n"
            f"🔘 Clique no botão 🔄 **Finalizar Mês** (admin)\n"
            f"📁 Histórico será preservado no botão 📁 **Ver Histórico**\n"
            f"🎯 Novo ranking começará zerado!"
        ),
        inline=False
    )
    
    embed.set_footer(text=f"⏱️ Atualizado automaticamente • {footer_message}")
    embed.timestamp = datetime.now()
    
    return embed

# ====================
# VIEWS COM BUTTONS
# ====================

class GenerateCodeButton(discord.ui.View):
    """View com botão para gerar código."""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🎫 Gerar Meu Código", style=discord.ButtonStyle.primary, custom_id="btn_generate_code")
    async def generate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        guild = interaction.guild
        
        if not guild:
            await interaction.response.send_message("❌ Erro ao obter servidor!", ephemeral=True)
            return
        
        member = guild.get_member(user_id)
        if not member:
            await interaction.response.send_message("❌ Você não está no servidor!", ephemeral=True)
            return
        
        # Verifica se já tem código
        if has_referral_code(user_id):
            existing_code = get_referral_code(user_id)
            embed = discord.Embed(
                title="⚠️ Código Já Existe",
                description=f"Seu código: `{existing_code}`\n\nCompartilhe com amigos para ganhar pontos!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Gera novo código
        new_code = generate_unique_referral_code()
        
        # Salva
        data = load_referral_data()
        data["referral_codes"][new_code] = {
            "discord_id": user_id,
            "username": member.name,
            "created_at": datetime.now().isoformat(),
            "referrals_count": 0,
            "total_earned_pending": 0,
            "total_earned_paid": 0
        }
        data["used_ids"].append(new_code)
        save_referral_data(data)
        
        # Responde
        embed = discord.Embed(
            title="🎉 Código Gerado com Sucesso!",
            description=f"**`{new_code}`**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📋 Como usar?",
            value="Compartilhe este código com seus amigos!\nEles vão usá-lo ao enviar a indicação.",
            inline=False
        )
        embed.add_field(
            name="💰 Recompensa",
            value=f"+{REFERRAL_POINTS_REFERRER} pontos por indicação validada!",
            inline=False
        )
        embed.set_footer(text="Código único e pessoal - não compartilhe com estranhos!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SubmitReferralModal(discord.ui.Modal, title="📝 Indicação"):
    """Modal simplificado para enviar indicação."""
    
    code = discord.ui.TextInput(
        label="Código de Indicação",
        placeholder="Ex: A1234",
        required=True,
        max_length=10
    )
    
    steam_link = discord.ui.TextInput(
        label="Link do seu perfil Steam",
        placeholder="https://steamcommunity.com/id/seu_usuario",
        required=True,
        max_length=500
    )
    
    extra_info = discord.ui.TextInput(
        label="Informações adicionais (opcional)",
        placeholder="Como você conheceu o servidor?",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        
        user_id = interaction.user.id
        guild = interaction.guild
        
        if not guild:
            await interaction.followup.send("❌ Erro ao obter servidor!", ephemeral=True)
            return
        
        member = guild.get_member(user_id)
        if not member:
            await interaction.followup.send("❌ Você não está no servidor!", ephemeral=True)
            return
        
        # Valida código
        data = load_referral_data()
        
        code_value = str(self.code).strip().upper()
        if code_value not in data.get("referral_codes", {}):
            embed = discord.Embed(
                title="❌ Código Inválido",
                description=f"Código `{code_value}` não existe ou está incorreto!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # ========== VALIDAÇÕES CRÍTICAS ==========
        is_valid, error_reason = validate_referral_submission(user_id, code_value, data)
        
        if not is_valid:
            if error_reason.startswith("JÁ_INDICADO"):
                parts = error_reason.split("|")
                existing_referrer = parts[1] if len(parts) > 1 else "Desconhecido"
                status = parts[2] if len(parts) > 2 else "pending"
                
                status_emoji = "⏳" if status == "pending" else "✅" if status == "approved" else "❌"
                status_text = "Pendente" if status == "pending" else "Aprovado" if status == "approved" else "Rejeitado"
                
                embed = discord.Embed(
                    title="⚠️ Você Já Foi Indicado",
                    description=f"Cada pessoa só pode ser indicada uma única vez!",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Indicador", value=f"{status_emoji} {existing_referrer}", inline=False)
                embed.add_field(name="Status", value=status_text, inline=False)
                embed.set_footer(text="Não é possível ser indicado novamente.")
                
            elif error_reason == "JÁ_ENVIOU|INDICADO_APENAS":
                embed = discord.Embed(
                    title="❌ Ação Não Permitida",
                    description="Você não pode enviar uma indicação porque você mesmo foi indicado!",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="📌 Regra",
                    value="Apenas indicadores (pessoas com código gerado) podem enviar indicações.",
                    inline=False
                )
            
            elif error_reason == "PROPRIO_CODIGO":
                embed = discord.Embed(
                    title="❌ Código Inválido",
                    description="Você não pode usar seu próprio código de indicação!",
                    color=discord.Color.red()
                )
            
            else:
                embed = discord.Embed(
                    title="❌ Erro na Validação",
                    description="Não foi possível processar sua indicação.",
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # ========== FIM DAS VALIDAÇÕES ==========
        
        code_info = data["referral_codes"][code_value]
        referrer_id = code_info.get("discord_id")
        referrer_name = code_info.get("username", "Desconhecido")
        
        # Tenta obter o usuário do servidor para nome atualizado
        try:
            referrer = guild.get_member(referrer_id)
            if referrer:
                referrer_name = referrer.name
        except:
            pass
        
        # View de confirmação
        class ConfirmReferralView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)
            
            @discord.ui.button(label="✅ Confirmar Indicação", style=discord.ButtonStyle.success)
            async def confirm_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.defer(thinking=True)
                
                try:
                    # Salva a indicação
                    referral_entry = {
                        "referrer_id": referrer_id,
                        "referred_id": user_id,
                        "code": code_value,
                        "referrer_name": referrer_name,
                        "referred_name": member.name,
                        "steam_link": str(self_modal.steam_link),
                        "extra_info": str(self_modal.extra_info) or "Nenhuma",
                        "status": "pending",
                        "created_at": datetime.now().isoformat(),
                        "approved_at": None
                    }
                    
                    data["referrals"].append(referral_entry)
                    data["referral_codes"][code_value]["referrals_count"] = data["referral_codes"][code_value].get("referrals_count", 0) + 1
                    data["referral_codes"][code_value]["total_earned_pending"] += REFERRAL_POINTS_REFERRER
                    save_referral_data(data)
                    
                    # Atualiza contador de indicações pendentes no nome do canal
                    await update_pending_counter(button_interaction.client)
                    
                    # Confirmação
                    referrer_mention = f"<@{referrer_id}> • [Perfil](https://discord.com/users/{referrer_id})"
                    embed = discord.Embed(
                        title="✅ Indicação Confirmada e Enviada!",
                        description=f"Obrigado por se juntar a nós via {referrer_mention}!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Seu Nick", value=member.name, inline=True)
                    embed.add_field(name="Indicador", value=referrer_mention, inline=True)
                    embed.add_field(name="Código", value=f"`{code_value}`", inline=True)
                    embed.add_field(name="Pontos", value=f"+{REFERRAL_POINTS_REFERRED} (pendente)", inline=True)
                    embed.add_field(name="Status", value="⏳ Aguardando aprovação", inline=False)
                    
                    await button_interaction.followup.send(embed=embed, ephemeral=True)
                    
                    # DM de confirmação para o usuário que fez a indicação
                    try:
                        dm_embed = discord.Embed(
                            title="✅ Sua Indicação foi Registrada!",
                            description=f"Indicador: {referrer_mention}\n\nAguarde a aprovação da administração para receber seus pontos!",
                            color=discord.Color.green()
                        )
                        dm_embed.add_field(name="Código Usado", value=f"`{code_value}`", inline=False)
                        dm_embed.add_field(name="Pontos Pendentes", value=f"+{REFERRAL_POINTS_REFERRED} pontos", inline=True)
                        dm_embed.add_field(name="Status", value="⏳ Aguardando aprovação", inline=True)
                        dm_embed.set_footer(text="Você receberá outro aviso quando for aprovado!")
                        await member.send(embed=dm_embed)
                    except Exception as e:
                        print(f"[Referrals] ⚠️ Erro ao enviar DM de confirmação: {e}")
                    
                    # DM para o indicador informando a nova indicação
                    try:
                        referrer_dm_embed = discord.Embed(
                            title="🎉 Nova Indicação Recebida!",
                            description=f"{member.mention} foi indicado pelo seu código `{code_value}`!",
                            color=discord.Color.gold()
                        )
                        referrer_dm_embed.add_field(name="Indicado", value=member.name, inline=True)
                        referrer_dm_embed.add_field(name="Steam", value=self_modal.steam_link, inline=False)
                        referrer_dm_embed.add_field(name="Pontos Ganhos", value=f"+{REFERRAL_POINTS_REFERRER} (após aprovação)", inline=True)
                        referrer_dm_embed.set_footer(text="Aguarde a aprovação do admin para confirmar!")
                        
                        if referrer:
                            await referrer.send(embed=referrer_dm_embed)
                    except Exception as e:
                        print(f"[Referrals] ⚠️ Erro ao enviar DM para indicador: {e}")
                    
                    # Log
                    try:
                        log_channel = interaction.client.get_channel(REFERRALS_LOGS_CHANNEL_ID)
                        if log_channel and isinstance(log_channel, discord.TextChannel):
                            referrer_mention_log = f"<@{referrer_id}>"
                            log_embed = discord.Embed(
                                title="📋 Nova Indicação Recebida",
                                description=f"**Indicador:** {referrer_mention_log}\n**Indicado:** {member.mention}",
                                color=discord.Color.blue()
                            )
                            log_embed.add_field(name="Código", value=f"`{code_value}`", inline=True)
                            log_embed.add_field(name="Steam", value=str(self_modal.steam_link), inline=False)
                            log_embed.add_field(name="Info Extra", value=str(self_modal.extra_info) or "Nenhuma", inline=False)
                            await log_channel.send(embed=log_embed)
                    except Exception as e:
                        print(f"[Referrals] ⚠️ Erro ao enviar log: {e}")
                
                except Exception as e:
                    print(f"[Referrals] ❌ Erro ao salvar indicação: {e}")
                    await button_interaction.followup.send("❌ Erro ao processar indicação!", ephemeral=True)
            
            @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
            async def cancel_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.defer(thinking=True)
                embed = discord.Embed(
                    title="❌ Indicação Cancelada",
                    description="Sua indicação foi cancelada. Pode tentar novamente quando desejar.",
                    color=discord.Color.red()
                )
                await button_interaction.followup.send(embed=embed, ephemeral=True)
        
        # Aliás para usar na view
        self_modal = self
        
        # Mostra confirmação
        embed = discord.Embed(
            title="👤 Confirme os Dados da Indicação",
            description=f"Revise as informações antes de confirmar:",
            color=discord.Color.gold()
        )
        # Nome do indicador com mention clicável e link para o perfil
        referrer_mention = f"<@{referrer_id}> • [Perfil](https://discord.com/users/{referrer_id})"
        embed.add_field(
            name="✅ Quem te Indicou",
            value=referrer_mention,
            inline=False
        )
        embed.add_field(
            name="🎮 Seu Steam",
            value=f"[Abrir Perfil]({str(self.steam_link)})",
            inline=False
        )
        if str(self.extra_info):
            embed.add_field(
                name="ℹ️ Informações Adicionais",
                value=str(self.extra_info),
                inline=False
            )
        embed.add_field(
            name="💰 Recompensa",
            value=f"**+{REFERRAL_POINTS_REFERRED} pontos** (após aprovação)",
            inline=False
        )
        embed.set_footer(text="Confirme apenas se os dados estão corretos!")
        
        await interaction.followup.send(embed=embed, view=ConfirmReferralView(), ephemeral=True)

class SubmitReferralButton(discord.ui.View):
    """View com botão para enviar indicação."""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📝 Enviar Indicação", style=discord.ButtonStyle.success, custom_id="btn_submit_referral")
    async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SubmitReferralModal())

class PointsButton(discord.ui.View):
    """View com botão para ver pontos."""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="💰 Meus Pontos", style=discord.ButtonStyle.success, custom_id="btn_my_points")
    async def points_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        
        user_id = interaction.user.id
        
        referrer_stats = get_referrer_stats(user_id)
        referred_stats = get_referred_stats(user_id)
        
        embed = discord.Embed(
            title="💰 Meus Pontos de Indicação",
            color=discord.Color.gold()
        )
        
        if referrer_stats:
            embed.add_field(
                name="🎯 Como Indicador",
                value=f"**Código:** `{referrer_stats['code']}`\n"
                      f"**Indicações:** {referrer_stats['referrals_count']}\n"
                      f"**Pontos Pendentes:** {referrer_stats['pending_points']}\n"
                      f"**Pontos Aprovados:** {referrer_stats['approved_points']}",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Como Indicador",
                value="Você ainda não tem código. Clique em **🎫 Gerar Meu Código**!",
                inline=False
            )
        
        # Busca quem indicou o usuário (máximo 1)
        data = load_referral_data()
        my_referrer = None
        for ref in data.get("referrals", []):
            if ref.get("referred_id") == user_id or ref.get("referred_discord_id") == user_id:
                my_referrer = ref
                break
        
        if my_referrer:
            referrer_name = my_referrer.get("referrer_name", "Desconhecido")
            referrer_id = my_referrer.get("referrer_id")
            status_emoji = "⏳" if my_referrer.get("status") == "pending" else "✅" if my_referrer.get("status") == "approved" else "❌"
            
            if referrer_id:
                referrer_mention = f"<@{referrer_id}>"
            else:
                referrer_mention = referrer_name
            
            embed.add_field(
                name="🎯 Meu Indicador",
                value=f"{status_emoji} {referrer_mention}",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Meu Indicador",
                value="Nenhum indicador registrado",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class MyReferralsView(discord.ui.View):
    """View com botão para ver histórico pessoal de indicações."""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📊 Minhas Indicações", style=discord.ButtonStyle.blurple, custom_id="btn_my_referrals")
    async def my_referrals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        
        user_id = interaction.user.id
        data = load_referral_data()
        
        # Busca indicações que o usuário FEZ (como indicador)
        made_referrals = [
            r for r in data.get("referrals", [])
            if r.get("referrer_id") == user_id or r.get("referrer_discord_id") == user_id
        ]
        
        # Busca indicações que o usuário RECEBEU (como indicado)
        received_referrals = [
            r for r in data.get("referrals", [])
            if r.get("referred_id") == user_id or r.get("referred_discord_id") == user_id
        ]
        
        # Separar por status
        made_pending = [r for r in made_referrals if r.get("status") == "pending"]
        made_approved = [r for r in made_referrals if r.get("status") == "approved"]
        made_rejected = [r for r in made_referrals if r.get("status") == "rejected"]
        
        received_pending = [r for r in received_referrals if r.get("status") == "pending"]
        received_approved = [r for r in received_referrals if r.get("status") == "approved"]
        received_rejected = [r for r in received_referrals if r.get("status") == "rejected"]
        
        # Cria embed com histórico
        embed = discord.Embed(
            title="📊 Meu Histórico de Indicações",
            color=discord.Color.blurple()
        )
        
        # --- INDICAÇÕES QUE EU FIZ ---
        if made_referrals:
            made_text = ""
            if made_pending:
                made_text += f"**⏳ Pendentes:** {len(made_pending)}\n"
                for r in made_pending[:3]:
                    referred = r.get('referred_name', 'Desconhecido')
                    made_text += f"  • {referred}\n"
                if len(made_pending) > 3:
                    made_text += f"  • +{len(made_pending) - 3} mais...\n"
            
            if made_approved:
                made_text += f"**✅ Aprovadas:** {len(made_approved)}\n"
                for r in made_approved[:3]:
                    referred = r.get('referred_name', 'Desconhecido')
                    made_text += f"  • {referred}\n"
                if len(made_approved) > 3:
                    made_text += f"  • +{len(made_approved) - 3} mais...\n"
            
            if made_rejected:
                made_text += f"**❌ Rejeitadas:** {len(made_rejected)}\n"
                for r in made_rejected[:2]:
                    referred = r.get('referred_name', 'Desconhecido')
                    made_text += f"  • {referred}\n"
                if len(made_rejected) > 2:
                    made_text += f"  • +{len(made_rejected) - 2} mais...\n"
            
            embed.add_field(
                name="🎯 Indicações que EU FIZ",
                value=made_text.strip() or "Nenhuma indicação realizada",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Indicações que EU FIZ",
                value="Você ainda não fez nenhuma indicação.",
                inline=False
            )
        
        # --- MEU INDICADOR ---
        # Busca se o usuário foi indicado (máximo 1 indicação)
        my_referrer = None
        for ref in received_referrals:
            my_referrer = ref
            break
        
        if my_referrer:
            referrer_name = my_referrer.get("referrer_name", "Desconhecido")
            referrer_id = my_referrer.get("referrer_id")
            status_emoji = "⏳" if my_referrer.get("status") == "pending" else "✅" if my_referrer.get("status") == "approved" else "❌"
            
            if referrer_id:
                referrer_mention = f"<@{referrer_id}>"
            else:
                referrer_mention = referrer_name
            
            embed.add_field(
                name="🎯 Meu Indicador",
                value=f"{status_emoji} {referrer_mention}",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Meu Indicador",
                value="Nenhum indicador registrado",
                inline=False
            )
        
        # Resumo de pontos
        referrer_stats = get_referrer_stats(user_id)
        referred_stats = get_referred_stats(user_id)
        
        points_text = ""
        if referrer_stats:
            points_text += f"**Como Indicador:**\n"
            points_text += f"  ⏳ Pendentes: {referrer_stats['pending_points']}\n"
            points_text += f"  ✅ Aprovados: {referrer_stats['approved_points']}\n\n"
        
        if referred_stats and (referred_stats['pending_points'] > 0 or referred_stats['approved_points'] > 0):
            points_text += f"**Como Indicado:**\n"
            points_text += f"  ⏳ Pendentes: {referred_stats['pending_points']}\n"
            points_text += f"  ✅ Aprovados: {referred_stats['approved_points']}\n"
        
        if points_text:
            embed.add_field(
                name="💰 Meus Pontos",
                value=points_text.strip(),
                inline=False
            )
        
        embed.set_footer(text="Sua visualização privada - Apenas você vê isso")
        await interaction.followup.send(embed=embed, ephemeral=True)

class ApprovedReferralsView(discord.ui.View):
    """View combinada para o painel de Aprovadas com ambos os botões."""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="💰 Meus Pontos", style=discord.ButtonStyle.success, custom_id="btn_my_points")
    async def points_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        
        user_id = interaction.user.id
        
        referrer_stats = get_referrer_stats(user_id)
        referred_stats = get_referred_stats(user_id)
        
        embed = discord.Embed(
            title="💰 Meus Pontos de Indicação",
            color=discord.Color.gold()
        )
        
        if referrer_stats:
            embed.add_field(
                name="🎯 Como Indicador",
                value=f"**Código:** `{referrer_stats['code']}`\n"
                      f"**Indicações:** {referrer_stats['referrals_count']}\n"
                      f"**Pontos Pendentes:** {referrer_stats['pending_points']}\n"
                      f"**Pontos Aprovados:** {referrer_stats['approved_points']}",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Como Indicador",
                value="Você ainda não tem código. Clique em **🎫 Gerar Meu Código**!",
                inline=False
            )
        
        if referred_stats and (referred_stats['pending_points'] > 0 or referred_stats['approved_points'] > 0):
            embed.add_field(
                name="👥 Como Indicado",
                value=f"**Pontos Pendentes:** {referred_stats['pending_points']}\n"
                      f"**Pontos Aprovados:** {referred_stats['approved_points']}",
                inline=False
            )
        else:
            embed.add_field(
                name="👥 Como Indicado",
                value="Você ainda não foi indicado",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📊 Minhas Indicações", style=discord.ButtonStyle.blurple, custom_id="btn_my_referrals_2")
    async def my_referrals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        
        user_id = interaction.user.id
        data = load_referral_data()
        
        # Busca indicações que o usuário FEZ (como indicador)
        made_referrals = [
            r for r in data.get("referrals", [])
            if r.get("referrer_id") == user_id or r.get("referrer_discord_id") == user_id
        ]
        
        # Busca indicações que o usuário RECEBEU (como indicado)
        received_referrals = [
            r for r in data.get("referrals", [])
            if r.get("referred_id") == user_id or r.get("referred_discord_id") == user_id
        ]
        
        # Separar por status
        made_pending = [r for r in made_referrals if r.get("status") == "pending"]
        made_approved = [r for r in made_referrals if r.get("status") == "approved"]
        made_rejected = [r for r in made_referrals if r.get("status") == "rejected"]
        
        received_pending = [r for r in received_referrals if r.get("status") == "pending"]
        received_approved = [r for r in received_referrals if r.get("status") == "approved"]
        received_rejected = [r for r in received_referrals if r.get("status") == "rejected"]
        
        # Cria embed com histórico
        embed = discord.Embed(
            title="📊 Meu Histórico de Indicações",
            color=discord.Color.blurple()
        )
        
        # --- INDICAÇÕES QUE EU FIZ ---
        if made_referrals:
            made_text = ""
            if made_pending:
                made_text += f"**⏳ Pendentes:** {len(made_pending)}\n"
                for r in made_pending[:3]:
                    referred = r.get('referred_name', 'Desconhecido')
                    made_text += f"  • {referred}\n"
                if len(made_pending) > 3:
                    made_text += f"  • +{len(made_pending) - 3} mais...\n"
            
            if made_approved:
                made_text += f"**✅ Aprovadas:** {len(made_approved)}\n"
                for r in made_approved[:3]:
                    referred = r.get('referred_name', 'Desconhecido')
                    made_text += f"  • {referred}\n"
                if len(made_approved) > 3:
                    made_text += f"  • +{len(made_approved) - 3} mais...\n"
            
            if made_rejected:
                made_text += f"**❌ Rejeitadas:** {len(made_rejected)}\n"
                for r in made_rejected[:2]:
                    referred = r.get('referred_name', 'Desconhecido')
                    made_text += f"  • {referred}\n"
                if len(made_rejected) > 2:
                    made_text += f"  • +{len(made_rejected) - 2} mais...\n"
            
            embed.add_field(
                name="🎯 Indicações que EU FIZ",
                value=made_text.strip() or "Nenhuma indicação realizada",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Indicações que EU FIZ",
                value="Você ainda não fez nenhuma indicação.",
                inline=False
            )
        
        # --- INDICAÇÕES QUE EU RECEBI ---
        if received_referrals:
            received_text = ""
            if received_pending:
                received_text += f"**⏳ Pendentes:** {len(received_pending)}\n"
                for r in received_pending[:3]:
                    referrer = r.get('referrer_name', 'Desconhecido')
                    received_text += f"  • {referrer}\n"
                if len(received_pending) > 3:
                    received_text += f"  • +{len(received_pending) - 3} mais...\n"
            
            if received_approved:
                received_text += f"**✅ Aprovadas:** {len(received_approved)}\n"
                for r in received_approved[:3]:
                    referrer = r.get('referrer_name', 'Desconhecido')
                    received_text += f"  • {referrer}\n"
                if len(received_approved) > 3:
                    received_text += f"  • +{len(received_approved) - 3} mais...\n"
            
            if received_rejected:
                received_text += f"**❌ Rejeitadas:** {len(received_rejected)}\n"
                for r in received_rejected[:2]:
                    referrer = r.get('referrer_name', 'Desconhecido')
                    received_text += f"  • {referrer}\n"
                if len(received_rejected) > 2:
                    received_text += f"  • +{len(received_rejected) - 2} mais...\n"
            
            embed.add_field(
                name="👥 Indicações que EU RECEBI",
                value=received_text.strip() or "Você ainda não recebeu indicações",
                inline=False
            )
        else:
            embed.add_field(
                name="👥 Indicações que EU RECEBI",
                value="Você ainda não recebeu nenhuma indicação.",
                inline=False
            )
        
        # Resumo de pontos
        referrer_stats = get_referrer_stats(user_id)
        referred_stats = get_referred_stats(user_id)
        
        points_text = ""
        if referrer_stats:
            points_text += f"**Como Indicador:**\n"
            points_text += f"  ⏳ Pendentes: {referrer_stats['pending_points']}\n"
            points_text += f"  ✅ Aprovados: {referrer_stats['approved_points']}\n\n"
        
        if referred_stats and (referred_stats['pending_points'] > 0 or referred_stats['approved_points'] > 0):
            points_text += f"**Como Indicado:**\n"
            points_text += f"  ⏳ Pendentes: {referred_stats['pending_points']}\n"
            points_text += f"  ✅ Aprovados: {referred_stats['approved_points']}\n"
        
        if points_text:
            embed.add_field(
                name="💰 Meus Pontos",
                value=points_text.strip(),
                inline=False
            )
        
        embed.set_footer(text="Sua visualização privada - Apenas você vê isso")
        await interaction.followup.send(embed=embed, ephemeral=True)

class PendingReferralsView(discord.ui.View):
    """View para gerenciar indicações pendentes."""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="👨‍💼 Gerenciar Indicações", style=discord.ButtonStyle.success, custom_id="btn_manage_pending")
    async def manage_pending_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verifica se é admin/mod
        user = interaction.user
        if not isinstance(user, discord.Member):
            await interaction.response.send_message("❌ Comando disponível apenas no servidor!", ephemeral=True)
            return
        
        if not user.guild_permissions.administrator and not any(role.name == "MOD" for role in user.roles):
            await interaction.response.send_message("❌ Apenas admins e mods podem usar isso!", ephemeral=True)
            return
        
        data = load_referral_data()
        pending_list = [r for r in data.get("referrals", []) if r.get("status") == "pending"]
        
        if not pending_list:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="📭 Nenhuma Indicação Pendente",
                    description="Todos os pendentes já foram aprovados ou rejeitados!",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            return
        
        # Cria um modal para seleção
        class SelectIndicacaoModal(discord.ui.Modal, title="Selecionar Indicação"):
            def __init__(self, pending_list_modal, data_modal):
                super().__init__()
                self.pending_list = pending_list_modal
                self.data_obj = data_modal
                
                # Cria opções numeradas para o campo
                options_text = "\n".join([
                    f"{i+1}. {r.get('referred_name', 'Desconhecido')} (por: {r.get('referrer_name', 'Desconhecido')}) - código: {r.get('code', 'N/A')}"
                    for i, r in enumerate(pending_list_modal[:25])
                ])
                
                self.numero_indicacao = discord.ui.TextInput(
                    label="Número da Indicação",
                    placeholder="Digite o número (ex: 1, 2, 3...)",
                    required=True,
                    max_length=3,
                    min_length=1
                )
                self.add_item(self.numero_indicacao)
            
            async def on_submit(self, interaction: discord.Interaction):
                try:
                    idx = int(self.numero_indicacao.value) - 1
                    
                    if idx < 0 or idx >= len(self.pending_list):
                        await interaction.response.send_message(
                            "❌ Número inválido! Digite um número entre 1 e " + str(len(self.pending_list)),
                            ephemeral=True
                        )
                        return
                    
                    referral = self.pending_list[idx]
                    
                    # Compatibilidade com estrutura antiga + nova
                    referred_name = referral.get('referred_name', 'Desconhecido')
                    referrer_name = referral.get('referrer_name', 'Desconhecido')
                    code = referral.get('code', referral.get('referrer_code', 'N/A'))
                    steam = referral.get('steam_link', referral.get('referred_steam_url', 'N/A'))
                    extra_info = referral.get('extra_info', referral.get('additional_info', 'Nenhuma'))
                    created_at = referral.get('created_at', 'N/A')
                    
                    # Fallback: se não tem referrer_name, tenta buscar do banco pelo código
                    if referrer_name == 'Desconhecido' and code != 'N/A':
                        code_info = self.data_obj.get('referral_codes', {}).get(code, {})
                        referrer_name = code_info.get('username', 'Desconhecido')
                    
                    # Mostra as informações da indicação
                    created_datetime = datetime.fromisoformat(created_at) if created_at != 'N/A' else None
                    time_ago = ""
                    if created_datetime:
                        time_diff = datetime.now() - created_datetime
                        days = time_diff.days
                        hours = time_diff.seconds // 3600
                        if days > 0:
                            time_ago = f" ({days}d atrás)"
                        elif hours > 0:
                            time_ago = f" ({hours}h atrás)"
                        else:
                            time_ago = " (há pouco)"
                    
                    embed = discord.Embed(
                        title="📋 Indicação Selecionada",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="👤 Indicado", value=referred_name, inline=True)
                    embed.add_field(name="🎯 Indicador", value=referrer_name, inline=True)
                    embed.add_field(name="🔖 Código", value=f"`{code}`", inline=True)
                    embed.add_field(name="🎮 Steam", value=f"[Link]({steam})" if steam and steam != "N/A" else steam, inline=False)
                    embed.add_field(name="📝 Info Extra", value=str(extra_info) or "Nenhuma informação", inline=False)
                    
                    # Informações de tempo
                    if created_at and created_at != 'N/A':
                        embed.add_field(
                            name="⏰ Data da Indicação",
                            value=f"{str(created_at)[:10]}{time_ago}",
                            inline=True
                        )
                    
                    # Pontos que serão desbloqueados
                    embed.add_field(
                        name="💰 Recompensa ao Aprovar",
                        value=f"Indicador: +{REFERRAL_POINTS_REFERRER} pontos\nIndicado: +{REFERRAL_POINTS_REFERRED} pontos",
                        inline=True
                    )
                    embed.set_footer(text="Use os botões abaixo para gerenciar esta indicação")
                    
                    # View com botões de Aprovar/Rejeitar
                    class ApprovalButtons(discord.ui.View):
                        def __init__(self, ref_data, data_obj, select_int):
                            super().__init__(timeout=300)
                            self.referral_data = ref_data
                            self.data_obj = data_obj
                            self.select_int = select_int
                        
                        @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success)
                        async def approve_button(self, button_interaction: discord.Interaction, btn: discord.ui.Button):
                            try:
                                await button_interaction.response.defer(thinking=True)
                                
                                # Atualiza status
                                self.referral_data['status'] = 'approved'
                                self.referral_data['approved_at'] = datetime.now().isoformat()
                                
                                # Salva
                                save_referral_data(self.data_obj)
                                
                                # Atualiza contador de indicações pendentes no nome do canal
                                await update_pending_counter(button_interaction.client)
                                
                                # Log com fallback para dados antigos
                                referrer_name = self.referral_data.get('referrer_name', 'Desconhecido')
                                referred_name = self.referral_data.get('referred_name', 'Desconhecido')
                                log_embed = discord.Embed(
                                    title="✅ Indicação Aprovada",
                                    description=f"Indicado: {referred_name}\nIndicador: {referrer_name}",
                                    color=discord.Color.green()
                                )
                                log_channel = self.select_int.client.get_channel(REFERRALS_LOGS_CHANNEL_ID)
                                if log_channel and isinstance(log_channel, discord.TextChannel):
                                    await log_channel.send(embed=log_embed)
                                
                                await button_interaction.followup.send("✅ Indicação aprovada!", ephemeral=True)
                            except Exception as e:
                                print(f"[Referrals] Erro ao aprovar: {e}")
                                try:
                                    await button_interaction.followup.send(f"❌ Erro: {str(e)[:100]}", ephemeral=True)
                                except:
                                    pass
                        
                        @discord.ui.button(label="❌ Rejeitar", style=discord.ButtonStyle.danger)
                        async def reject_button(self, button_interaction: discord.Interaction, btn: discord.ui.Button):
                            try:
                                await button_interaction.response.defer(thinking=True)
                                
                                # Atualiza status
                                self.referral_data['status'] = 'rejected'
                                
                                # Salva
                                save_referral_data(self.data_obj)
                                
                                # Atualiza contador de indicações pendentes no nome do canal
                                await update_pending_counter(button_interaction.client)
                                
                                # Log com fallback para dados antigos
                                referrer_name = self.referral_data.get('referrer_name', 'Desconhecido')
                                referred_name = self.referral_data.get('referred_name', 'Desconhecido')
                                log_embed = discord.Embed(
                                    title="❌ Indicação Rejeitada",
                                    description=f"Indicado: {referred_name}\nIndicador: {referrer_name}",
                                    color=discord.Color.red()
                                )
                                log_channel = self.select_int.client.get_channel(REFERRALS_LOGS_CHANNEL_ID)
                                if log_channel and isinstance(log_channel, discord.TextChannel):
                                    await log_channel.send(embed=log_embed)
                                
                                await button_interaction.followup.send("❌ Indicação rejeitada!", ephemeral=True)
                            except Exception as e:
                                print(f"[Referrals] Erro ao rejeitar: {e}")
                                try:
                                    await button_interaction.followup.send(f"❌ Erro: {str(e)[:100]}", ephemeral=True)
                                except:
                                    pass
                        
                        @discord.ui.button(label="🗑️ Deletar", style=discord.ButtonStyle.secondary)
                        async def delete_button(self, button_interaction: discord.Interaction, btn: discord.ui.Button):
                            try:
                                await button_interaction.response.defer(thinking=True)
                                
                                # Remove a indicação completamente do JSON
                                if self.referral_data in self.data_obj['referrals']:
                                    self.data_obj['referrals'].remove(self.referral_data)
                                    save_referral_data(self.data_obj)
                                    
                                    # Atualiza contador de indicações pendentes no nome do canal
                                    await update_pending_counter(button_interaction.client)
                                    
                                    # Log com fallback para dados antigos
                                    referrer_name = self.referral_data.get('referrer_name', 'Desconhecido')
                                    referred_name = self.referral_data.get('referred_name', 'Desconhecido')
                                    log_embed = discord.Embed(
                                        title="🗑️ Indicação Deletada",
                                        description=f"Indicado: {referred_name}\nIndicador: {referrer_name}\n\n**Motivo:** Remoção manual (quebrada/inválida)",
                                        color=discord.Color.greyple()
                                    )
                                    log_channel = self.select_int.client.get_channel(REFERRALS_LOGS_CHANNEL_ID)
                                    if log_channel and isinstance(log_channel, discord.TextChannel):
                                        await log_channel.send(embed=log_embed)
                                    
                                    await button_interaction.followup.send("🗑️ Indicação deletada permanentemente!", ephemeral=True)
                                else:
                                    await button_interaction.followup.send("⚠️ Erro ao deletar indicação!", ephemeral=True)
                            except Exception as e:
                                print(f"[Referrals] ❌ Erro ao deletar: {e}")
                                try:
                                    await button_interaction.followup.send(f"❌ Erro: {str(e)[:100]}", ephemeral=True)
                                except:
                                    pass
                    
                    await interaction.response.send_message(embed=embed, view=ApprovalButtons(referral, self.data_obj, interaction), ephemeral=True)
                
                except ValueError:
                    await interaction.response.send_message("❌ Digite um número válido!", ephemeral=True)
                except Exception as e:
                    print(f"[Referrals] ❌ Erro no modal: {e}")
                    await interaction.response.send_message(f"❌ Erro: {str(e)[:100]}", ephemeral=True)
        
        await interaction.response.send_modal(SelectIndicacaoModal(pending_list, data))


async def update_pending_counter(bot):
    """Atualiza o nome do canal de pendentes com o contador de indicações."""
    try:
        pending_channel = bot.get_channel(REFERRALS_PENDING_CHANNEL_ID)
        if not pending_channel or not isinstance(pending_channel, discord.TextChannel):
            return
        
        # Conta indicações pendentes
        data = load_referral_data()
        pending_count = len([r for r in data.get("referrals", []) if r.get("status") == "pending"])
        
        # Atualiza o nome do canal
        new_name = f"📋-pendentes-{pending_count}"
        if pending_channel.name != new_name:
            await pending_channel.edit(name=new_name)
            print(f"[Referrals] ✅ Contador de pendentes atualizado: {pending_count}")
    except Exception as e:
        print(f"[Referrals] ⚠️ Erro ao atualizar contador de pendentes: {e}")


class Referrals(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.panels_created = False
        
        # Cria pasta de banco de dados se não existir
        bancos_dir = os.path.dirname(REFERRALS_FILE) or "."
        os.makedirs(bancos_dir, exist_ok=True)
        print(f"[Referrals] 📁 Pasta de banco de dados garantida: {bancos_dir}")
        
        # Carrega e valida dados ao iniciar
        print("\n[Referrals] 🔍 Validando dados persistidos...")
        self._validate_referral_data()
        
        print("[Referrals] ✅ COG REFERRALS INICIALIZADA!")
        # Inicia task para criar painéis quando bot estiver pronto
        self.bot.loop.create_task(self._setup_panels())
        # Inicia task para atualizar ranking periodicamente
        self.bot.loop.create_task(self._update_ranking_loop())
    
    def _validate_referral_data(self):
        """Valida integridade dos dados de referrals ao startup."""
        try:
            data = load_referral_data()
            
            # Conta estatísticas
            num_codes = len(data.get("referral_codes", {}))
            num_referrals = len(data.get("referrals", []))
            
            print(f"[Referrals] 📊 Estatísticas:")
            print(f"           • Códigos de indicação: {num_codes}")
            print(f"           • Indicações registradas: {num_referrals}")
            
            # Valida consistency de used_ids
            codes_set = set(data.get("referral_codes", {}).keys())
            used_ids = set(data.get("used_ids", []))
            
            if codes_set != used_ids:
                print(f"[Referrals] ⚠️ INCONSISTÊNCIA DETECTADA: Reparando...")
                data["used_ids"] = list(codes_set)
                save_referral_data(data)
                print(f"[Referrals] ✅ Dados reparados!")
            
            print("[Referrals] ✅ Validação concluída com sucesso!\n")
            
        except Exception as e:
            print(f"[Referrals] ❌ Erro ao validar dados: {e}")
            traceback.print_exc()
    
    async def _setup_panels(self):
        """Aguarda bot ficar pronto e cria painéis."""
        print("[Referrals] ⏳ Aguardando bot ficar pronto...")
        await self.bot.wait_until_ready()
        print("[Referrals] 🔍 Bot está pronto! Iniciando criação de painéis...")
        
        await asyncio.sleep(3)  # Aguarda mais um pouco para garantir disponibilidade
        
        # Atualiza o contador de indicações pendentes
        await update_pending_counter(self.bot)
        
        if not self.panels_created:
            self.panels_created = True
            await self._create_all_panels()
        
        # 🔄 Atualiza o ranking quando o bot inicia
        print("[Referrals] 📊 Limpando e reenviando ranking...")
        await asyncio.sleep(2)
        await self._update_ranking()
    
    async def _create_all_panels(self):
        """Cria todos os painéis de indicação."""
        print(f"\n🔄 [REFERRALS] Iniciando limpeza e recriação de painéis...\n")
        
        try:
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                print(f"[Referrals] ❌ Guild {GUILD_ID} não encontrada!")
                return
            
            print(f"[Referrals] ✅ Guild encontrada: {guild.name}\n")
            
            # Lista de canais e suas configurações
            pain_config = [
                (REFERRALS_GENERATE_ID_CHANNEL_ID, "🎫 Gerador de ID", GenerateCodeButton()),
                (REFERRALS_FORM_CHANNEL_ID, "📝 Formulário", SubmitReferralButton()),
                (REFERRALS_PENDING_CHANNEL_ID, "⏳ Pendentes", PendingReferralsView()),
                (REFERRALS_APPROVED_CHANNEL_ID, "✅ Aprovadas", ApprovedReferralsView()),
            ]
            
            for channel_id, canal_type, view in pain_config:
                await self._clean_and_recreate_panel(channel_id, canal_type, view)
            
            print("\n[Referrals] ✅ Limpeza e recriação de painéis concluída!\n")
        
        except Exception as e:
            print(f"[Referrals] ❌ Erro ao criar painéis: {e}")
            traceback.print_exc()
    
    async def _clean_and_recreate_panel(self, channel_id: int, canal_type: str, view: Optional[discord.ui.View]):
        """Limpa canal e recria painel."""
        if channel_id == 0:
            print(f"[Referrals] ⚠️ Canal ID é 0 para {canal_type}! Verificar .env")
            return
        
        try:
            channel = self.bot.get_channel(channel_id)
            
            if not channel:
                print(f"[Referrals] ⚠️ Canal {channel_id} não encontrado para '{canal_type}'")
                return
            
            # Valida se é TextChannel
            if not isinstance(channel, discord.TextChannel):
                print(f"[Referrals] ⚠️ Canal {channel_id} não é um TextChannel!")
                return
            
            # Limpa canal deletando todas as mensagens com retry
            try:
                max_purge_retries = 3
                for attempt in range(max_purge_retries):
                    try:
                        await channel.purge(limit=None)
                        print(f"✅ [REINICIO] Canal de {canal_type} ({channel_id}) limpado")
                        break
                    except discord.errors.HTTPException as e:
                        if e.status == 503 and attempt < max_purge_retries - 1:
                            print(f"⚠️ [REINICIO] Erro 503 ao limpar {canal_type}, tentando novamente...")
                            await asyncio.sleep(2)
                        else:
                            raise
            except Exception as e:
                print(f"⚠️ [REINICIO] Erro ao limpar canal de {canal_type}: {e}")
            
            # Define o conteúdo do painel
            if canal_type == "🎫 Gerador de ID":
                title = "🎫 Gerador de ID de Indicação"
                description = (
                    f"Clique no botão abaixo para gerar seu código único!\n\n"
                    f"**Como funciona?**\n"
                    f"1. Clique em **🎫 Gerar Meu Código**\n"
                    f"2. Receba um código único (A1234)\n"
                    f"3. Compartilhe com amigos\n"
                    f"4. Cada indicação = **{REFERRAL_POINTS_REFERRER} pontos**\n\n"
                    f"💡 Dica: Use o botão **💰 Meus Pontos** para acompanhar seus ganhos!"
                )
                color = discord.Color.blue()
            
            elif canal_type == "📝 Formulário":
                title = "📝 Formulário de Indicação"
                description = (
                    f"Você foi indicado? Preencha o formulário!\n\n"
                    f"Clique no botão abaixo para enviar sua indicação.\n\n"
                    f"**Você vai precisar de:**\n"
                    f"✅ Nome de quem te indicou\n"
                    f"✅ Código de indicação (A1234)\n"
                    f"✅ Link do seu perfil Steam\n"
                    f"⭕ Informações complementares (opcional)\n\n"
                    f"**Após enviar:**\n"
                    f"1. Você recebe **{REFERRAL_POINTS_REFERRED} pontos**\n"
                    f"2. Admin verifica e aprova\n"
                    f"3. Você recebe confirmação via DM\n\n"
                    f"✨ Verifique seus pontos clicando em **💰 Meus Pontos**"
                )
                color = discord.Color.gold()
            
            elif canal_type == "⏳ Pendentes":
                title = "⏳ Indicações Pendentes"
                description = (
                    f"As indicações aparecem aqui enquanto aguardam aprovação da administração.\n\n"
                    f"📊 **Status da Indicação:**\n"
                    f"• ⏳ Estado: Aguardando verificação\n"
                    f"• 💰 Pontos: Bloqueados até aprovação\n"
                    f"• 🔔 Você será notificado via DM quando aprovada\n\n"
                    f"🔧 **Para Admins:**\n"
                    f"Clique em **👨‍💼 Gerenciar Indicações** para revisar e aprovar!\n\n"
                    f"ℹ️ *As indicações podem levar até 24h para serem avaliadas*"
                )
                color = discord.Color.orange()
            
            elif canal_type == "✅ Aprovadas":
                title = "✅ Indicações Aprovadas"
                description = (
                    f"As indicações aprovadas aparecem aqui!\n\n"
                    f"**Status:** Pagamento realizado ✓\n"
                    f"**Pontos:** Já foram creditados\n\n"
                    f"Parabéns pela indicação! 🎉\n\n"
                    f"Use **💰 Meus Pontos** para ver seus ganhos!"
                )
                color = discord.Color.green()
            
            # Cria painel
            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )
            embed.set_footer(text="Sistema de Indicação • Atualizado automaticamente")
            
            # Cria painel com retry para erros 503
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if view:
                        await channel.send(embed=embed, view=view)
                    else:
                        await channel.send(embed=embed)
                    
                    print(f"✅ [REINICIO] Painel de {canal_type} recriado com sucesso!")
                    return
                
                except discord.errors.HTTPException as e:
                    if e.status == 503 and attempt < max_retries - 1:
                        print(f"⚠️ [REINICIO] Erro 503 ao criar {canal_type}, tentando novamente em 3s...")
                        await asyncio.sleep(3)
                    else:
                        raise
        
        except Exception as e:
            print(f"[Referrals] ❌ Erro ao processar {canal_type}: {e}")
            traceback.print_exc()
    
    async def _update_ranking_loop(self):
        """Atualiza o ranking de indicadores a cada 5 minutos."""
        await self.bot.wait_until_ready()
        print("[Referrals] 🏆 Tarefa de atualização de ranking iniciada")
        
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(300)  # Atualiza a cada 5 minutos
                await self._update_ranking()
            except Exception as e:
                print(f"[Referrals] ❌ Erro ao atualizar ranking: {e}")
                traceback.print_exc()
    
    async def _update_ranking(self):
        """Ranking unificado gerenciado pelo xp.py — sem-op aqui."""
        pass
    
    # ====================
    # COMANDOS
    # ====================
    
    @commands.command(name="gerar_id_indicacao")
    async def generate_code_old(self, ctx: commands.Context):
        """Comando legado - use os botões nos painéis!"""
        embed = discord.Embed(
            title="🎫 Use os Botões!",
            description="Acesse o canal de **Gerador de ID de Indicação** e clique no botão **🎫 Gerar Meu Código**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="enviar_indicacao")
    async def submit_referral_old(self, ctx: commands.Context):
        """Comando legado - use os botões nos painéis!"""
        embed = discord.Embed(
            title="📝 Use os Botões!",
            description="Acesse o canal de Formulário de Indicação e clique no botão **📝 Enviar Indicação**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="meus_pontos_indicacao")
    async def check_points(self, ctx: commands.Context):
        """Verifica pontos. Use: !meus_pontos_indicacao"""
        user_id = ctx.author.id
        
        referrer_stats = get_referrer_stats(user_id)
        referred_stats = get_referred_stats(user_id)
        
        embed = discord.Embed(
            title="💰 Meus Pontos de Indicação",
            color=discord.Color.gold()
        )
        
        if referrer_stats:
            embed.add_field(
                name="🎯 Como Indicador",
                value=f"**Código:** `{referrer_stats['code']}`\n"
                      f"**Indicações:** {referrer_stats['referrals_count']}\n"
                      f"**Pontos Pendentes:** {referrer_stats['pending_points']}\n"
                      f"**Pontos Aprovados:** {referrer_stats['approved_points']}",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Como Indicador",
                value="Você ainda não tem código. Use `!gerar_id_indicacao`",
                inline=False
            )
        
        if referred_stats:
            embed.add_field(
                name="👥 Como Indicado",
                value=f"**Pontos Pendentes:** {referred_stats['pending_points']}\n"
                      f"**Pontos Aprovados:** {referred_stats['approved_points']}",
                inline=False
            )
        else:
            embed.add_field(
                name="👥 Como Indicado",
                value="Você ainda não foi indicado",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="painel_indicacoes")
    @commands.has_role("MOD")  # Ajuste conforme sua estrutura
    async def admin_panel(self, ctx: commands.Context):
        """Painel admin detalhado. Use: !painel_indicacoes"""
        
        data = load_referral_data()
        
        pending = [r for r in data.get("referrals", []) if r.get("status") == "pending"]
        approved = [r for r in data.get("referrals", []) if r.get("status") == "approved"]
        rejected = [r for r in data.get("referrals", []) if r.get("status") == "rejected"]
        
        # Busca indicações quebradas (sem referrer_name ou com "Desconhecido")
        broken = [
            r for r in pending 
            if r.get('referrer_name') == 'Desconhecido' or not r.get('referrer_name')
        ]
        
        embed = discord.Embed(
            title="👨‍💼 Painel de Indicações - Resumo",
            color=discord.Color.purple()
        )
        
        # Resumo rápido
        embed.add_field(
            name="📊 Status",
            value=f"⏳ Pendentes: **{len(pending)}**\n✅ Aprovadas: **{len(approved)}**\n❌ Rejeitadas: **{len(rejected)}**",
            inline=False
        )
        
        # Indicações quebradas
        if broken:
            broken_list = "\n".join([f"• {r.get('referred_name', 'N/A')} (código: {r.get('code', 'N/A')})" for r in broken[:5]])
            embed.add_field(
                name="⚠️ QUEBRADAS - Precisam ser Deletadas",
                value=broken_list + (f"\n... e +{len(broken)-5} mais" if len(broken) > 5 else ""),
                inline=False
            )
        
        # Pendentes válidas
        valid_pending = [r for r in pending if r.get('referrer_name') and r.get('referrer_name') != 'Desconhecido']
        if valid_pending:
            pending_list = "\n".join([f"• {r.get('referred_name', 'Desconhecido')} (por: {r.get('referrer_name', 'Desconhecido')})" for r in valid_pending[:5]])
            embed.add_field(
                name="⏳ Primeiras 5 Pendentes (válidas)",
                value=pending_list + (f"\n... e +{len(valid_pending)-5} mais" if len(valid_pending) > 5 else ""),
                inline=False
            )
        
        embed.add_field(
            name="🔧 Como Gerenciar",
            value="Acesse o painel **⏳ Indicações Pendentes** e clique em **👨‍💼 Gerenciar Indicações**\n\nLá você pode:\n✅ Aprovar\n❌ Rejeitar\n🗑️ Deletar (para indicações quebradas)",
            inline=False
        )
        
        embed.set_footer(text=f"Total no banco: {len(data['referrals'])} indicações")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="limpar_indicacoes_quebradas")
    @commands.has_role("MOD")
    async def cleanup_broken_referrals(self, ctx: commands.Context):
        """Deleta automaticamente indicações quebradas/inválidas. Use: !limpar_indicacoes_quebradas"""
        
        data = load_referral_data()
        original_count = len(data['referrals'])
        
        # Remove indicações quebradas
        cleaned = [
            r for r in data['referrals']
            if r.get('referrer_name') and r.get('referrer_name') != 'Desconhecido' and
               r.get('referred_name') and r.get('referred_name') != 'Desconhecido'
        ]
        
        broken_count = original_count - len(cleaned)
        
        if broken_count > 0:
            data['referrals'] = cleaned
            save_referral_data(data)
            
            embed = discord.Embed(
                title="🧹 Limpeza Concluída",
                description=f"**{broken_count}** indicações quebradas foram deletadas!\n\nRestante: **{len(cleaned)}** indicações válidas",
                color=discord.Color.green()
            )
            
            # Log
            log_channel = self.bot.get_channel(REFERRALS_LOGS_CHANNEL_ID)
            if log_channel and isinstance(log_channel, discord.TextChannel):
                log_embed = discord.Embed(
                    title="🧹 Limpeza de Indicações Quebradas",
                    description=f"Admin {ctx.author.mention} limpou **{broken_count}** indicações inválidas",
                    color=discord.Color.orange()
                )
                await log_channel.send(embed=log_embed)
        else:
            embed = discord.Embed(
                title="✅ Sem Indicações Quebradas",
                description="Todas as indicações estão válidas! ✨",
                color=discord.Color.green()
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="recriar_paineis_indicacao")
    async def recreate_panels(self, ctx: commands.Context):
        """Recria painéis. Use: !recriar_paineis_indicacao"""
        
        # Verifica permissão
        if not is_admin_or_mod(ctx.author.id):
            await ctx.send("❌ Você não tem permissão!")
            return
        
        self.panels_created = False
        await ctx.send("🔄 Recriando painéis...")
        await self._create_all_panels()
        await ctx.send("✅ Painéis recriados!")
    
    @commands.command(name="atualizar_ranking_indicacoes")
    async def update_ranking_command(self, ctx: commands.Context):
        """Atualiza o ranking de indicadores manualmente. Use: !atualizar_ranking_indicacoes"""
        
        # Verifica permissão
        if not is_admin_or_mod(ctx.author.id):
            await ctx.send("❌ Você não tem permissão!")
            return
        
        await ctx.send("🔄 Atualizando ranking...")
        await self._update_ranking()
        await ctx.send("✅ Ranking atualizado!")
    
    @commands.command(name="distribuir_premios_ranking")
    async def distribute_ranking_prizes(self, ctx: commands.Context):
        """
        Distribui prêmios aos top 3 indicadores do mês.
        Prêmios: 1º = 1000 pontos, 2º = 750 pontos, 3º = 500 pontos
        Use: !distribuir_premios_ranking
        """
        
        # Verifica permissão
        if not is_admin_or_mod(ctx.author.id):
            await ctx.send("❌ Você não tem permissão!")
            return
        
        top_referrers = get_top_referrers(3)
        
        if not top_referrers:
            embed = discord.Embed(
                title="❌ Sem Indicações",
                description="Não há indicações aprovadas para distribuir prêmios!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Cria embed com os prêmios
        embed = discord.Embed(
            title="🎁 DISTRIBUIÇÃO DE PRÊMIOS DO RANKING",
            description=f"Mês: {datetime.now().strftime('%B de %Y')}",
            color=discord.Color.gold()
        )
        
        prizes_to_distribute = []
        medals = ["🥇", "🥈", "🥉"]
        prize_values = [1000, 750, 500]
        
        for idx, (referrer_id, stats) in enumerate(top_referrers):
            medal = medals[idx]
            prize = prize_values[idx]
            name = stats["name"]
            approved_count = stats["approved_count"]
            
            try:
                user = self.bot.get_user(referrer_id)
                mention = user.mention if user else f"@{name}"
            except:
                mention = f"@{name}"
            
            prizes_to_distribute.append({
                "position": idx + 1,
                "referrer_id": referrer_id,
                "referrer_name": name,
                "prize": prize,
                "approved_count": approved_count
            })
            
            embed.add_field(
                name=f"{medal} {idx + 1}º Lugar",
                value=f"{mention}\n📊 {approved_count} indicações\n💰 **+{prize} pontos de prêmio**",
                inline=False
            )
        
        # View com botões de confirmação
        class ConfirmPrizesView(discord.ui.View):
            def __init__(self, prizes_list, bot_instance):
                super().__init__(timeout=300)
                self.prizes_list = prizes_list
                self.bot_instance = bot_instance
            
            @discord.ui.button(label="✅ Confirmar Distribuição", style=discord.ButtonStyle.success)
            async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(thinking=True)
                
                try:
                    # Aqui você pode integrar com um sistema de pontos de loja
                    # Por enquanto, apenas logamos a distribuição
                    
                    log_text = "🎁 **PRÊMIOS DISTRIBUÍDOS:**\n"
                    for prize_info in self.prizes_list:
                        log_text += f"• {prize_info['referrer_name']}: +{prize_info['prize']} pontos (Posição: {prize_info['position']}ª)\n"
                    
                    result_embed = discord.Embed(
                        title="✅ Prêmios Distribuídos com Sucesso!",
                        description=log_text,
                        color=discord.Color.green()
                    )
                    result_embed.set_footer(text=f"Distribuído por: {interaction.user}")
                    result_embed.timestamp = datetime.now()
                    
                    await interaction.followup.send(embed=result_embed)
                    
                    # Log no canal de logs se existir
                    try:
                        log_channel = self.bot_instance.get_channel(REFERRALS_LOGS_CHANNEL_ID)
                        if log_channel and isinstance(log_channel, discord.TextChannel):
                            await log_channel.send(embed=result_embed)
                    except:
                        pass
                    
                except Exception as e:
                    print(f"[Referrals] ❌ Erro ao distribuir prêmios: {e}")
                    await interaction.followup.send(f"❌ Erro: {str(e)[:100]}", ephemeral=True)
            
            @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
            async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer()
                cancel_embed = discord.Embed(
                    title="❌ Distribuição Cancelada",
                    description="A distribuição de prêmios foi cancelada.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=cancel_embed, ephemeral=True)
        
        # Envia embed com botões
        view = ConfirmPrizesView(prizes_to_distribute, self.bot)
        await ctx.send(embed=embed, view=view)


# ====================
# SETUP
# ====================

async def setup(bot: commands.Bot):
    """Carrega a cog."""
    print("[Referrals] 🎯 setup() iniciado")
    await bot.add_cog(Referrals(bot))
    print("[Referrals] ✅ Cog adicionada ao bot!")
