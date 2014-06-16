REM See http://developer.android.com/reference/android/app/NativeActivity.html
REM See http://stackoverflow.com/questions/14848042/running-the-ndk-native-activity-sample-from-a-command-line-ide
REM See http://developer.android.com/tools/help/android.html
REM Download ant from http://www.apache.org/dist/ant/binaries/

setlocal

del /F /Q /S _out\bin

set PATH=%PATH%;c:\adt-bundle-windows-x86_64-20140321\sdk\tools\;"c:\Program Files\apache-ant-1.9.4\bin"

REM The target to use can be known via "android list targets"
call android update project --path ./activity --name NativeActivity --target 1
call ant -buildfile activity/ -lib _out/libs debug
