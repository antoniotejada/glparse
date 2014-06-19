cls

setlocal

REM Generate the .inc file
glparse.py > _out\trace.inc 2> _out\trace.log

if ERRORLEVEL 1 GOTO ERROR

REM Build the ndk project
call ndk-build.bat

if ERRORLEVEL 1 GOTO ERROR

REM Build the ant project
call ant-build.bat

if ERRORLEVEL 1 GOTO ERROR

REM Install and run
call run.bat

goto END

:ERROR
echo ERROR BUILDING - STOPPING

:END
