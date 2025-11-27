import asyncio

# Simples gerador de IDs sequenciais.
# Em produção você pode substituir por banco de dados.
ticket_sequencial = 1

async def gerar_id_ticket_formato():
    global ticket_sequencial

    id_num = ticket_sequencial
    ticket_sequencial += 1

    return str(id_num).zfill(5)
