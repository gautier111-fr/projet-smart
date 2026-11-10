@echo off
REM Double-cliquer sur ce fichier pour ouvrir l'interface dans le navigateur.
cd /d "%~dp0"
python -m streamlit run app.py
pause
