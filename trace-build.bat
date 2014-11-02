REM Delete old assets and generate new assets and trace include files
REM %1: Out directory name
REM %2: Trace filepath
REM %3: Comma-separated list 0-based of indices to the GL contexts to trace

setlocal

REM Get parameters from command line
set OUT_SUBDIR=%1
if "%OUT_SUBDIR%" EQU "" set OUT_SUBDIR=NativeActivity
set OUT_DIR=_out\%OUT_SUBDIR%

set TRACE_FILEPATH=%2
if "%TRACE_FILEPATH%" EQU "" set TRACE_FILEPATH=_out\com.vectorunit.blue-30s-textures.gltrace.gz

set GL_CONTEXTS=%3
if "%GL_CONTEXTS%" EQU "" set GL_CONTEXTS=0

REM Create directories
mkdir %OUT_DIR%
mkdir %OUT_DIR%\assets

REM Deleting old assets
del /F /Q /S %OUT_DIR%\assets > NUL

REM Generate the .inc file
python -O glparse.py %TRACE_FILEPATH% %OUT_DIR% %GL_CONTEXTS% > %OUT_DIR%\trace.inc 2> %OUT_DIR%\trace.log

if ERRORLEVEL 1 exit /B

REM Generate the deinlined file
REM python -O deinline.py > %OUT_DIR%\trace2.inc 2> %OUT_DIR%\trace2.log
copy /Y %OUT_DIR%\trace.inc %OUT_DIR%\trace2.inc