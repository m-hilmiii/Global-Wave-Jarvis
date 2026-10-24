Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir
WshShell.Run """C:\Users\unalm\AppData\Local\Programs\Python\Python311\pythonw.exe"" """ & currentDir & "\run_global_wave.py""", 0, False
