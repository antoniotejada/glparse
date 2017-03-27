SET PACKAGE = com.example.Tests
SET ACTIVITY = android.app.NativeActivity
SET PARAMS = --ez stop_motion false

REM SET PACKAGE=com.kipolabs.tusker
REM SET ACTIVITY=com.kipolabs.tusker.MainActivity

REM SET PACKAGE=com.kipoapp.reader.debug
REM SET ACTIVITY=com.kipoapp.reader.Reader

adb shell am force-stop %PACKAGE%

adb shell am start --opengl-trace %PARAMS% %PACKAGE%/%ACTIVITY%

glcap.py capture --trace-filepath=glcap.gltrace.gz