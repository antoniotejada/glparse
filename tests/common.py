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

import nose

import errno
import filecmp
import logging
import os
import sys
import types

# Inform Nose that the tests can be split across processes
_multiprocess_can_split_ = True

logger = logging.getLogger(__name__)

def remove(filepath):
    """!
    Identical to os.remove but ignores non-existing files
    """
    try:
        os.remove(filepath)
    except OSError as e:
        if (e.errno != errno.ENOENT):
            raise

def makedirs(dirname):
    """!
    Identical to os.makedirs, but ignores already existing exceptions.
    """

    try:
        os.makedirs(dirname)
    except OSError as e:
        # ignore already existing path exceptions
        if e.errno != errno.EEXIST:
            raise

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

def declare_per_file_functions(filepaths, modulename, test_single_file):
    """!
    Declare as many test functions as files
    This allows Nose to run them in parallel and give per-file errors
    """

    # Sort the paths alphabetically to guarantee all the processes get the same
    # filename-to-function-name mapping

    for index, filepath in enumerate(filepaths):
        # Create a functor that captures the filename argument (can't use a
        # lambda directly because it doesn't capture the value of the argument
        # but the address)
        fn_name = "test_file_%d" % index
        filename = os.path.basename(filepath)

        logger.info("Creating test function %s for file %s" % (fn_name, filename))

        wrapper = types.FunctionType(test_single_file.func_code,
                                     test_single_file.func_globals,
                                     fn_name,
                                    (filename,),
                                     test_single_file.func_closure)

        # Add it to the module
        setattr(sys.modules[modulename], fn_name, wrapper)

def invoke_per_file_functions(modulename): # pragma: no cover
    import inspect

    # Run all the testXXXXX functions, unless decorated with @nose.tools.nottest
    testFunctions = inspect.getmembers(sys.modules[modulename],
                                       predicate=lambda obj: inspect.isfunction(obj) and
                                                             obj.__name__.startswith("test") and
                                                             (not hasattr(obj, "__test__") or obj.__test__))
    print testFunctions
    logger.debug("%d test functions found" % len(testFunctions))
    for name, function in testFunctions:
        logger.info("Testing function %s" % name)
        function()

    # Run all the testXXXXX methods of the TestXXXX classes, unless decorated with @nose.tools.nottest
    try:

        testClasses = inspect.getmembers(sys.modules[modulename],
                                       predicate=lambda obj: inspect.isclass(obj) and
                                                             obj.__name__.startswith("test") and
                                                            (not hasattr(obj, "__test__") or obj.__test__))

        logger.debug("%d test classes found" % len(testClasses))
        for className, cls in testClasses:
            test = cls()

            testMethods = inspect.getmembers(Test,
                                             predicate=lambda obj: inspect.ismethod(obj) and
                                                                   obj.__name__.startswith("test") and
                                                                  (not hasattr(obj, "__test__") or obj.__test__))

            logger.debug("%d test methods found in class %s" % (len(testMethods), className))
            for methodName, method in testMethods:
                logger.debug("Testing method %s of class %s" % (methodName, className))
                test.setUp()
                method(test)
                test.tearDown()

    except NameError:
        logger.debug("No running methods No Test class found")

