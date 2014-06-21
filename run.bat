REM Uninstall completely to prevent certificate failures when over-installing
REM builds from a different machine
adb shell pm uninstall com.example.native_activity
adb install -r _out/bin/NativeActivity-debug.apk
adb logcat -c
adb shell am start -n com.example.native_activity/android.app.NativeActivity
adb logcat -v threadtime
