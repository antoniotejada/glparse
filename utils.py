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

# XXX Note using compression will cause corrupt files if the program is aborted
#     with ctrl+break while saving (ctrl+c seems to work fine)
def xopen(filepath, mode = 'rb', compresslevel=9):
    # Guess from the filename whether to decompress or not
    if (filepath.endswith(".gz")):
        compressed = True
    else:
        compressed = False

    if (compressed):
        import gzip

        # Gzipfile recommends compressed files to force binary for compatibility
        newmode = mode
        if ('b' not in newmode):
            newmode += 'b'
        # Remove universal newline flags, not supported by gzip
        # Note opening for append produces the unexpected effect of creting a
        # new gzip member, rather than resuming the previous compression.
        newmode = newmode.replace('U', '')

        file = gzip.open(filepath, newmode, compresslevel)

    else:
        import __builtin__
        file = __builtin__.open(filepath, mode)

    return file

def xgetsize(filepath):
    # Guess from the filename whether to decompress or not
    if (filepath.endswith(".gz")):
        compressed = True
    else:
        compressed = False

    if (compressed):
        # Get the size reading the ISIZE component, see
        # http://www.gzip.org/zlib/rfc-gzip.html#header-trailer
        # Note this assumes there's only one component in the gzip file
        # and that the size is less than 2GB
        import struct
        with open(filepath, "rb") as f:
            f.seek(-4, os.SEEK_END)
            size = struct.unpack("<I", f.read(4))[0]
    else:
        size = os.path.getsize(filepath)

    return size
