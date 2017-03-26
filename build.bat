rem build.py all --trace-filepath=samples\kipo.gltrace.gz --trace-contexts=0 --deinline

build.py all  --targets=ndk,ant,install,run  ^
              --android-home=c:\android-sdk ^
              --ant-home=c:\apache-ant-1.9.4 ^
              --ndk-home=c:\android-ndk-r10d ^
              --trace-filepath=samples\com.amazon.tv.launcher.gltrace.gz ^
              --verbose ^
              --trace-contexts=0
