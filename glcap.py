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
Utility to capture a GL trace
Use with:
    adb shell am force-stop %PACKAGE%
    adb shell am start --opengl-trace %PACKAGE%/%ACTIVITY%
    glcap.py --trace-file=my.gltrace --store-textures

References:

https://android.googlesource.com/platform/frameworks/native/+/jb-dev/opengl/libs/GLES_trace/
https://android.googlesource.com/platform/frameworks/native/+/jb-dev/opengl/libs/GLES_trace/src/gltrace_transport.cpp
https://android.googlesource.com/platform/frameworks/native/+/jb-dev/opengl/libs/GLES_trace/src/gltrace_eglapi.cpp
https://android.googlesource.com/platform/sdk/+/eabd472/eclipse/plugins/com.android.ide.eclipse.gldebugger/src/com/android/ide/eclipse/gltrace/TraceCommandWriter.java
https://android.googlesource.com/platform/sdk/+/eabd472/eclipse/plugins/com.android.ide.eclipse.gldebugger/src/com/android/ide/eclipse/gltrace/TraceFileWriter.java
https://android.googlesource.com/platform/sdk/+/f51d3b0/eclipse/plugins/com.android.ide.eclipse.gldebugger/src/com/android/ide/eclipse/gltrace/CollectTraceAction.java

1. GL tracing opens a unix domain socket named "gltrace"
2. DDMS forwards to port 6039 (adb forward tcp:6039 localabstract:gltrace )
2. command options are sent to the socket
    private static final int READ_FB_ON_EGLSWAP_BIT = 0;
    private static final int READ_FB_ON_GLDRAW_BIT = 1;
    private static final int READ_TEXTURE_DATA_ON_GLTEXIMAGE_BIT = 2;
3. trace is read from the socket
    Each packet has a 4-byte little endian header and the payload in protobuff format
4. trace is written to the file
    The trace is written as network-order header plus payload
"""

import errno
import os
import socket
import struct

import scriptine

import utils

#
# scriptine.shell is missing from the manifest in 0.2.0, provide our own shell
# functions (this is probably fixed on 0.2.0a2, but not available on pip)
#
@scriptine.misc.dry_guard
def os_system(cmd):
    if (os.system(cmd) != 0):
        raise Exception("Exception running command %s" % repr(cmd))

def socket_recv(sock, buffer_size):
    """!
    Really blocking recv
    """
    buffer_data = ""
    while (buffer_size != 0):
        b = sock.recv(buffer_size)
        if (b == ""):
            raise OSError(errno.EPIPE, 'Broken pipe')
        buffer_size -= len(b)
        buffer_data = buffer_data + b

    return buffer_data


def capture_command(trace_filepath = "glcap.gltrace",
                    store_fb_on_swap = False,
                    store_fb_on_draw = False,
                    store_textures = False,
                    gltrace_port = 6039):
    """
    Capture a GL trace into a .gltrace file with the given capture options.
    The application must be started before invoking the capture.

    :param trace_filepath: Path to the destination GL trace. Terminate in .gz
                           for compression
    :param store_fb_on_swap: Store the framebuffer contents in the trace on every
                           eglSwapBuffers call
    :param store_fb_on_draw: Store the framebuffer contents in the trace on every
                           glDrawXXX call
    :param store_textures: Store the texture contents on everly glTexImageXX call
    :param gltrace_port: Temporary port to forward gltrace's unix domain socket to.
    """

    GLTRACE_PORT = int(gltrace_port)
    GLTRACE_HOST = "127.0.0.1"
    GLTRACE_UNIX_DOMAIN_SOCKET_NAME = "gltrace"

    READ_FB_ON_EGLSWAP_MASK = 2 ** 0
    READ_FB_ON_GLDRAW_MASK = 2 ** 1
    READ_TEXTURE_DATA_ON_GLTEXIMAGE_MASK = 2 ** 2

    flags = 0

    if (store_fb_on_swap):
        flags += READ_FB_ON_EGLSWAP_MASK
    if (store_fb_on_draw):
        flags += READ_FB_ON_GLDRAW_MASK
    if (store_textures):
        flags += READ_TEXTURE_DATA_ON_GLTEXIMAGE_MASK

    # Forward socket from unix domain to tcp
    os_system("adb forward tcp:%d localabstract:%s" % (GLTRACE_PORT, GLTRACE_UNIX_DOMAIN_SOCKET_NAME))

    # Open forwarded socket
    trace_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    trace_socket.connect((GLTRACE_HOST, GLTRACE_PORT))

    # Write control options packet (textures, swapbuffer, etc)
    # This is length+payload, both in network order
    trace_socket.send(struct.pack("!i", 4))
    trace_socket.send(struct.pack("!i", flags))

    # Read the trace
    with utils.xopen(trace_filepath, "wb") as f:
        while (True):
            try:
                packet_length = socket_recv(trace_socket, 4)
            except OSError as e:
                if (e.errno != errno.EPIPE):
                    raise
                else:
                    break

            # Packet length is read in little endian
            packet_length = struct.unpack("<I", packet_length)
            packet_length = packet_length[0]
            packet_data = socket_recv(trace_socket, packet_length)

            # Packet length is written to file in network order
            f.write(struct.pack("!i", packet_length))
            f.write(packet_data)

if (__name__ == "__main__"):
    scriptine.run()