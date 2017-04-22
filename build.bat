SET TRACE_FILEPATH=samples\sonicdash-stage1.gltrace.gz
REM Note this name cannot contain hyphens or dots 
SET PACKAGE_NAME=sonicdash_stage1

REM SET TRACE_FILEPATH=samples\com.vectorunit.blue-30s-textures.gltrace.gz
REM Note this name cannot contain hyphens or dots
REM SET PACKAGE_NAME=vectorunit30s

REM SET TRACE_FILEPATH=samples\triangle.gltrace.gz
REM Note this name cannot contain hyphens or dots
REM SET PACKAGE_NAME=triangle

python -O build.py all  --targets=trace,ndk,ant,install,run  ^
              --android-home=c:\android-sdk ^
              --ant-home=c:\apache-ant-1.9.4 ^
              --ndk-home=c:\android-ndk-r10d ^
              --trace-filepath=%TRACE_FILEPATH% ^
              --package-name=%PACKAGE_NAME% ^
              --trace-contexts=1 ^
              --run-options="--ei egl_width 1280 --ei egl_height 1024 --ez stop_motion false --ei egl_swapbuffers_sync 2" ^
              --output-dir=_out\%PACKAGE_NAME%
