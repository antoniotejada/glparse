REM Build the ant project and generate the APK
REM %1: Package root name

REM See http://developer.android.com/reference/android/app/NativeActivity.html
REM See http://stackoverflow.com/questions/14848042/running-the-ndk-native-activity-sample-from-a-command-line-ide
REM See http://developer.android.com/tools/help/android.html
REM Download ant from http://www.apache.org/dist/ant/binaries/

setlocal


REM Get parameters from command line

set OUT_SUBDIR=%1
if "%OUT_SUBDIR%" EQU "" set OUT_SUBDIR=NativeActivity
set OUT_DIR=_out\%OUT_SUBDIR%

set PACKAGE_NAME=%1
if "%PACKAGE_NAME%" EQU "" set PACKAGE_NAME=NativeActivity

del /F /Q /S %OUT_DIR%\bin

set PATH=%PATH%;c:\adt-bundle-windows-x86_64-20140321\sdk\tools\;"c:\Program Files\apache-ant-1.9.4\bin"

REM Generate a project
REM The target to use can be known via "android list targets"
REM See http://developer.android.com/tools/projects/projects-cmdline.html

rmdir /S /Q %OUT_DIR%\activity
call android create project ^
    --path %OUT_DIR%/activity ^
    --name %PACKAGE_NAME% ^
    --target 1 ^
    --package com.example.%PACKAGE_NAME% ^
    --activity %PACKAGE_NAME%

REM android create disables echo, turn it on
echo on

REM Delete unnecessary files in the created project
rmdir /S /Q %OUT_DIR%\activity\bin
rmdir /S /Q %OUT_DIR%\activity\libs
rmdir /S /Q %OUT_DIR%\activity\src

REM Override the ant.properties and AndroidManifest.xml files
REM XXX Should this do an android update project instead + the proper renaming?
copy activity\ant.properties %OUT_DIR%\activity
copy activity\AndroidManifest.xml 

REM Rename package in AndroidManifest.xml
type activity\AndroidManifest.xml | python -c "import sys,re;[sys.stdout.write(re.sub('native_activity', '%PACKAGE_NAME%', line)) for line in sys.stdin]" > %OUT_DIR%\activity\AndroidManifest.xml

REM Do the build
call ant -buildfile %OUT_DIR%/activity/ -lib %OUT_DIR%/libs debug