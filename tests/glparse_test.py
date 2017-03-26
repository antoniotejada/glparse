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
# XXX This is so __main__ can find glparse.py and the unit tests can be debugged
#     by running __main__. Is there a better way? Can unit tests be debugged from
#     nose itself?
if __name__ == '__main__':
    sys.path.append('..')

import nose

import filecmp
import glob
import logging
import os
import shutil

import common
import glparse

logger = logging.getLogger(__name__)

TEST_FILES_FILEDIR = "glparse"
OUTPUT_FILEDIR = "_out"

def dircmp(d1, d2):
    """!
    Non-shallow directory comparison, asserts in case of mismatch
    """
    logger.debug("dircmp %s vs. %s" % (d1, d2))
    d = filecmp.dircmp(d1, d2)
    assert(len(d.left_only) == 0)
    assert(len(d.right_only) == 0)

    # Check that every file is binary equal
    for filename in d.common_files:
        f1 = os.path.join(d1, filename)
        f2 = os.path.join(d2, filename)
        logger.debug("cmp %s vs. %s" % (f1, f2))
        assert(filecmp.cmp(f1, f2, False))

    # Check that the subdirs are binary equal
    for dirname in d.subdirs:
        dircmp(os.path.join(d1, dirname), os.path.join(d2, dirname))

@nose.tools.nottest
def test_single_file(filename):
    """!
    Test a single file given by the filename
    """

    logger.info("Starting test for file %s" % filename)

    outFilename = "trace.inc"
    filepath = os.path.join(TEST_FILES_FILEDIR, filename)
    outFiledir = os.path.join(TEST_FILES_FILEDIR, OUTPUT_FILEDIR)
    oldOutFiledir = os.path.join(outFiledir, "old", filename)
    newOutFiledir = os.path.join(outFiledir, "new", filename)
    newOutFilepath = os.path.join(newOutFiledir, outFilename)

    compare_only = False
    if (not compare_only):
        # Re-create the new dirs, deleting existing content
        shutil.rmtree(newOutFiledir)
        common.makedirs(newOutFiledir)

        output_dir = newOutFiledir
        assets_dir = os.path.join(newOutFiledir, "assets")
        gl_contexts_to_trace = [0]
        # XXX How is this going to test future config parameters, where get them from?
        #     filename? config file?
        lines = glparse.glparse(filepath, output_dir, assets_dir, gl_contexts_to_trace)

        with open(newOutFilepath, "w") as f:
            for line in lines:
                f.writelines([line, "\n"])

    # Do non-shallow directory comparison
    dircmp(oldOutFiledir, newOutFiledir)

filepaths = glob.glob(os.path.join(TEST_FILES_FILEDIR, "*.gz"))
filepaths += glob.glob(os.path.join(TEST_FILES_FILEDIR, "*.gltrace"))
if __name__ == '__main__':
    for l in [logging.getLogger("glparse"), logging.getLogger(__name__),
              logging.getLogger('common')]:
        l.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("%(asctime).19s %(levelname)s:%(filename)s(%(lineno)d) [%(threadName)s]: %(message)s")
        console_handler.setFormatter(console_formatter)
        l.addHandler(console_handler)

    logging.getLogger('glparse').setLevel(logging.INFO)
    logging.getLogger('__main__').setLevel(logging.INFO)

common.declare_per_file_functions(filepaths, __name__, test_single_file)

if (__name__ == '__main__'):
    common.invoke_per_file_functions(__name__)