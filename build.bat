cls

setlocal

REM Generate the .inc file
glparse.py > _out\trace.inc 2> _out\trace.log

REM Build the ndk project
call ndk-build.bat

if ERRORLEVEL 1 GOTO ERROR

REM Build the ant project
call ant-build.bat

if ERRORLEVEL 1 GOTO ERROR

REM Install and run

adb install -r _out/bin/NativeActivity-debug.apk
adb logcat -c
adb shell am start -n com.example.native_activity/android.app.NativeActivity
adb logcat

:END

:ERROR
echo ERROR BUILDING - STOPPING
