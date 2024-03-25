python --version 2>NUL
if errorlevel 1 goto errorNoPython

python ./_preview_shader_deliver.py
pause

goto:eof

:errorNoPython
echo.
echo Error^: Python not installed

pause