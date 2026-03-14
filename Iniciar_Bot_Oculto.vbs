' ============================================================
' VBScript para iniciar o bot completamente oculto
' Uso: Duplo-clique em "Iniciar_Bot_Oculto.vbs"
' ============================================================

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Define o caminho do diretório do projeto
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Monta o comando para ativar venv e executar bot
strCommand = "cmd /c cd /d """ & strPath & """ && .venv\\Scripts\\activate.bat && python bot.py"

' Executa completamente oculto (0 = hidden)
objShell.Run strCommand, 0
