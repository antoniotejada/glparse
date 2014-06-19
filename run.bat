adb install -r _out/bin/NativeActivity-debug.apk
adb logcat -c
adb shell am start -n com.example.native_activity/android.app.NativeActivity
adb logcat -v threadtime
