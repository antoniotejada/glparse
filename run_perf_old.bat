
SET PACKAGE=com.example.sonicdash_stage1
SET ACTIVITY=android.app.NativeActivity
SET APK_FILEPATH=_out\sonicdash_stage1\bin\sonicdash_stage1-debug.apk

REM get the device information
adb shell getprop ro.product.device > device.txt
set /p DEVICE=<device.txt

REM Stop
adb shell am force-stop %PACKAGE%

REM uninstall
adb uninstall %PACKAGE%

REM install the apk
adb install -r %APK_FILEPATH%

SET OPTIONS=--ez stop_motion false --ei egl_depth_size 16
SET OPTIONS=%OPTIONS% --ez egl_window_bit false --ei gl_get_error 0 --ez gl_log_context true
SET COLORDEPTH=--ei egl_red_size 8 --ei egl_green_size 8 --ei egl_blue_size 8 --ei egl_alpha_size 8

REM other options
rem --ei capture_frequency 100 --ez capture_compressed true ^
REM run it 

CALL :do_test 720 1280 0 0 45 false
CALL :do_test 720 1280 0 0 45 true
CALL :do_test 720 1280 0 1 45 true
CALL :do_test 720 1280 1 0 50 true
CALL :do_test 720 1280 1 1 50 true
CALL :do_test 720 1280 2 0 45 true
CALL :do_test 720 1280 2 1 45 true
CALL :do_test 720 1280 3 0 45 true
CALL :do_test 720 1280 3 1 45 true

CALL :do_test 1080 1920 0 0 60 false
CALL :do_test 1080 1920 0 0 60 true
CALL :do_test 1080 1920 0 1 60 true
CALL :do_test 1080 1920 1 0 70 true
CALL :do_test 1080 1920 1 1 70 true
CALL :do_test 1080 1920 2 0 60 true
CALL :do_test 1080 1920 2 1 60 true
CALL :do_test 1080 1920 3 0 60 true
CALL :do_test 1080 1920 3 1 60 true

CALL :do_test 2160 3840 0 0 75 false
CALL :do_test 2160 3840 0 0 75 true
CALL :do_test 2160 3840 0 1 75 true
CALL :do_test 2160 3840 1 0 90 true
CALL :do_test 2160 3840 1 1 90 true
CALL :do_test 2160 3840 2 0 75 true
CALL :do_test 2160 3840 2 1 75 true
CALL :do_test 2160 3840 3 0 75 true
CALL :do_test 2160 3840 3 1 75 true

EXIT /B %ERRORLEVEL%

:do_test

REM resize to prevent losing entries when doing long experiments (256K is not enough)
REM %1 width
REM %2 height
REM %3 egl_swapbuffer_sync
REM %4 iteration index
REM %5 delay in seconds
REM %6 egl_pbuffer_bit false/true
adb logcat -g
adb logcat -G 512K
adb logcat -g

REM clear logcat
adb logcat -c

SET RESOLUTION=--ei egl_width %1 --ei egl_height %2
SET SWAPABUFFERSSYNC=--ei egl_swapbuffers_sync %3
SET PBUFFERBIT=--ez egl_pbuffer_bit %6

REM run the test
adb shell am start %OPTIONS% ^
                   %COLORDEPTH% ^
                   %RESOLUTION% ^
                   %SWAPABUFFERSSYNC% ^
                   %PBUFFERBIT% ^
                   %PACKAGE%/%ACTIVITY%

REM wait for a few seconds
adb shell sleep %5

REM collect the log
REM adb logcat -d -v threadtime | find /I "native-activity" > %DEVICE%-sync%3-%1x%2-perf.log
adb logcat -d -v threadtime | find /I "native-activity" > %DEVICE%-sync_%3_pb_%6_%4-%1x%2-perf.log

EXIT /B 0