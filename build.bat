REM %1: Package and out temp directory root name, NativeActivity by default
REM %2: Trace filepath
REM %3: Comma-separated list 0-based of indices to the GL contexts to trace

cls

setlocal

REM Generate the trace
call trace-build.bat %1 %2 %3

if ERRORLEVEL 1 GOTO ERROR

REM Build the ndk project
call ndk-build.bat %1

if ERRORLEVEL 1 GOTO ERROR

REM Build the ant project
call ant-build.bat %1

if ERRORLEVEL 1 GOTO ERROR

REM Install and run
call run.bat %1

goto END

:ERROR
echo ERROR BUILDING - STOPPING

:END
