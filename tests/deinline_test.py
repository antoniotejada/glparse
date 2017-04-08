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
# XXX This is so __main__ can find deinline.py and the unit tests can be debugged
#     by running __main__. Is there a better way? Can unit tests be debugged from
#     nose itself?
if __name__ == '__main__':
    sys.path.append('..')

import nose

import filecmp
import glob
import logging
import os

import common
import deinline

# Inform Nose that the tests can be split across processes
_multiprocess_can_split_ = True

logger = logging.getLogger(__name__)

def count_lines_between_braces(lines):
    """!
    Count the number of non-empty lines between top level braces
    """

    braceNestingLevel = 0
    lineCount = 0

    for line in lines:
        line = line.rstrip()
        topLevelNestStarts = False
        if (line == "{"):
            if (braceNestingLevel == 0):
                topLevelNestStarts = True
            braceNestingLevel += 1

        elif (line == "}"):
            braceNestingLevel -= 1

        line = line.strip()
        # Ignore blank lines
        if (not topLevelNestStarts and (line != "") and (braceNestingLevel > 0)):
            lineCount += 1

        assert(braceNestingLevel >= 0)

    assert(braceNestingLevel == 0)

    return lineCount

TEST_FILES_FILEDIR = "deinline"
OUTPUT_FILEDIR = "_out"

@nose.tools.nottest
def test_single_file(filename):
    """!
    Test a single file given by the filename
    """

    logger.info("Starting test for file %s" % filename)

    filepath = os.path.join(TEST_FILES_FILEDIR, filename)
    outFiledir = os.path.join(TEST_FILES_FILEDIR, OUTPUT_FILEDIR)
    oldOutFilepath = os.path.join(outFiledir, "old", filename)
    newOutFiledir = os.path.join(outFiledir, "new")
    newOutFilepath = os.path.join(newOutFiledir, filename)

    with open(filepath, "rb") as f:
        lines = f.readlines()
        srcLineCount = count_lines_between_braces(lines)

    lines = deinline.deinline(filepath)
    dstLineCount = count_lines_between_braces(lines)

    # Create the new dir if necessary, delete old content
    common.remove(newOutFilepath)
    common.makedirs(newOutFiledir)

    with open(newOutFilepath, "w") as f:
        lines = ["// Src lines %d" % srcLineCount,
                 "// Dest lines %d" % dstLineCount] + lines
        for line in lines:
            f.writelines([line, "\n"])

    assert(filecmp.cmp(oldOutFilepath, newOutFilepath, False))

# Note on multiprocess this function runs once on each test process
filepaths = glob.glob(os.path.join(TEST_FILES_FILEDIR, "*.c"))

if __name__ == '__main__':
    for l in [logging.getLogger("deinline"), logging.getLogger(__name__),
              logging.getLogger('common')]:
        l.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("%(asctime).19s %(levelname)s:%(filename)s(%(lineno)d) [%(threadName)s]: %(message)s")
        console_handler.setFormatter(console_formatter)
        l.addHandler(console_handler)

    logging.getLogger("common").setLevel(logging.DEBUG)

common.declare_per_file_functions(filepaths, __name__, test_single_file)

if (__name__ == '__main__'):
    common.invoke_per_file_functions(__name__)
