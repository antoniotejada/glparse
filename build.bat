cls

setlocal

REM Deleting old assets
del /F /Q /S _out\assets > NUL

REM Generate the .inc file
python -O glparse.py > _out\trace.inc 2> _out\trace.log

if ERRORLEVEL 1 GOTO ERROR

REM Generate the deinlined file
REM python -O deinline.py > _out\trace2.inc 2> _out\trace2.log
copy /Y _out\trace.inc _out\trace2.inc

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
