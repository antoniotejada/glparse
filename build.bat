SET TRACE_FILEPATH=samples\com.vectorunit.blue-30s-textures.gltrace.gz
REM Note this name cannot contain hyphens or dots 
SET PACKAGE_NAME=vectorunit30s

build.py all  --targets=trace,ndk,ant,install,run  ^
              --android-home=c:\android-sdk ^
              --ant-home=c:\apache-ant-1.9.4 ^
              --ndk-home=c:\android-ndk-r10d ^
              --trace-filepath=%TRACE_FILEPATH% ^
              --package-name=%PACKAGE_NAME% ^
              --trace-contexts=1 ^
              --run-options="--ei egl_width 1280 --ei egl_height 1024" ^
              --output-dir=_out\%PACKAGE_NAME%
