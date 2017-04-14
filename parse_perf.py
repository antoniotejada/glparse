import glob
import logging
import os
import re
import string

logger = logging.getLogger(__name__)

device_to_gpu = {
    'grouper' : "Tegra 3",
    'brouper' : "Tegra 3r",
    'roth' : "Tegra 4",
    'broth' : "Tegra 4r",
    'proth' : "Tegra 4s",
    'heroqlteatt' : "Adreno 530",
    'ariel' : "PVR G6200",
    'ford' : "Mali 450",
    'kodiak' : "Adreno 320"
}

logging_format = "%(asctime).23s %(levelname)s:%(filename)s(%(lineno)d) [%(thread)d]: %(message)s"
logger_handler = logging.StreamHandler()
logger_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(logger_handler)
logger.setLevel(logging.INFO)

min_frame = 430
max_frame = 800
for res in ["720x1280", "1080x1920", "2160x3840"]:
    print res
    stats = {}
    for filepath in glob.glob("*-%s-perf.log" % res):
        logger.debug(filepath)
        filename = os.path.basename(filepath)
        m = re.match(r"(\w+)-(\w+)-\d+x\d+-perf.log", filename)
        device = m.group(1)
        sync_type = m.group(2)
        gpu = "%s-%s" % (device_to_gpu[device], sync_type)
        with open(filepath, "r") as f:
            lines = f.readlines()
            stats[gpu] = []
            for line in lines:
                m = re.match(r".*Swap \d+ time is (\d+\.\d+)ms.*", line)

                if (m is not None):
                    logger.debug("frame %d: %s" % (len(stats[gpu]), line.strip()))
                    stats[gpu].append(float(m.group(1)))

    keys = stats.keys()
    nframes = max([len(l) for l in stats.values()])
    del_keys = []
    for key in stats.keys():
        if (len(stats[key]) != nframes):
            print "removing %s, found %d frames instead of %d" % (key, len(stats[key]), nframes)
            del_keys.append(key)

    for key in del_keys:
        del stats[key]


    for key in sorted(stats.keys()):
        filtered_stats = stats[key][min_frame:max_frame+1]
        print "%s (%3.2f)\t" % (key, sum(filtered_stats) / len(filtered_stats)),
    print

    for frame in xrange(len(stats[stats.keys()[0]])):
        if ((frame >= min_frame) and (frame <= max_frame)):
            try:
                for gpu in sorted(stats.keys()):
                    print "%f\t" % stats[gpu][frame],
                print
            except IndexError as e:
                print "Corrupted frame %d for file %s" % (frame, filepath)
                break
