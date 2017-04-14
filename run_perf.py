import logging
import subprocess
import re
import sys
import time

logger = logging.getLogger(__name__)

def adb(cmd, serial=None):
    params = ""
    if (serial is not None):
        params = "-s %s" % serial

    logger.debug("%s: -> %s" % (serial, cmd))
    out = subprocess.check_output("adb %s %s" % (params, cmd))

    logger.debug("%s: <- %s" % (serial, out))

    return out

def adb_devices():
    """!
    @return array of dicts with fields 'serial', 'type'.
            If 'type' is 'device', it also has fields 'product', 'model' and 'device'.
    """
    lines = adb("devices -l")
    lines = lines.splitlines()

    devices = []
    # Ignore the first line which contains the header and the last line which is empty
    # List of devices attached
    # 015d2ea4ce1ffc0c       device product:nakasi model:Nexus_7 device:grouper
    # ...
    for line in lines[1:-1]:
        line = re.split(r"[\t :]+", line)
        print line
        device = {'serial' : line[0],
                  'type' : line[1]}
        if (device['type'] == 'device'):
            device.update({
                  'product' : line[3],
                  'model' : line[5],
                  'device': line[7]}
            )
        devices.append(device)

    return devices

def adb_shell(cmd, serial=None):
    out = adb("shell \"%s\"" % cmd, serial)

    return out

def perform_test(device_name, serial, egl_width, egl_height, egl_swapbuffers_sync, egl_pbuffer_bit, ):
    # Stop any previous execution
    logger.info("Stopping existing execution for %s" % PACKAGE)
    adb_shell("am force-stop %s" % PACKAGE, serial)

    # Clear logcat
    adb("logcat -c", serial)

    params = ""
    params += " --ez stop_motion false --ei egl_depth_size 16 "
    params += " --ei egl_red_size 8 --ei egl_green_size 8 --ei egl_blue_size 8 --ei egl_alpha_size 8 "
    params += " --ei egl_width %d --ei egl_height %d " % (egl_width, egl_height)
    params += " --ei egl_swapbuffers_sync %d " % egl_swapbuffers_sync
    params += " --ez egl_pbuffer_bit %s " % ("true" if egl_pbuffer_bit else "false")

    adb_shell("am start %s %s/%s" % (params, PACKAGE, ACTIVITY), serial)

    # read from logcat until the last frame is received
    pipe = subprocess.Popen("adb -s %s logcat -v threadtime" % serial, stdout = subprocess.PIPE)

    try:
        filepath = "%s-sync_%d_pb_%s_0-%dx%d-perf.log" % (device_name,
                                      egl_swapbuffers_sync,
                                      "true" if egl_pbuffer_bit else "false",
                                       egl_width, egl_height)

        logger.info("Writing log to %s" % filepath)

        out = open(filepath, "w")
        while True:
            # XXX Do a timeot
            line = pipe.stdout.readline()
            out.write(line)
            if ((line.find("end of replay, exiting") != -1) or
                # XXX This could do a regexp search, but this is enough for now
                ## 04-11 02:49:45.544   573  3596 I ActivityManager: Process com.example.sonicdash_stage1 (pid 10420) has died
                (line.find("ActivityManager: Process com.example.sonicdash_stage1 (pid") != -1) or
                # Tegra3 gives this on every frame instead of failing to create
                # the surface
                # GLConsumer: [com.example.sonicdash_stage1/android.app.NativeActivity] bindTextureImage: error binding external image: 0x502
                (line.find("GLConsumer: [com.example.sonicdash_stage1/android.app.NativeActivity] bindTextureImage: error binding external image: 0x502") != -1)
                ):
                # XXX That single error is not enough, should this look for win death?
                # Sleep for the process to end
                # XXX This could also "ps" instead and wait for it to finish
                break
    finally:
        pipe.kill()

    return

if (__name__ == "__main__"):
    logging_format = "%(asctime).23s %(levelname)s:%(filename)s(%(lineno)d) [%(thread)d]: %(message)s"
    logger_handler = logging.StreamHandler()
    logger_handler.setFormatter(logging.Formatter(logging_format))
    logger.addHandler(logger_handler)
    logger.setLevel(logging.DEBUG)

    devices = adb_devices()
    print devices

    device_name = sys.argv[1]

    serial = [device['serial'] for device in devices if (device['device'] == device_name) ][0]

    PACKAGE="com.example.sonicdash_stage1"
    ACTIVITY="android.app.NativeActivity"
    APK_FILEPATH=R"_out\sonicdash_stage1\bin\sonicdash_stage1-debug.apk"

    # Stop any previous execution
    logger.info("Stopping existing execution for %s" % PACKAGE)
    adb_shell("am force-stop %s" % PACKAGE, serial)

    do_installation = False
    if (do_installation):
        # Uninstall
        logger.info("Uninstalling package %s" % PACKAGE)
        adb("uninstall %s" % PACKAGE, serial)
        # Install
        logger.info("Installing apk %s" % APK_FILEPATH)
        adb("install -r %s" % APK_FILEPATH, serial)

    resolutions = [ (720, 1280), (1080, 1920), (2160, 3840) ]
    egl_swapbuffers_syncs = [ 0, 1, 2, 3]
    egl_swapbuffers_syncs = [ 0 ]

    for egl_width, egl_height in resolutions:

        for egl_swapbuffers_sync in egl_swapbuffers_syncs:
            if (egl_swapbuffers_sync == 0):
                logger.info("Running test for resolution %dx%d and frontbuffer" % (egl_width, egl_height))
                perform_test(device_name, serial, egl_width, egl_height, 0, False)
            logger.info("Running test for resolution %dx%d and pbuffer sync_type %d" % (egl_width, egl_height, egl_swapbuffers_sync))
            perform_test(device_name, serial, egl_width, egl_height, egl_swapbuffers_sync, True)