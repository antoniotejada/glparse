REM Uninstall completely to prevent certificate failures when over-installing
REM builds from a different machine
REM %1: Package rootname

setlocal

REM Get parameters from command line
set OUT_SUBDIR=%1
if "%OUT_SUBDIR%" EQU "" set OUT_SUBDIR=NativeActivity
set OUT_DIR=_out\%OUT_SUBDIR%

set PACKAGE_NAME=%1
if "%PACKAGE_NAME%" EQU "" set PACKAGE_NAME=NativeActivity

adb shell pm uninstall com.example.%PACKAGE_NAME%
adb install -r %OUT_DIR%/bin/%PACKAGE_NAME%-debug.apk
adb logcat -c
adb shell am start --ez stop_motion true -n com.example.%PACKAGE_NAME%/android.app.NativeActivity
adb logcat -v threadtime
