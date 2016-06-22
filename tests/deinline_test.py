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

import errno
import filecmp
import glob
import logging
import os
import string
import types

import deinline

# Inform Nose that the tests can be split across processes
_multiprocess_can_split_ = True

logger = logging.getLogger(__name__)

def makedirs(dirname):
    """!
    Identical to os.makedirs, but ignores already existing exceptions.
    """

    try:
        os.makedirs(dirname)
    except OSError, e:
        # ignore already existing path exceptions
        if e.errno != errno.EEXIST:
            raise

def count_lines_between_braces(lines):
    """!
    Count the number of lines between braces
    """

    braceNestingLevel = 0
    lineCount = 0

    for line in lines:
        strippedLine = line.strip()
        if (strippedLine == ""):
            pass
        elif (strippedLine == "{"):
            braceNestingLevel += 1
        elif (strippedLine == "}"):
            braceNestingLevel -= 1
        elif (braceNestingLevel > 0):
            lineCount += 1

        assert(braceNestingLevel >= 0)

    assert(braceNestingLevel == 0)

    return lineCount

def declare_per_file_functions():
    """!
    Declare as many test functions as files
    This allows Nose to run them in parallel and give per-file errors
    """

    SNIPPETS_FILEDIR = "deinline"
    OUTPUT_FILEDIR = "_out"

    def test_single_file(filename):
        """!
        Test a single file given by the filename
        """

        logger.info("Starting test for file %s" % filename)

        outFilename = "%s.out" % filename
        filepath = os.path.join(SNIPPETS_FILEDIR, filename)
        outFilepath = os.path.join(SNIPPETS_FILEDIR, outFilename)
        newOutFiledir = os.path.join(SNIPPETS_FILEDIR, OUTPUT_FILEDIR)
        newOutFilepath = os.path.join(newOutFiledir, outFilename)

        with open(filepath, "rb") as f:
            lines = f.readlines()
            srcLineCount = count_lines_between_braces(lines)

        lines = deinline.deinline(filepath)
        dstLineCount = count_lines_between_braces(lines)

        makedirs(newOutFiledir)

        with open(newOutFilepath, "w") as f:
            lines = ["// Src lines %d" % srcLineCount,
                     "// Dest lines %d" % dstLineCount] + lines
            f.write(string.join(lines, "\n"))

        assert(filecmp.cmp(outFilepath, newOutFilepath, False))

    # Sort the paths alphabetically to guarantee all the processes get the same
    # filename-to-function-name mapping

    filepaths = glob.glob(os.path.join(SNIPPETS_FILEDIR, "*.c"))

    for index, filepath in enumerate(filepaths):
        # Create a functor that captures the filename argument (can't use a
        # lambda directly because it doesn't capture the value of the argument
        # but the address)
        fn_name = "test_file_%d" % index
        filename = os.path.basename(filepath)

        logger.debug("Creating test function %s for file %s" % (fn_name, filename))

        wrapper = types.FunctionType(test_single_file.func_code,
                                     test_single_file.func_globals,
                                     fn_name,
                                    (filename,),
                                     test_single_file.func_closure)

        # Add it to the module
        setattr(sys.modules[declare_per_file_functions.__module__], fn_name, wrapper)


# Note on multiprocess this function runs once on each test process
declare_per_file_functions()

if __name__ == '__main__':
    import inspect
    for l in [logging.getLogger("deinline"), logging.getLogger(__name__)]:
        # deinline.py is very verbose, set logging to INFO level
        l.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("%(asctime).19s %(levelname)s:%(filename)s(%(lineno)d) [%(threadName)s]: %(message)s")
        console_handler.setFormatter(console_formatter)
        l.addHandler(console_handler)

    # Run all the testXXXXX functions
    testFunctions = inspect.getmembers(sys.modules['__main__'],
                                       predicate=lambda obj: inspect.isfunction(obj) and obj.__name__.startswith("test"))
    logger.debug("%d test functions found" % len(testFunctions))
    for name, function in testFunctions:
        logger.info("Testing function %s" % name)
        function()

    # Run all the testXXXXX methods of the TestXXXX classes
    try:

        testClasses = inspect.getmembers(sys.modules['__main__'],
                                       predicate=lambda obj: inspect.isclass(obj) and obj.__name__.startswith("test"))

        logger.debug("%d test classes found" % len(testClasses))
        for className, cls in testClasses:
            test = cls()

            testMethods = inspect.getmembers(Test,
                                             predicate=lambda obj: inspect.ismethod(obj) and obj.__name__.startswith("test"))

            logger.debug("%d test methods found in class %s" % (len(testMethods), className))
            for methodName, method in testMethods:
                logger.debug("Testing method %s of class %s" % (methodName, className))
                test.setUp()
                method(test)
                test.tearDown()

    except NameError:
        logger.debug("No running methods No Test class found")

