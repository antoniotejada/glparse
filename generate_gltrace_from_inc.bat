REM Create a gltrace file from a C include trace file
REM 1. Generate an apk invoking glparse using the include file as trace.inc
REM 2. Execute the apk on the device under --opengl-trace under parse
REM 3. Extract the trace via glcap

REM copy the trace include file into the output dir
SET TRACE_INC_BASENAME=resources
MKDIR _out
MKDIR _out\%TRACE_INC_BASENAME%
COPY tests\glparse\includes\%TRACE_INC_BASENAME%.inc  _out\%TRACE_INC_BASENAME%\trace2.inc

REM Generate and install an apk from that trace2.inc

build.py all --targets=ant,ndk,install ^
             --ndk-home=c:\android-ndk-r10d ^
             --ant-home=c:\apache-ant-1.9.4 ^
             --android-home=c:\android-sdk ^
             --output-dir=_out\%TRACE_INC_BASENAME% ^
             --package-name=%TRACE_INC_BASENAME%


IF %ERRORLEVEL% NEQ 0 GOTO END

REM Run that apk and capture its gltrace

SET PACKAGE=com.example.%TRACE_INC_BASENAME%
SET ACTIVITY=android.app.NativeActivity
SET PARAMS="--ez stop_motion false --ei frame_limit 0"

adb shell am force-stop %PACKAGE%
adb shell am start --opengl-trace %PARAMS% %PACKAGE%/%ACTIVITY%

REM Wait a bit for the application to start, otherwise glcap will error out
timeout 2

glcap.py capture --trace-filepath=%TRACE_INC_BASENAME%.gltrace.gz

IF %ERRORLEVEL% NEQ 0 GOTO END

adb logcat -d | find /I "native"

:END