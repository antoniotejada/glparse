
# Delete temporaries
rm -rf _out/assets
rm _out/trace.inc
rm _out/trace2.inc
rm _out/trace.log
rm _out/trace2.log
mkdir _out/assets


# Generate the trace.inc file
echo Generating trace.inc file
python -O glparse.py > _out/trace.inc 2> _out/trace.log

# echo De-inlining trace
# python -O deinline.py > _out/trace2.inc 2> _out/trace2.log
cp _out/trace.inc _out/trace2.inc

echo Building NDK project
# Build the NDK project
NDK_ROOT=~/android-ndk-r9d/

# Delete temporaries
rm -rf _out/obj
rm -rf _out/libs

# To enable GNU make debugging
# set MAKEFLAGS=-d

# needs android-9 for NativeActivity, Android-12 for GLES2
$NDK_ROOT/ndk-build V=1 NDK_DEBUG=1 NDK_LOG=0 NDK_PROJECT_PATH=activity/jni/ APP_BUILD_SCRIPT=activity/jni/Android.mk APP_ABI=armeabi-v7a TARGET_PLATFORM=android-12 NDK_LIBS_OUT=_out/libs NDK_OUT=_out/obj

# Build the ANT project
echo Building ANT project

# Delete temporaries
rm -rf _out/bin

# See http://developer.android.com/reference/android/app/NativeActivity.html
# See http://stackoverflow.com/questions/14848042/running-the-ndk-native-activity-sample-from-a-command-line-ide
# See http://developer.android.com/tools/help/android.html
# Download ant from http://www.apache.org/dist/ant/binaries/

PATH=$PATH:~/adt-bundle-linux-x86_64/sdk/tools/

# The target to use can be known via "android list targets"
# XXX Should we just "android create project" and check-in those files?
android update project --path ./activity --name NativeActivity --target 1
# Linux ant fails with Unexpected element "{}manifest"  when passing -buildfile,
# switch to activity the directory and invoke with no parameters
cd activity
ant -lib ../_out/libs debug
cd ..

# Make sure we uninstall the activity to prevent certificate issues when installing
# over old versions or compiled on other machines
adb shell pm uninstall com.example.native_activity
adb install -r _out/bin/NativeActivity-debug.apk
adb logcat -c
adb shell am start -n com.example.native_activity/android.app.NativeActivity
adb logcat -v threadtime
