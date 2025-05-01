chcp 65001 > nul

@echo off
rem ====== src\scripts\daily_job.bat ======
python -m models.inference                  || exit /b
python -m optimization.schedule_optimizer ^
        --out ..\results\schedule_%date:~10,4%-%date:~4,2%-%date:~7,2%.json
