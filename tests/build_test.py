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

import sys
# XXX This is so __main__ can find build.py and the unit tests can be debugged
#     by running __main__. Is there a better way? Can unit tests be debugged from
#     nose itself?
if __name__ == '__main__':
    sys.path.append('..')

import nose

import errno
import glob
import logging
import os
import shutil

import common
import build

logger = logging.getLogger(__name__)

TEST_FILES_FILEDIR = "build"
OUTPUT_FILEDIR = "_out"

@nose.tools.nottest
def test_single_file(filename):
    """!
    Test a single file given by the filename
    """

    logger.info("Starting test for file %s" % filename)

    outFiledir = os.path.join(TEST_FILES_FILEDIR, OUTPUT_FILEDIR)
    oldOutFiledir = os.path.join(outFiledir, "old", filename)
    newOutFiledir = os.path.join(outFiledir, "new", filename)

    compare_only = False
    if (not compare_only):
        # Re-create the new dirs, deleting existing content
        try:
            shutil.rmtree(newOutFiledir)
        except OSError as e:
            if (e.errno != errno.ENOENT):
                raise
        common.makedirs(newOutFiledir)

        package_name = os.path.splitext(filename)[0]
        # Package names cannot contain hyphens, dots
        package_name = package_name.replace("-", "_")
        package_name = package_name.replace(".", "_")
        trace_filepath = os.path.join(TEST_FILES_FILEDIR, filename)
        # Don't invoke build as a library since the ant build requires the
        # activity to be a subdirectory
        # XXX Note this doesn't test "install" or "run"
        build.all_command(targets="trace,ndk,ant",
                          package_name = package_name,
                          trace_filepath = trace_filepath,
                          # XXX This should be taken from some per-test config
                          #     option
                          trace_contexts = None,
                          # XXX Deinline is broken, removes braces, create a test,
                          #     fix and activate here
                          deinline = False,
                          ndk_debug = False,
                          ndk_home = r"c:\android-ndk-r10d",
                          ant_home = r"c:\apache-ant-1.9.4",
                          android_home = r"c:\android-sdk",
                          run_options = "",
                          output_dir = newOutFiledir,
                          activity_dir = r"..\activity")

    # Remove bin directory to prevent hits due to apk mismatch
    # XXX Investigate why apks mismatch
    shutil.rmtree(os.path.join(newOutFiledir, "bin"))
    # Remove object files to prevent hits due to mismatch
    # XXX Probably due to gcc random seed
    # http://stackoverflow.com/questions/14653874/how-to-produce-deterministic-binary-output-with-g
    shutil.rmtree(os.path.join(newOutFiledir, "obj"))
    shutil.rmtree(os.path.join(newOutFiledir, "libs"))

    # Do non-shallow directory comparison
    common.dircmp(oldOutFiledir, newOutFiledir)

filepaths = glob.glob(os.path.join(TEST_FILES_FILEDIR, "*.gz"))
filepaths += glob.glob(os.path.join(TEST_FILES_FILEDIR, "*.gltrace"))
if __name__ == '__main__':
    for l in [logging.getLogger("build"), logging.getLogger(__name__),
              logging.getLogger('common')]:
        l.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("%(asctime).19s %(levelname)s:%(filename)s(%(lineno)d) [%(threadName)s]: %(message)s")
        console_handler.setFormatter(console_formatter)
        l.addHandler(console_handler)

    logging.getLogger('build').setLevel(logging.INFO)
    logging.getLogger('__main__').setLevel(logging.INFO)

common.declare_per_file_functions(filepaths, __name__, test_single_file)

if (__name__ == '__main__'):
    common.invoke_per_file_functions(__name__)