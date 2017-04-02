#!/usr/bin/env python

# Copyright 2014 Antonio Tejada
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Generate a replayer APK from an Android OpenGL ES trace invoking different
utilities
"""

import errno
import os
import pipes
import scriptine
import subprocess
import string

#
# scriptine.shell is missing from the manifest in 0.2.0, provide our own shell
# functions (this is probably fixed on 0.2.0a2, but not available on pip)
#
@scriptine.misc.dry_guard
def os_system(cmd):
    if (os.system(cmd) != 0):
        raise Exception("Exception running command %s" % repr(cmd))

@scriptine.misc.dry_guard
def check_call(cmds):
    """
    :param cmds: List of program and arguments to run. Given as a list so
                 the commands and arguments are properly escaped

    On Windows, programs are given by name without extension and the shell
    is in charge of finding the right .bat, .cmd, .py, etc file, so subprocess
    invocation has to be forced with shell=True
    Being able to give the name without extension is important for cross-platform
    purposes, as in Unix the shellscript normally doesn't have an extension, but
    the Windows counterpart has a .bat or .cmd extension.
    """
    scriptine.log.mark("Calling '%s'" % string.join(cmds, " "))
    ## Subprocess fails when running ant (java tries to start gtk) and
    ## ndk (lookslike the NDK_XXX= variables are not set?
    # XXX subprocess.check_call is not working on Ubuntu,
    # - Invoking "android create project ..." causes the GUI to popup
    # - Invoking ndk-build doesn't get the command line variables properly,
    #   complains about missing
    # Both work if you use os.system instead, although you have to quote spaces
    # and other manually
    ## subprocess.check_call(cmds, shell=True)
    # Quote the command if it contains spaces
    os_system(subprocess.list2cmdline(cmds))

def trace_command(package_name = "Replayer",
                  trace_filepath = "_out/com.amazon.tv.launcher.gltrace.gz",
                  trace_contexts = "0",
                  deinline = False):
    """
    Generate C include files and assets from an OpenGL ES trace.

    :param package_name: Name of the package, full name will be
                         com.example.<package_name>
    :param trace_filepath: Path to the OpenGL ES trace file
    :param trace_contexts: Index to the 0-based OpenGL ES context to trace
    :param deinline: Perform trace deinlining
    """
    # Generate the necessary dirs and filepaths
    output_dir = scriptine.path("_out").joinpath(package_name)
    assets_dir = output_dir.joinpath("assets")
    trace_logpath = output_dir.joinpath("trace.log")
    trace_incpath = output_dir.joinpath("trace.inc")
    deinlined_incpath = output_dir.joinpath("trace2.inc")
    deinlined_logpath = output_dir.joinpath("trace2.log")

    # Create the output and assets directories
    scriptine.log.mark("Creating output and asset directories")
    output_dir.ensure_dir()
    assets_dir.ensure_dir()

    # Delete the old assets
    scriptine.log.mark("Deleting old assets")
    assets_dir.rmtree(True)

    # Generate the trace.inc file
    scriptine.log.mark("Generating the trace.inc file")
    cmd = str("python -O glparse.py %(trace_filepath)s %(output_dir)s %(trace_contexts)s "
              "> %(trace_incpath)s 2> %(trace_logpath)s" % {
                'trace_filepath' : trace_filepath,
                'output_dir' : output_dir,
                'trace_contexts' : trace_contexts,
                'trace_incpath' : trace_incpath,
                'trace_logpath' : trace_logpath,
            })

    os_system(cmd)

    # Generate the deinlined file
    if (deinline):
        scriptine.log.info("Deinlining the trace.inc file")
        cmd = str("python -O deinline.py %(trace_incpath)s > %(deinlined_incpath)s 2> "
                  "%(deinlined_logpath)s" % {
                'trace_incpath' : trace_incpath,
                'deinlined_incpath' : deinlined_incpath,
                'deinlined_logpath' : deinlined_logpath,
                })
        os_system(cmd)
    else:
        scriptine.path.copyfile(trace_incpath, deinlined_incpath)

def ndk_command(package_name = "Replayer", ndk_home = None, debug = False):
    """
    Build the NDK project and generate native object files (requires the 'trace'
    target to have been built beforehand).

    :param package_name: Name of the package, com.example.<package_name>
    :param ndk_home: Path to the Android NDK home directory if not in NDK_HOME or
                     NDK_HOME/bin is not in the path.
    """
    output_dir = scriptine.path("_out").joinpath(package_name)
    obj_dir = output_dir.joinpath("obj")
    libs_dir = output_dir.joinpath("libs")
    activity_dir = scriptine.path("activity")
    activity_jni_dir = activity_dir.joinpath("jni")
    android_mk_path = activity_jni_dir.joinpath("Android.mk")

    # Find out the right invocation for 'ndk-build' via ndk_home/bin, via
    # NDK_HOME/bin or via PATH, in this oder
    ndk_build_path = "ndk-build"
    if (ndk_home is None):
        ndk_home = os.environ.get('NDK_HOME', None)
    if (ndk_home is not None):
        ndk_build_path = scriptine.path(ndk_home).joinpath(ndk_build_path)

    if (debug):
        os.environ['MAKEFLAGS'] = "-d"

    # Delete temporaries
    scriptine.log.mark("Deleting old obj and lib files")
    obj_dir.rmtree(True)
    libs_dir.rmtree(True)

    # needs android-9 for NativeActivity, Android-12 for GLES2
    scriptine.log.mark("Performing the NDK build")
    cmds = [ndk_build_path,
            "V=1", "NDK_DEBUG=1", "NDK_LOG=1",
            "NDK_PROJECT_PATH=%s" % activity_jni_dir,
            "APP_BUILD_SCRIPT=%s" % android_mk_path,
            "APP_OPTIM=debug",
            "APP_ABI=armeabi-v7a",
            "APP_PLATFORM=android-12",
            "TARGET_PLATFORM=android-12",
            "NDK_LIBS_OUT=%s" % libs_dir,
            "NDK_OUT=%s" % obj_dir]
    check_call(cmds)

def ant_command(package_name = "Replayer", android_home = None, ant_home = None):
    """
    Build the ANT project and generate Android APK (requires the NDK and trace
    targets to have been built beforehand).
    Download ant from http://www.apache.org/dist/ant/binaries/

    See http://developer.android.com/reference/android/app/NativeActivity.html
    See http://stackoverflow.com/questions/14848042/running-the-ndk-native-activity-sample-from-a-command-line-ide
    See http://developer.android.com/tools/help/android.html

    :param package_name: Name of the package, com.example.<package_name>
    :param android_home: Path to the Android SDK root directory if not in the
                         ANDROID_HOME environment variable or ANDROID_HOME/bin
                         is not in the path
    :param ant_home: Path to the Ant build system directory if not in the path or
                     in the ANT_HOME environment variable
    """
    output_dir = scriptine.path("_out").joinpath(package_name)
    bin_dir = output_dir.joinpath("bin")

    # Delete any existing files
    bin_dir.rmtree(True)

    # Find out the right invocation for 'android' via android_home/bin, via
    # ANDROID_HOME/bin or via PATH, in this oder
    android_build_path = "android"
    if (android_home is None):
        android_home = os.environ.get('ANDROID_HOME', None)
    if (android_home is not None):
        android_build_path = scriptine.path(android_home).joinpath("tools", android_build_path)

    # Find out the right invocation for 'ant' via ant_home/bin, ant_HOME/bin
    # or via PATH, in this order
    ant_build_path = "ant"
    if (ant_home is None):
        ant_home = os.environ.get('ANT_HOME', None)
    if (ant_home is not None):
        # If there's a HOME, use HOME/bin
        ant_build_path = scriptine.path(ant_home).joinpath("bin", ant_build_path)

    # Generate a project
    # The target to use can be known via "android list targets"
    # See http://developer.android.com/tools/projects/projects-cmdline.html

    output_activity_dir = output_dir.joinpath("activity")
    input_activity_dir =  scriptine.path("activity")

    scriptine.log.mark("Deleting output activity directory")
    output_activity_dir.rmtree(True)

    scriptine.log.mark("Creating project on output activity directory")
    cmds = [android_build_path, "create", "project",
              "--path", output_activity_dir,
              "--name", package_name,
              "--target", "1",
              "--package", "com.example." + package_name,
              "--activity", package_name,
            ]
    check_call(cmds)

    # Delete unnecessary files in the created project
    scriptine.log.mark("Deleting unnecessary files from output activity directory")
    for d in ["bin", "libs", "src"]:
        output_activity_dir.joinpath(d).rmtree(True)


    scriptine.log.mark("Overwriting generic files from output activity directory")

    # Override the ant.properties file
    # XXX Should this do an android update project instead + the proper renaming?
    scriptine.path.copyfile(input_activity_dir.joinpath("ant.properties"),
                            output_activity_dir.joinpath("ant.properties"))

    # Override the AndroidManifest.xml file, renamign the package in the
    # source activity directory
    android_manifest_text = input_activity_dir.joinpath("AndroidManifest.xml").text()
    android_manifest_text = android_manifest_text.replace("native_activity", package_name)
    output_activity_dir.joinpath("AndroidManifest.xml").write_bytes(android_manifest_text)

    # Do the build
    scriptine.log.mark("Building activity project")
    cmds = [ ant_build_path,
            "-buildfile", output_activity_dir.joinpath("build.xml"),
            "-lib", output_dir.joinpath("libs"),
            "debug" ]
    check_call(cmds)

def install_command(package_name = "Replayer"):
    """
    Install the package on the device (requires the 'ant' target to have been built
    beforehand).

    :param package_name: Name of the package
    """
    output_dir = scriptine.path("_out").joinpath(package_name)

    # Uninstall completely to prevent certificate failures when over-installing
    # builds from a different machine
    scriptine.log.mark("Uninstalling application to prevent certificate failures")
    os_system("adb uninstall com.example.%s" % package_name)

    scriptine.log.mark("Installing application")
    apk_path = output_dir.joinpath("bin", "%s-debug.apk" % package_name)
    os_system("adb install -r %s" % apk_path)

def run_command(package_name = "Replayer", run_options = ""):
    """
    Run the package on the device (requires the 'install' target to have been built
    beforehand).

    :param package_name: Name of the package
    :param run_options: Options to pass to "am start", in quotation marks
    """
    output_dir = scriptine.path("_out").joinpath(package_name)

    scriptine.log.mark("Stopping application")
    os_system("adb shell am force-stop com.example.%s" % package_name)
    scriptine.log.mark("Clearing logcat")
    os_system("adb logcat -c")
    scriptine.log.mark("Starting application")
    os_system("adb shell am start --ez stop_motion false %(run_options)s "
              "com.example.%(package_name)s/android.app.NativeActivity" % {
                'run_options' : run_options,
                'package_name' : package_name,
              })
    scriptine.log.mark("Dumping logcat")
    os_system("adb logcat -v threadtime")

def all_command(targets="trace,ndk,ant,install,run",
                package_name = "Replayer",
                trace_filepath = "_out/test.gltrace.gz",
                trace_contexts = "0",
                deinline = False,
                ndk_debug = False,
                ndk_home = None,
                android_home = None,
                ant_home= None,
                run_options="",
                ):
    """
    Build all or selected targets.

    :param targets: Comma-separated list of targets to build (order is ignored,
                    the program will build them in the required order).
    :param package_name: Name of the package
    :param trace_filepath: Path to the OpenGL ES trace file
    :param trace_contexts: Index to the 0-based OpenGL ES context to trace
    :param deinline: Perform trace deinlining
    :param ndk_home: Path to the Android NDK home directory if not in NDK_HOME or
                     NDK_HOME/bin is not in the path.
    :param ndk_debug: Build NDK for debug
    :param android_home: Path to the Android SDK root directory if not in the
                         ANDROID_HOME environment variable or ANDROID_HOME/bin
                         is not in the path
    :param ant_home: Path to the Ant build system directory if not in the path or
                     in the ANT_HOME environment variable
    :param run_options: Comma-separated list of options to pass to "am start"
    """
    target_list = targets.split(",")
    if ("trace" in target_list):
        trace_command(package_name, trace_filepath, trace_contexts, deinline)
    if ("ndk" in target_list):
        ndk_command(package_name, ndk_home, ndk_debug)
    if ("ant" in target_list):
        ant_command(package_name, android_home, ant_home)
    if ("install" in target_list):
        install_command(package_name)
    if ("run" in target_list):
        run_command(package_name, run_options)

if (__name__ == "__main__"):
    scriptine.run()
