import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import asyncio

# --- CONFIGURAÇÃO ---
# CANAL_PROMO_ID FOI REMOVIDO DAQUI E AGORA É LIDO DO bot.py
SALES_FILE = 'data/game_sales_history.json' 
DATA_FOLDER = 'data'

# Mapeamento de Cores para o Embed (Plataforma -> Cor Hex)
PLATFORM_COLORS = {
    "Steam": discord.Color.from_rgb(27, 40, 56),        # Azul Escuro Steam
    "Nuuvem": discord.Color.from_rgb(117, 191, 68),     # Verde Nuuvem
    "Epic Games": discord.Color.from_rgb(255, 0, 85)    # Rosa/Vermelho Epic
}
# --------------------

class MultiPlatformSales(commands.Cog):
    # ✅ __init__ agora espera o canal_promo_id como argumento
    def __init__(self, bot, canal_promo_id: int):
        self.bot = bot
        self.canal_promo_id = canal_promo_id # ✅ ID recebido e armazenado
        
        # Garante que a pasta 'data' exista e carrega o histórico
        if not os.path.exists(DATA_FOLDER):
            os.makedirs(DATA_FOLDER)
        self.sales_data = self._load_sales_history()
            
        if not self.checar_promocoes.is_running():
            self.checar_promocoes.start() 

    def cog_unload(self):
        self.checar_promocoes.cancel()

    # --- Funções de Persistência ---

    def _load_sales_history(self):
# ... (o resto da classe permanece igual)
# ...
    def _save_sales_history(self, new_data):
        """Salva o histórico de vendas no arquivo JSON."""
        with open(SALES_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=4, ensure_ascii=False)
            
    # --- Lógica de Scraping por Plataforma ---

    def _scrape_steamdb(self):
        """Busca promoções na SteamDB."""
        URL = "https://steamdb.info/sales/"
        headers = {'User-Agent': 'DiscordBot'}
        promos = {}
        
        try:
            # Requer requests
            response = requests.get(URL, headers=headers, timeout=15)
            response.raise_for_status()
            # Requer beautifulsoup4
            soup = BeautifulSoup(response.text, 'html.parser')
            tabela = soup.find('table', {'id': 'sales'})
            if not tabela: return {}

            for linha in tabela.find('tbody').find_all('tr', limit=15):
                colunas = linha.find_all('td')
                if len(colunas) < 8: continue
                
                app_id = colunas[0].text.strip()
                jogo_nome = colunas[2].text.strip()
                
                promos[f"Steam-{app_id}"] = {
                    'nome': jogo_nome,
                    'desconto': colunas[4].text.strip(),
                    'preco_novo': colunas[5].text.strip(),
                    'preco_normal': colunas[6].text.strip(),
                    'link_store': f"https://store.steampowered.com/app/{app_id}/",
                    'data_fim': colunas[7].text.strip(),
                    'imagem': f'https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg',
                    'plataforma': 'Steam'
                }
            return promos
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao raspar SteamDB: {e}")
            return {}

    def _scrape_nuuvem(self):
        """Busca promoções na Nuuvem (Scraping simplificado)."""
        URL = "https://www.nuuvem.com/promo/todos"
        headers = {'User-Agent': 'DiscordBot'}
        promos = {}
        
        try:
            response = requests.get(URL, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            cards = soup.find_all('a', class_='product-card')
            
            for i, card in enumerate(cards):
                if i >= 15: break
                
                nome_tag = card.find('h3', class_='product-card--title')
                preco_promocional_tag = card.find('span', class_='price-tag--display')
                preco_normal_tag = card.find('span', class_='product-price--val-small')
                desconto_tag = card.find('span', class_='product-card--discount')
                
                if not nome_tag or not preco_promocional_tag: continue
                
                nome = nome_tag.text.strip()
                link = "https://www.nuuvem.com" + card.get('href')
                
                promo_id = f"Nuuvem-{nome.replace(' ', '_')}" 
                
                promos[promo_id] = {
                    'nome': nome,
                    'desconto': desconto_tag.text.strip() if desconto_tag else "N/A",
                    'preco_novo': preco_promocional_tag.text.strip(),
                    'preco_normal': preco_normal_tag.text.strip() if preco_normal_tag else "N/A",
                    'link_store': link,
                    'data_fim': "Indisponível (Nuuvem)",
                    'imagem': "https://i.imgur.com/yC6c0fA.png", # Imagem padrão da Nuuvem
                    'plataforma': 'Nuuvem'
                }
            return promos
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao raspar Nuuvem: {e}")
            return {}

    def _scrape_epicgames(self):
        """Busca promoções na Epic Games (Scraping simplificado)."""
        URL = "https://store.epicgames.com/pt-BR/browse?sortBy=releaseDate&sortDir=DESC&tag=Sale"
        headers = {'User-Agent': 'DiscordBot'}
        promos = {}
        
        try:
            response = requests.get(URL, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            cards = soup.find_all('a', class_='css-1g9t06x') 

            for i, card in enumerate(cards):
                if i >= 15: break
                
                nome_tag = card.find('div', class_='css-rgpb39')
                preco_tag = card.find('div', class_='css-4lny3h')
                
                if not nome_tag or not preco_tag: continue
                
                nome = nome_tag.text.strip()
                link = "https://store.epicgames.com" + card.get('href', '/pt-BR/offers/no-link')
                
                preco_info = preco_tag.text.split('R$')
                preco_novo = 'R$' + preco_info[-1] if len(preco_info) > 1 else "Grátis/Desconhecido"
                
                promo_id = f"Epic-{nome.replace(' ', '_')}"
                
                promos[promo_id] = {
                    'nome': nome,
                    'desconto': 'N/A' if "Grátis" in preco_novo else "Ver link",
                    'preco_novo': preco_novo,
                    'preco_normal': "N/A",
                    'link_store': link,
                    'data_fim': "Semanal (Ver Epic)",
                    'imagem': "https://i.imgur.com/97yC71Q.png", # Imagem padrão da Epic
                    'plataforma': 'Epic Games'
                }
            return promos
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao raspar Epic Games: {e}")
            return {}

    # --- Lógica de Execução e Agendamento ---
    
    # Roda diariamente às 10:00 (Ajuste o fuso e horário se necessário)
    @tasks.loop(time=datetime.time(hour=10, minute=0)) 
    async def checar_promocoes(self):
        await self.raspar_e_enviar_promocoes(enviar_novas=True)

    @checar_promocoes.before_loop
    async def before_checar_promocoes(self):
        await self.bot.wait_until_ready()
        print("✅ Loop de checagem de promoções multi-plataforma iniciado.")
    
    async def raspar_e_enviar_promocoes(self, enviar_novas=False):
        
        # ✅ Usa self.canal_promo_id que foi passado no __init__
        canal = self.bot.get_channel(self.canal_promo_id)
        if not canal:
            print(f"❌ Erro: Canal de promoção com ID {self.canal_promo_id} não encontrado.")
            return

        # Executa todos os scrapings em paralelo (para economizar tempo)
        steam_promos_future = self.bot.loop.run_in_executor(None, self._scrape_steamdb)
        nuuvem_promos_future = self.bot.loop.run_in_executor(None, self._scrape_nuuvem)
        epic_promos_future = self.bot.loop.run_in_executor(None, self._scrape_epicgames)

        steam_promos = await steam_promos_future
        nuuvem_promos = await nuuvem_promos_future
        epic_promos = await epic_promos_future

        promocoes_hoje = {}
        promocoes_hoje.update(steam_promos)
        promocoes_hoje.update(nuuvem_promos)
        promocoes_hoje.update(epic_promos)

        hoje = datetime.date.today().strftime('%Y-%m-%d')
        novas_promocoes_por_plataforma = {"Steam": {}, "Nuuvem": {}, "Epic Games": {}}
        
        # 1. Comparação e Separação das Novas Ofertas
        
        for promo_id, promo_data in promocoes_hoje.items():
            if 'yesterday' not in self.sales_data or promo_id not in self.sales_data['yesterday']:
                plataforma = promo_data['plataforma']
                novas_promocoes_por_plataforma[plataforma][promo_id] = promo_data

        # 2. Salva o Novo Estado
        self.sales_data = {
            'yesterday': self.sales_data.get('today', {}), 
            'today': promocoes_hoje,
            'data_execucao': hoje
        }
        self._save_sales_history(self.sales_data)
        
        # 3. Envia as Novas Promoções (Separável por Plataforma)
        if enviar_novas:
            for plataforma, promos in novas_promocoes_por_plataforma.items():
                if promos:
                    await self._enviar_lista_promocoes(
                        promos, 
                        canal, 
                        f"🔥 Novas Ofertas {plataforma} Adicionadas Hoje!", 
                        plataforma
                    )
            await canal.send(f"✅ Execução diária multi-plataforma concluída em {hoje}.")
        
        return promocoes_hoje

    async def _enviar_lista_promocoes(self, lista_promos: dict, canal, titulo: str, plataforma: str):
        """Formata e envia uma lista de promoções para o canal, usando a cor da plataforma."""
        
        promos_a_enviar = list(lista_promos.values())[:5] # Limita a 5 por plataforma
        plataforma_color = PLATFORM_COLORS.get(plataforma, discord.Color.default())
        
        await canal.send(f"### {titulo} ({len(promos_a_enviar)} jogos)")

        for promo in promos_a_enviar:
            embed = discord.Embed(
                title=f"🎮 {promo['nome']} | {promo['desconto']}",
                url=promo['link_store'],
                description=f"Preço: **{promo['preco_novo']}** (Normal: {promo['preco_normal']})",
                color=plataforma_color, 
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=promo['imagem'])
            embed.set_author(name=f"Plataforma: {plataforma}", icon_url=promo['imagem'])
            
            embed.add_field(name="💰 Desconto", value=f"**{promo['desconto']}**", inline=True)
            embed.add_field(name="📅 Fim da Promoção", value=promo['data_fim'], inline=True)
            
            await canal.send(embed=embed)
            await asyncio.sleep(1) 


    # --- COMANDO: Promoções do Dia Anterior ---
    @commands.command(name='promosontem')
    async def promos_ontem_cmd(self, ctx, plataforma: str = None):
        """
        Envia a lista de promoções ativas no dia anterior, opcionalmente filtrada por plataforma.
        Uso: !promosontem [Steam|Nuuvem|Epic Games]
        """
        await ctx.defer()
        
        if 'yesterday' not in self.sales_data or not self.sales_data['yesterday']:
            return await ctx.send("Não há dados de promoções salvas do dia anterior.")

        data_anterior = self.sales_data.get('data_execucao', 'Data Indisponível')
        todas_promos_ontem = self.sales_data['yesterday']
        promos_filtradas = {}

        plataforma_capitalizada = plataforma.title() if plataforma else None
        
        if plataforma_capitalizada and plataforma_capitalizada in PLATFORM_COLORS:
            for promo_id, promo_data in todas_promos_ontem.items():
                if promo_data.get('plataforma') == plataforma_capitalizada:
                    promos_filtradas[promo_id] = promo_data
            
            titulo = f"↩️ Promoções Ativas {plataforma_capitalizada} em {data_anterior}"
            await self._enviar_lista_promocoes(promos_filtradas, ctx.channel, titulo, plataforma_capitalizada)
        
        elif plataforma is None:
            
            promos_agrupadas = {"Steam": {}, "Nuuvem": {}, "Epic Games": {}}
            for promo_data in todas_promos_ontem.values():
                p = promo_data.get('plataforma', 'Steam')
                promos_agrupadas[p][promo_data['nome']] = promo_data
                
            await ctx.send(f"### 🕒 Promoções de ONTEM ({data_anterior})")
            for p, promos in promos_agrupadas.items():
                if promos:
                    await self._enviar_lista_promocoes(
                        promos, 
                        ctx.channel, 
                        f"Lista Ativa {p}", 
                        p
                    )
        
        else:
            await ctx.send("Plataforma inválida. Use `Steam`, `Nuuvem` ou `Epic Games`.")


# ✅ Função de setup agora recebe argumentos kwargs
async def setup(bot, **kwargs):
    # ✅ Passa os argumentos para o construtor da classe
    await bot.add_cog(MultiPlatformSales(bot, **kwargs))