setlocal

set NDK_ROOT=c:\android-ndk-r9d\

REM Delete temporaries

del /F /Q /S _out\obj
del /F /Q /S _out\libs

REM To enable GNU make debugging
REM set MAKEFLAGS=-d

REM needs android-9 for NativeActivity, Android-12 for GLES2
%NDK_ROOT%\ndk-build.cmd V=1 NDK_DEBUG=1 NDK_LOG=0 NDK_PROJECT_PATH=activity/jni/ APP_BUILD_SCRIPT=activity\jni\Android.mk APP_OPTIM=debug APP_ABI=armeabi-v7a APP_PLATFORM=android-12 TARGET_PLATFORM=android-12 NDK_LIBS_OUT=_out/libs NDK_OUT=_out/obj
