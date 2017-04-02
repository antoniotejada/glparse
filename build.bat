REM Note this name cannot contain hyphens or dots because it's used as package
REM basename
SET GLTRACE_BASENAME=sonicdash

build.py all  --targets=trace,ndk,ant,install,run  ^
              --android-home=c:\android-sdk ^
              --ant-home=c:\apache-ant-1.9.4 ^
              --ndk-home=c:\android-ndk-r10d ^
              --trace-filepath=samples\%GLTRACE_BASENAME%.gltrace.gz ^
              --package-name=%GLTRACE_BASENAME% ^
              --trace-contexts=0
