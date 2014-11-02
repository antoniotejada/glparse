REM %1: Temporary output directory to append to _out

setlocal

REM Get parameters from command line
set OUT_SUBDIR=%1

if "%OUT_SUBDIR%" EQU "" set OUT_SUBDIR=NativeActivity
set OUT_DIR=_out\%OUT_SUBDIR%

set NDK_ROOT=c:\android-ndk-r9d\

REM Delete temporaries

del /F /Q /S %OUT_DIR%\obj
del /F /Q /S %OUT_DIR%\libs

REM To enable GNU make debugging
REM set MAKEFLAGS=-d

REM needs android-9 for NativeActivity, Android-12 for GLES2

%NDK_ROOT%\ndk-build.cmd V=1 NDK_DEBUG=1 NDK_LOG=0 NDK_PROJECT_PATH=activity/jni/ ^
    APP_BUILD_SCRIPT=activity\jni\Android.mk APP_OPTIM=debug APP_ABI=armeabi-v7a ^
    APP_PLATFORM=android-12 TARGET_PLATFORM=android-12 NDK_LIBS_OUT=%OUT_DIR%/libs ^
    NDK_OUT=%OUT_DIR%/obj 
