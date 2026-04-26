@echo off
echo ============================================
echo   EZZAOUIA Platform - Mode Developpement
echo ============================================
echo.

REM Demarrer Django API
start "Django API :8000" cmd /k "cd /d C:\ezzaouia_platform && venv\Scripts\activate && python manage.py runserver"

REM Demarrer React Frontend
start "React Frontend :3000" cmd /k "cd /d C:\ezzaouia_platform\frontend && npm run dev"

REM Demarrer Ollama (optionnel)
start "Ollama LLM" cmd /k "ollama serve"

echo.
echo Services demarres :
echo   Django API    : http://localhost:8000
echo   React App     : http://localhost:3000
echo   Ollama LLM    : http://localhost:11434
echo.
echo Ouvrez http://localhost:3000 dans votre navigateur.
echo.
pause
