:loop
python bot.py -ne -1
if %errorlevel% EQU -1 (
    goto loop
)