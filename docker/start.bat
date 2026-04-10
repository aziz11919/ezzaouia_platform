@echo off
echo ════════════════════════════════════════════
echo   EZZAOUIA Platform — Docker Deployment
echo   MARETAP S.A. — CPF Zarzis
echo ════════════════════════════════════════════

echo [1/3] Starting Ollama (on HOST, not Docker)...
start "Ollama" /min cmd /c "ollama serve"
timeout /t 3 /nobreak > nul

echo [2/3] Building and starting Docker containers...
docker-compose up --build -d

echo [3/3] Checking container status...
docker-compose ps

echo ════════════════════════════════════════════
echo   Platform accessible at:
echo   http://localhost:8000
echo   http://192.168.87.x:8000 (network)
echo ════════════════════════════════════════════
echo.
echo   Useful commands:
echo   docker-compose logs -f web      (Django logs)
echo   docker-compose logs -f celery   (Celery logs)
echo   docker-compose restart web      (Restart Django)
echo   docker-compose down             (Stop all)
echo ════════════════════════════════════════════
pause
