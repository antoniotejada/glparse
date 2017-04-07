REM SET PACKAGE=com.example.Tests
REM SET ACTIVITY=android.app.NativeActivity

REM SET PACKAGE=com.kipolabs.tusker
REM SET ACTIVITY=com.kipolabs.tusker.MainActivity
REM SET TRACE_FILEPATH=tusker.gltrace.gz

REM SET PACKAGE=com.kipoapp.reader.profile
REM SET ACTIVITY=com.kipoapp.reader.Reader
REM SET TRACE_FILEPATH=kipoprofile.gltrace.gz

REM SET PACKAGE=com.example.kipoprofile
REM SET ACTIVITY=android.app.NativeActivity
REM SET TRACE_FILEPATH=kipoprofile250.gltrace.gz

SET PACKAGE=com.google.fpl.zooshi
SET ACTIVITY=.ZooshiActivity
SET TRACE_FILEPATH=zooshi.gltrace.gz

SET PARAMS="--ez stop_motion false"

adb shell am force-stop %PACKAGE%

adb shell am start --opengl-trace %PARAMS% %PACKAGE%/%ACTIVITY%

glcap.py capture --store-textures --trace-filepath=%TRACE_FILEPATH%