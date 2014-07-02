setlocal

REM Load the .prof files with RunSnakeRun (instaled by pip as runsnake in the Python scripts directory)
set BASENAME=%1
if [%BASENAME%] == [] set BASENAME=deinline
"\Program Files\Python27\python.exe" -O -m cProfile -o _out\%BASENAME%.prof ^
    "c:\Users\atejada\Documents\works\python\glparse\%BASENAME%.py" ^
    > _out\%BASENAME%.inc 2> _out\%BASENAME%.log
"\Program Files\Python27\scripts\runsnake" _out\%BASENAME%.prof