@echo off
setlocal
title Tests
set PYTHONDIR=c:\Python27
set PYTHONPATH=%PYTHONDIR%\python.exe
set NOSEPATH=%PYTHONDIR%\Scripts\nosetests.exe
set NOSEOPTS=""

rem nose debugging options
rem Nose requires "pip install nose"
rem set NOSEOPTS=--detailed-errors --debug=nose --nologcapture --stop --verbosity=4 --nocapture

rem test debugging options
rem set NOSEOPTS=--detailed-errors --debug=nose --nologcapture --stop --verbosity=4 --nocapture

rem normal options, stop on first error, do INFO level logging
set NOSEOPTS=--detailed-errors --stop --logging-level=INFO

rem multiprocess options, use as many as CPUs
rem requires invoking the tests with
rem "%PYTHONPATH%" -c "import sys; sys.path.append('..'); import nose; nose.main()" 
rem Note multiprocess doesn't work with coverage (errors out)
rem instead of the coverage plugin, you have to use coverage.py directly with 
rem --parallel-mode and combine later (https://groups.google.com/forum/#!topic/nose-users/wQ205ruxtCA)
rem But that still doesn't work because coverage.py requires to be invoked with 
rem a script name rather than the -c "instructions", which again breaks nose's 
rem --parallel mode
rem Use a big timeout because some files take a long time to deinline (more than
rem 30s, normally when debug logging is enabled)
set NOSEOPTS=%NOSEOPTS% --processes=-1 --process-timeout=300

rem all modules coverage
rem Coverage requires "pip install coverage"
rem set NOSEOPTS=%NOSEOPTS% --with-coverage --cover-html --cover-html-dir=_out\cover --cover-tests --cover-erase --cover-branches --cover-package=deinline

rem deinline module coverage
rem set NOSEOPTS=%NOSEOPTS% --with-coverage --cover-html --cover-html-dir=_out\cover --cover-tests --cover-erase --cover-branches --cover-package=deinline

rem display collected tests with
rem "%NOSEPATH%" ..\ -vvv --collect-only 2>&1 | find /I ": Preparing"
rem or (parallel)
rem "%PYTHONPATH%" -c "import sys; sys.path.append('..'); import nose; nose.main()"  -vvv --collect-only 2>&1 | find /I ": Add test"

rem this invocation doesn't work with multiprocess, invoke nose directly
rem "%NOSEPATH%" ..\ %NOSEOPTS% %*

"%PYTHONPATH%" -c "import sys; sys.path.append('..'); import nose; nose.main()" %NOSEOPTS% %*

pause