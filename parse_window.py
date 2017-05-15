import datetime
import glob
import logging
import re
import time

logger = logging.getLogger(__name__)

logging_format = "%(asctime).23s %(levelname)s:%(filename)s(%(lineno)d) [%(thread)d]: %(message)s"
logger_handler = logging.StreamHandler()
logger_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(logger_handler)
logger.setLevel(logging.INFO)

filepaths = list(glob.glob("perf/deinline*b.log"))
# Name is like perf\deinline1000b.log, perf\deinline1b.log, sort so 1b appears
# before 1000b
filepaths = sorted(filepaths, key=lambda f: int(filter(str.isdigit, f)))
for filepath in filepaths:
    with open(filepath) as f:
        # Get the first and last lines of the file
        # 2017-05-07 00:34:49,934 INFO:deinline.py(1379) [8572]: Starting
        # ..
        # 2017-05-07 02:16:25,496 INFO:deinline.py(1516) [8572]: Initial code lines 388484 final 17029 compression ratio 22.813
        time_pattern = "%Y-%m-%d %H:%M:%S,%f"

        lines = f.readlines()

        first = lines[0]
        start = time.strptime(first[:23], time_pattern)

        last = lines[-1]
        m = re.match(r".*Initial code lines (\d+) final (\d+) compression ratio (\d+\.\d+)", last)
        window_size = int(filter(str.isdigit, filepath))
        initial = int(m.group(1))
        final = int(m.group(2))
        ratio = float(m.group(3))
        end = time.strptime(last[:23], time_pattern)

        print "%s\t%s\t%f\t%d\t%d\t%f" %(filepath, window_size, time.mktime(end) - time.mktime(start), initial, final, ratio)
