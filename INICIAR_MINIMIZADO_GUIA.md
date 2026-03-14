# 🎯 Como Iniciar o Bot Minimizado na Bandeja

## ⚠️ PRIMEIRO: Execute o Setup (UMA ÚNICA VEZ)

**Na primeira vez que usar a máquina/pasta:**

1. Duplo-clique em `SETUP.bat`
2. Aguarde até ver ✅ "Setup concluído com sucesso!"
3. Pronto! Agora pode usar os scripts abaixo

⏭️ **A partir da próxima vez, pule este passo!**

---

## ✨ Opções Disponíveis

### **Opção 1: Duplo-clique em `Iniciar_Bot_Oculto.vbs` (MAIS FÁCIL)**
- ✅ Não mostra nenhuma janela
- ✅ Bot inicia direto na bandeja
- ✅ Mais elegante e profissional

**Passo a passo:**
1. Localize o arquivo `Iniciar_Bot_Oculto.vbs` na pasta do projeto
2. Duplo-clique nele
3. 🤖 Bot inicia sem mostrar nada!
4. Procure pelo ícone na bandeja do sistema (📺 perto do relógio)

---

### **Opção 2: Duplo-clique em `Iniciar_Minimizado.bat`**
- ✅ Mostra janela do terminal minimizada
- ✅ Mais fácil de debug (ver logs se clicar)
- ⚠️ Um pouco menos elegante que a Opção 1

**Passo a passo:**
1. Duplo-clique em `Iniciar_Minimizado.bat`
2. Uma janela do terminal abrirá minimizada
3. 🤖 Bot inicia e rodará em background

---

### **Opção 3: Via Terminal (Administrativo)**
```powershell
python iniciar_minimizado.py
```

---

## 📍 Achar o Bot na Bandeja

**Ao usar qualquer uma das opções acima:**

1. Procure pela bandeja do sistema (canto inferior direito)
2. Você verá ícones de programas rodando
3. O bot pode estar lá! (pode precisar clicar na seta para expandir)

**Para ver os logs em tempo real:**
- Clique com botão direito no ícone do bot (se houver)
- Ou abra o arquivo `Iniciar_Minimizado.bat` normalmente para ver logs

---

## 🔄 Parar o Bot

**Opção 1: Via Tarefa (Mais Fácil)**
```
Ctrl + Shift + Esc  (abre Task Manager)
Procure por: python.exe ou bot
Clique em "End Task"
```

**Opção 2: Via Terminal**
```powershell
taskkill /IM python.exe /F
```

---

## 🎨 Criar Atalho de Desktop (Opcional)

Se quiser um atalho bonito na Desktop:

1. Clique com direito no `Iniciar_Bot_Oculto.vbs`
2. "Enviar para" → "Desktop (criar atalho)"
3. Agora pode clicar duplo na Desktop para iniciar!

---

## 💡 Recomendação

**Para máquine de produção/servidor:**
- Use `Iniciar_Bot_Oculto.vbs` ✅ (mais limpo)

**Para desenvolvimento:**
- Use `Iniciar_Minimizado.bat` (vê os logs se problema)

---

## 🐛 Se não funcionar

**Erro: "Python não encontrado"**
- Instale Python: https://www.python.org/downloads/
- ⚠️ IMPORTANTE: Marque "Add Python to PATH" durante instalação
- Depois execute `SETUP.bat` novamente

**Erro: "No module named 'dotenv'" ou similar**
- Execute `SETUP.bat` novamente
- Ele vai instalar todas as dependências automaticamente

**Erro: Acesso Negado**
- Execute os arquivos como Administrador
- Clique direito → "Run as administrator"

**O Bot não aparece na bandeja**
- Pode estar rodando normalmente (não minimizado)
- Verifique Task Manager: `Ctrl + Shift + Esc`
- Se não aparecer ali, execute `Iniciar_Minimizado.bat` para ver os logs

---

## 📋 Checklist para Primeira Execução

- [ ] Python instalado e no PATH
- [ ] Executou `SETUP.bat` com sucesso
- [ ] Arquivo `.env` configurado (se necessário)
- [ ] Executou `Iniciar_Bot_Oculto.vbs` ou `Iniciar_Minimizado.bat`
- [ ] Bot aparece na bandeja (ou Task Manager)

---
