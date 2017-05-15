REM Provide deinline or glparse as parameter to profile one or the other
setlocal

REM Load the .prof files with RunSnakeRun (instaled by pip as runsnake in the Python scripts directory)
set BASENAME=%1
set PYTHONDIR=c:\Python27\
REM XXX Fix this, glparse has default parameters, deinline doesn't
if [%BASENAME%] == [] set BASENAME=deinline
"%PYTHONDIR%\python.exe" -O -m cProfile -o _out\%BASENAME%.prof ^
    "c:\Users\atejada\Documents\works\python\glparse\%BASENAME%.py"  _out\sonicdash_stage1\trace.inc 50 ^
    > _out\%BASENAME%.inc 2> _out\%BASENAME%.log
"%PYTHONDIR%\scripts\runsnake" _out\%BASENAME%.prof