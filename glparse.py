#!/usr/bin/python

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

# https://android.googlesource.com/platform/frameworks/native/+/master/opengl/libs/GLES_trace/DESIGN.txt
# https://android.googlesource.com/platform/frameworks/native/+/master/opengl/libs/GLES_trace/gltrace.proto

# https://cvs.khronos.org/svn/repos/ogl/trunk/doc/registry/public/api/gl.xml

import ctypes
import logging
import re
import string
import struct
import sys
import xml.etree.ElementTree

logger = logging.getLogger(__name__)

PROTOBUFF_DIR = "external/google"
sys.path.append(PROTOBUFF_DIR)
try:
    import gltrace_pb2
except ImportError:
    print ("The protobuff gltrace Python module %s/gltrace_pb2.py doesn't exist, generate it with\n"
           "  %s/protoc %s/gltrace.proto --python_out=%s" %
              (PROTOBUFF_DIR, PROTOBUFF_DIR, PROTOBUFF_DIR, PROTOBUFF_DIR))
    # XXX Generate it automatically?
    sys.exit()

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

def bytes_to_dwords(bytes):
    """!

    """
    dwords = []
    dword = 0
    shift = 0
    for byte in bytes:
        dword += (ord(byte) << shift)
        shift += 8
        if (shift == 32):
            dwords.append(dword)
            shift = 0
            dword = 0

    if (shift != 0):
        dwords.append(dword)

    return dwords

def update_translation_machinery_from_xml(translation_tables, translation_lookups):

    def update_translation_overrides(translation_tables):
        # Some values are not present in gles, override them here
        # XXX Do this with an XML?
        # XXX Review if there's a better way of filtering out non-gles2 defines
        #     or translating to gles2-friendly ones when parsing global and local
        #     namespaces

        # GetPName contains GL_BLEND_EQUATION_EXT, the global namespace has the
        # gles2-aware GL_BLEND_EQUATION, remove it from the GetPName namespace
        del translation_tables['GetPName'][0x8009]
        # GL_DRAW_FRAMEBUFFER_BINDING is not gles2, but GL_FRAMEBUFFER_BINDING is
        translation_tables['global'][0x8ca6] = "GL_FRAMEBUFFER_BINDING"
        # Make sure low numbers are set properly (Eg GL_CURRENT_BIT overrides GL_ONE, etc)
        translation_tables['global'][0] = "GL_ZERO"
        translation_tables['global'][1] = "GL_ONE"
        # Remove the BlendEquationModeEXT table, as it's in the global namespace
        # without the EXT
        del translation_tables['BlendEquationModeEXT']

    def update_translation_if_better(translation_table, group_name, enum_name, enum_value):
        # Favor non-extension names over extension names, as the extensions
        # may not be present in the gles headers and cause build failures
        # XXX Review if there's a better way of filtering out non-gles2 defines
        #     when parsing the global namespace
        if ((enum_value not in translation_table) or
            (re.match(".*_NV$|.*_ATI$|.*_3DFX$|.*_SGIS$|.*_INTEL$|.*_IMG|.*_QCOM",
                      translation_table[enum_value]) is not None)):
            logger.debug("Inserting translation in %s for %s as 0x%x" %
                         (group_name, enum_name, enum_value))
            translation_table.update({ enum_value : enum_name })
        else:
            logger.debug("Not inserting translation in %s for %s as 0x%x due to already-existing to %s" %
                         (group_name, enum_name, enum_value, translation_table[enum_value]))

    logger.info("Updating translation machinery from xml")

    # pre-fill the translation tables with enums
    with xopen("external/khronos/gl.xml", "r") as xml_file:
        tree = xml.etree.ElementTree.parse(xml_file)

        # For every GLES 2 function, get the enumerants and fill the translation table
        # Get all the GLES2 features
        registry = tree.getroot()
        # From the registry hangs
        # - groups with the possible types of each group
        # - types
        # - enums for each namespace with the allowed values
        # - commands (functions) for each namespace
        # - feature with the api and version, containing
        #       - required commands,
        #       - types,
        # - extensions
        # Get all the gles2 2.0 commands (note ES 3.0 is also regarded as gles2 api)
        # XXX May be it's better just to insert all the groups no matter the api?
        # XXX Note this leaves out lots of functions (glPointerAttrib...) whose enums
        #     are post-patched later using the global table (which is necessary anyway
        #     because many groups are not defined eg VertexAttribEnum)
        logger.info("Updating translation machinery gles2 namespace")
        for required_command in registry.findall("./feature[@api='gles2'][@number='2.0']/require/command"):
            # Insert the command and the enum mappings it accepts for
            # each argument
            command_name = required_command.get('name')
            logger.debug("Creating translation machinery for function %s" % command_name)

            # Fetch the command information
            # ElementTree XPath doesn't support [text()=]
            commands = registry.iterfind("./commands/command")
            params = None
            for command in commands:
                if (command.findtext('./proto/name') == command_name):
                    params = command.iterfind("./param")
                    break

            if (params is None):
                continue

            for param_index, param in enumerate(params):
                group_name = param.get('group')

                logger.debug("Found param %s" % param.findtext('./name'))

                try:
                    translation_lookup = translation_lookups[command_name]
                except KeyError:
                    translation_lookup = {}
                    translation_lookups[command_name] = translation_lookup

                # Don't insert the element if already there, as this would override
                # the id translation tables (eg this happens with glBindTexture
                # because the "texture" parameter is defined as part of the
                # group "Texture")
                if (param_index in translation_lookup):
                    logger.debug("Not inserting already-existing lookup %s" %
                                 translation_lookup[param_index])
                    continue

                logger.debug("Inserting lookup for %s %s" % (command_name, translation_lookup))

                # Lookup the right field depending on the type
                # XXX This is not very nice, it's dependent on the types defined
                #     in the xml, maybe this should be done "at the other side"
                #     when we get the trace item
                if (group_name == "Boolean"):
                    field_name = "boolValue"
                else:
                    # XXX Missing looking up floats?
                    field_name = "intValue"

                # XXX Another dependency on the xml types, move this to the other side
                #     as above
                if (group_name not in [None, "ColorF", "CheckedIn32", "CheckedFloat32"]):
                    translation_lookup.update(
                        { param_index : { "field" : field_name, "table" : group_name } }
                    )

                # Don't insert the group if there was no group (eg the type wasn't
                # enum) or if it has already been inserted
                if ((group_name is not None) and (group_name not in translation_tables)):
                    logger.debug("Creating translation machinery for parameter %s" % param.findtext('./name'))

                    group = registry.find("./groups/group[@name='%s']" % group_name)

                    # Some groups (TextureUnit) have the translation in the global
                    # namespace
                    if (group is not None):
                        logger.debug("Creating translation machinery for group %s" % group_name)

                        translation_table = {}
                        translation_tables[group_name] = translation_table

                        # For every enum in the group, get the value and insert it as a
                        # possible translation
                        group_enums = group.findall("./enum")
                        for group_enum in group_enums:
                            enum_name = group_enum.get('name')

                            # Get the enum value
                            enum = registry.find("./enums/enum[@name='%s']" % enum_name)
                            if (field_name == "boolValue"):
                                enum_value = bool(int(enum.get('value')))
                            else:
                                enum_value = int(enum.get('value'), 16)

                            update_translation_if_better(translation_table, group_name, enum_name, enum_value)

        # Insert all the enums without group enums in the global table so they can
        # be used as fall-back when a translation is not found in the group
        logger.info("Updating translation machinery global namespace")
        translation_table = translation_tables['global']
        for enum in registry.findall("./enums/enum"):
            if (enum.get('group', None) is None):
                enum_value = int(enum.get('value'), 16)
                enum_name = enum.get('name')
                update_translation_if_better(translation_table, 'global', enum_name, enum_value)

    logger.debug("Doing manual overrides")
    update_translation_overrides(translation_tables)

    logger.info("Updated translation machinery")

def main():
    LOG_LEVEL=logging.INFO

    logger.setLevel(LOG_LEVEL)

    logger.info("Starting")
    ##trace = xopen(r"_out/bmk_hw_layer_use_color_hw_layer.gltrace.gz", "rb")
    ##trace = xopen(r"_out/com.amazon.kindle.otter.gltrace.gz", "rb")
    ##trace = xopen(r"_out\contactsShowcaseAnimation.gltrace.gz", "rb")
    ##trace = xopen(r"_out\bmk_hw_layer.gltrace.gz", "rb")
    trace = xopen(r"_out\bmk_bitmap.gltrace.gz", "rb")
    ##trace = xopen(r"_out\kipo.gltrace", "rb")

    # Every argument can be optionally translated using a translation table
    # Each translation table contains:
    #   - the function that generates the translation table, the parameter index
    #     and and field
    #       - the function will generate the value to translate to at trace replay
    #       - the value to translate from is given as the intValue
    #       - multiple values can be translated
    #   - the functions that consume the translation table and which parameter
    #     and field n

    # Optionally, the translation table can be prefilled with ENUMs so numeric
    # literals are translated to GL ENUMS

    # The translation tables can be swapped in and out eg
    # - makeCurrent swaps all translation tables if there's no sharing across
    #   contexts
    # - glUseProgram swaps the active uniform translation table
    translation_tables = {
        # When reading the XML is enabled, this generates entries like
        # "AccumOp" : { 0x0100 : "GL_ACCUM" },

        # Additionally, it fills the global namespace with enums that don't belong
        # to a specific group
        'global' : {},

        # At runtime, more entries will be generated for object IDs like
        # "textures" :  { 1 : "var121[0]" },
        # No need to initialize them here as they will be created as needed
    }

    # Functions that trigger insertions in the translation machinery and the
    # argument's index that should be inserted, or -1 if the return value should
    # be inserted
    translation_insertions = {
        #  XXX This doesn't work atm, the trace doesn't contain the return value
        #      for eglCreateContext.
        #      This probably needs to be handled in a special way?
        ## "eglCreateContext"  : { -1 :{ "field" : "intValue", "table" : "contexts"     }},

        "glCreateShader"    : { -1 : { "field" : "intValue", "table" : "shaders"  }},
        "glCreateProgram"   : { -1 : { "field" : "intValue", "table" : "programs" }},

        # Insertions to the current context
        "glGenBuffers"      : { 1 : { "field" : "intValue", "table" : "buffers"      }},
        "glGenFramebuffers" : { 1 : { "field" : "intValue", "table" : "framebuffers" }},
        "glGenRenderBuffers": { 1 : { "field" : "intValue", "table" : "renderbuffers"}},
        "glGenTextures"     : { 1 : { "field" : "intValue", "table" : "textures"     }},


        # Insertions to the current context and the program parameter
        "glGetUniformLocation" : { -1 : {"field" : "intValue", "context" : 0, "table" : "uniforms" }},
        "glGetAttribLocation"  : { -1 : {"field" : "intValue", "context" : 0, "table" : "attribs" }},
    }

    # XXX Missing removing entries when calling glDeleteXXXX.
    # Currently translations are overwritten when a new one is found after a
    # deletion, so things should work fine
    translation_deletions = {
        ## glDeleteBuffers
        ## glDeleteFrameBuffers
        ## glDeleteProgram
        ## glDeleteRenderBuffers
        ## glDeleteShader
        ## glDeleteTextures
        ## glDetachShader
    }

    # Functions with arguments that require lookups from the translation machinery
    # Function, zero-index argument, field and translation table that require a
    # given translation, optional context with the argument index to use as context
    # (eg active uniforms use the program parameter as context for the table)
    translation_lookups = {
        "eglMakeCurrent"    : { 0 : { "field" : "intValue", "table" : "contexts"     }},

        "glActiveTexture"   : { 1 : { "field" : "intValue", "table" : "textures"     }},
        "glAttachShader"    : { 0 : { "field" : "intValue", "table" : "programs"     },
                                1 : { "field" : "intValue", "table" : "shaders"      }},

        "glBindAttribLocation": { 0: { "field" : "intValue", "table" : "programs"    }},
        "glBindBuffer"      : { 1 : { "field" : "intValue", "table" : "buffers"      }},
        "glBindFrameBuffer" : { 1 : { "field" : "intValue", "table" : "framebuffers" }},
        "glBindRenderBuffer" : { 1 : { "field" : "intValue", "table" : "renderbuffers" }},
        "glBindTexture"     : { 1 : { "field" : "intValue", "table" : "textures"     }},

        "glCompileShader"   : { 0 : { "field" : "intValue", "table" : "shaders"      }},

        # XXX Needs per-element lookup support
        ## "glDeleteBuffers"   : { 1 : { "field" : "intValue", "table" : "buffers"      }},
        # XXX Needs per-element lookup support
        ## "glDeleteBuffers"   : { 1 : { "field" : "intValue", "table" : "framebuffers" }},
        "glDeleteProgram"   : { 0 : { "field" : "intValue", "table" : "programs"     }},
        # XXX Needs per-element lookup support
        ## "glDeleteRenderBuffers" : { 1 : { "field" : "intValue", "table" : "renderbuffers"      }},
        "glDeleteShader"    : { 0 : { "field" : "intValue", "table" : "shaders"     }},
        # XXX Needs per-element lookup support
        ## "glDeleteTextures"   : { 1 : { "field" : "intValue", "table" : "textures" }},
        "glDetachShader"    : { 0 : { "field" : "intValue", "table" : "programs"     },
                                1 : { "field" : "intValue", "table" : "shaders"      }},
        "glEGLImageTargetTexture2DOES" : { 1 : { "field" : "intValue", "table" : "textures" }},
        "glFramebufferRenderbuffer" : { 3 : { "field" : "intValue", "table" : "renderbuffers" }},
        "glFramebufferTexture2D" : { 3 : { "field" : "intValue", "table" : "textures" }},

        "glGetActiveAttrib" : { 0: { "field" : "intValue", "table" : "programs"      },
                                1: { "field" : "intValue", "context" : 0, "table" : "attribs" }},
        "glGetActiveUniform": { 0: { "field" : "intValue", "table" : "programs"      },
                                1: { "field" : "intValue", "context" : 0, "table" : "uniforms" }},
        "glGetAttachedShaders" : { 0 : { "field" : "intValue", "table" : "programs"     }},
        "glGetAttribLocation": { 0: { "field" : "intValue", "table" : "programs"     }},
        "glGetProgramiv"    : { 0 : { "field" : "intValue", "table" : "programs"     }},
        "glGetProgramInfoLog" : { 0 : { "field" : "intValue", "table" : "programs"     }},
        "glGetShaderiv"     : { 0 : { "field" : "intValue", "table" : "shaders"      }},
        "glGetShaderInfoLog" : { 0 : { "field" : "intValue", "table" : "shaders"     }},
        "glGetShaderSource" : { 0 : { "field" : "intValue", "table" : "shaders"     }},
        "glGetUniformfv" : { 0: { "field" : "intValue", "table" : "programs"   }},
        "glGetUniformiv" : { 0: { "field" : "intValue", "table" : "programs"   }},
        "glGetUniformLocation" : { 0: { "field" : "intValue", "table" : "programs"   }},

        "glIsBuffer"        : { 0 : { "field" : "intValue", "table" : "buffers"      }},
        "glIsFramebuffer"   : { 0 : { "field" : "intValue", "table" : "framebuffers" }},
        "glIsProgram"       : { 0 : { "field" : "intValue", "table" : "programs"     }},
        "glIsShader"        : { 0 : { "field" : "intValue", "table" : "shaders"      }},
        "glIsTexture"       : { 0 : { "field" : "intValue", "table" : "textures"     }},

        "glLinkProgram"     : { 0 : { "field" : "intValue", "table" : "programs"     }},

        # XXX needs per-element lookup support
        ##"glShaderBinary"    : { 1 : { "field" : "intValue", "table" : "shaders"      }},
        "glShaderSource"    : { 0 : { "field" : "intValue", "table" : "shaders"      }},

        "glUniform1f"       : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform1fv"      : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform1i"       : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform1iv"      : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform2f"       : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform2fv"      : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform2i"       : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform2iv"      : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform3f"       : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform3fv"      : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform4f"       : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform4fv"      : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform3i"       : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform3iv"      : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform4i"       : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniform4iv"      : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniformMatrix2fv" : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniformMatrix3fv" : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUniformMatrix4fv" : { 0 : { "field" : "intValue", "table" : "current_uniforms" }},
        "glUseProgram"      : { 0 : { "field" : "intValue", "table" : "programs"     }},
        "glValidateProgram" : { 0 : { "field" : "intValue", "table" : "programs"     }},

        # Additionally, when reading the XML this will be filled in with lookups
        # for translating numeric literals to human-friendly enums
        # "glBindTexture"   : { 0 : { "field" : "intValue", "table" : "TextureTarget" }},
    }

    # This can be disabled to save ~5s of time
    # XXX This needs fixing so:
    # - it doesn't use global tables with enums that gles2 doesn't have
    # - it doesn't override runtime look up tables (not clear why this happens)
    use_human_friendly_gl_enums = True
    if (use_human_friendly_gl_enums):
        update_translation_machinery_from_xml(translation_tables, translation_lookups)

    # Number of temporary variables that have been allocated, we need this
    # so we don't generate a variable with the same name twice
    allocated_vars = 0
    current_state = { 'program' : None, 'context' : None }
    while True:
        buffer_length = trace.read(4)
        if (buffer_length == ""):
            break
        buffer_length = struct.unpack('!i', buffer_length)[0]
        logger.debug("unpacked %d ints" % buffer_length)
        buffer = trace.read(buffer_length)
        msg = gltrace_pb2.GLMessage.FromString(buffer)

        function_name = gltrace_pb2.GLMessage.Function.DESCRIPTOR.values_by_number[msg.function].name
        function_string = function_name

        logger.debug("Found function %s" % function_name)

        # Add frame check
        if (function_name == "eglSwapBuffers"):
            print "if (frame_count++ >= frame_limit) { return; }"
        # XXX Remove
        ## if (function_name == "eglSwapBuffers"):
        ##    break

        # Do translation machinery context in/out
        # This could be parameterized in tables, but only two functions cause
        # switches so it's not worth it
        if (function_name == "glUseProgram"):
            # Copy this program's uniforms to the active uniforms
            # Note this copies the reference, so inserting in 'uniforms' is enough
            # to update both
            table_name = "uniforms_%d" % msg.args[0].intValue[0]
            try:
                current_uniforms = translation_tables[table_name]
            except:
                current_uniforms = {}
                translation_tables[table_name] = current_uniforms

            translation_tables['current_uniforms'] = current_uniforms

            logger.debug("Switched current uniforms to %s" % table_name)

        if (function_name == "eglMakeCurrent"):
            # XXX This needs to evict the program-specific tables like uniforms_NNN
            tables_to_evict = [ 'attribs', 'uniforms', 'current_uniforms', 'textures', 'shaders', 'programs', 'buffers', 'framebuffers' ]
            current_field_name = 'context'
            id_prefix_current_field_names = []
            next_current_value = msg.args[0].intValue[0]

            # Switch the attribs and uniforms tables away by renaming the tables
            # Only do this if the new state is different from the old
            if (current_state[current_field_name] != next_current_value):
                if (current_state[current_field_name] is not None):

                    # Calculate a prefix to the evict id, this is necessary
                    # eg. so evicted tables from different contexts are not
                    # overwritten
                    # XXX Right now this doesn't work if contexts share lists
                    #     Probably the solution to that is to make different contexts
                    #     share the translation tables (either by having them
                    #     point to the same dict or by having the id be shared
                    #     across contexts of the same group)

                    evict_id_prefixes = [str(current_state[id_prefix_current_field_name])
                                        for id_prefix_current_field_name in id_prefix_current_field_names]

                    for table_name in tables_to_evict:

                        evict_id = string.join(evict_id_prefixes + [str(current_state[current_field_name])], "_")
                        evicted_table_name = "%s_%s" % (table_name, evict_id)
                        evicted_table = translation_tables.get(table_name, {})

                        logger.debug("Evicting table %s into %s" % (table_name, evicted_table_name))
                        logger.debug("  %s" % evicted_table)
                        translation_tables[evicted_table_name] = evicted_table

                        # XXX Check for setting the NULL object?
                        evict_id = string.join(evict_id_prefixes + [str(next_current_value)], "_")
                        evicted_table_name = "%s_%s" % (table_name, evict_id)
                        evicted_table = translation_tables.get(evicted_table_name, {})

                        logger.debug("Restoring table %s into %s" % (evicted_table_name, table_name))
                        logger.debug("  %s" % evicted_table)
                        translation_tables[table_name] = evicted_table

                logger.debug("Setting new current state %s from %s to %s" %
                             (current_field_name,
                              current_state[current_field_name],
                          next_current_value))
                logger.debug(current_state[current_field_name])
                current_state[current_field_name] = next_current_value

        # XXX glVertexAttribPointerData is a fake call that Android inserts before
        # glDrawXXXXX to supply the glVertexAttribPointer data, see
        # http://stackoverflow.com/questions/14382208/what-is-glvertexattribpointerdata

        # Ignore makecurrent and createcontext
        # XXX Implement makecurrent and createcontext
        if ((function_name == "eglCreateContext") or
            (function_name == "eglMakeCurrent") or
            (function_name == "eglSwapBuffers")):
            continue

        args_strings = []
        preamble_strings = []

        translation_insertion = translation_insertions.get(function_name, {})
        translation_lookup = translation_lookups.get(function_name, {})

        for arg_index, arg in enumerate(msg.args):

            logger.debug("Found arg %s" % str(arg))

            # Patch wrong functions
            if ((function_name == "glGetVertexAttribiv") and (arg_index == 2)):
                # XXX The trace sends intValue with isArray false
                logger.debug("Patching function %s" % function_name)
                arg.isArray = True

            elif ((function_name == "glGetActiveUniform") and (arg_index == 7)):
                # XXX The trace sends an extra int with some index?
                continue

            elif (function_name == "glGetActiveAttrib"):
                if (arg_index == 7):
                    # XXX The trace sends an extra int with some index?
                    continue

            elif ((function_name == "glVertexAttribPointerData") and (arg_index > 5)):
                # XXX The trace sends two extra ints with some indices?
                continue

            elif (function_name == "glGetFloatv"):
                if (arg_index == 0):
                    is_aliased_point_size_range = True
                elif ((arg_index == 1) and (is_aliased_point_size_range)):
                    # XXX The trace sends a single float array, but the spec says two
                    #     elements
                    is_aliased_point_size_range = False
                    arg.floatValue.append(0.0)

            elif (function_name == "glGetShaderInfoLog"):
                # the two last glGetShaderInfoLog arguments in the trace are ints
                # instead array of int and array of char, convert to those
                if (arg_index == 1):
                    # Store the max length for later
                    get_shader_info_log_max_length = int(arg.intValue[0])
                    logger.debug("Found shader_info_log_max_length %d" % get_shader_info_log_max_length)
                if (arg_index == 2):
                    # Convert to pointer to int
                    arg.isArray = True
                elif (arg_index == 3):
                    # Convert to pointer to char
                    arg.isArray = True
                    arg.charValue.append("?" * get_shader_info_log_max_length)

            elif (function_name == "glGetVertexAttribPointerv"):
                # the last parameter in the trace is an INT instead of a pointer
                # to pointer, convert to pointer to int
                if (arg_index == 2):
                    arg.isArray = True
                    arg.type = gltrace_pb2.GLMessage.DataType.VOID

            elif (function_name == "glDiscardFramebufferEXT"):
                # the last parameter in the trace is an INT instead of a pointer,
                # convert to pointer
                if (arg_index == 2):
                    logger.debug("Patching parameter of glDiscardFramebufferEXT")
                    arg.type = gltrace_pb2.GLMessage.DataType.VOID

            elif (function_name == "glVertexAttribPointer"):
                # the last parameter in the trace is an INT instead of a pointer,
                # convert to pointer
                if (arg_index == 5):
                    arg.type = gltrace_pb2.GLMessage.DataType.VOID

            elif (function_name == "glShaderSource"):
                # The trace uses CHAR array, remove the array as a special case
                # to signify that it's an array of char arrays
                if (arg_index == 2):
                    arg.isArray = False

            elif ((function_name == "glTexParameteri") and (arg_index == 2)):
                # glTexParameteri has an INT as last parameter but in real life
                # it's always an ENUM
                # Switch to ENUM so it gets translated
                arg.type = gltrace_pb2.GLMessage.DataType.ENUM

            # Do argument translation lookup if necessary
            lookup = translation_lookup.get(arg_index, None)
            translated_value = None
            if (lookup is not None):
                # Note some tables don't exist (Eg BufferTargetARB)
                field_name = lookup['field']
                table_name = lookup['table']
                try:
                    # Append the context to the table, if any
                    table_name = "%s_%d" % (table_name, msg.args[lookup['context']].intValue[0])
                except KeyError:
                    pass
                # The attribute may not be there
                logger.debug("Getting field %s" % str(field_name))
                value = getattr(arg, field_name)
                if (len(value) == 0):
                    logger.error("Unexpected arg %s in function %s" % (str(arg), function_name))
                else:
                    if (field_name == "boolValue"):
                        value = bool(int(value[0]))
                    else:
                        value = int(value[0])
                    logger.debug("Looking up translation for 0x%x in %s" % (value, table_name))
                    # The entry will not exist eg if we are binding back the NULL object
                    # XXX This could be changed to there's a default 0-entry in all
                    #     translation tables
                    translation_table = translation_tables.get(table_name, {})
                    try:
                        translated_value = translation_table[value]
                        logger.debug("Translated %s to %s via %s" % (str(value), translated_value, table_name))
                    except KeyError:
                        pass


            # Fall-back to the global enums for untranslated enums
            # (this can happen eg for Google's fake AttribPointerData functions,
            # but also for functions out of gles2 which are not explicitly inserted
            # at initialization time)
            if ((translated_value is None) and (arg.type == gltrace_pb2.GLMessage.DataType.ENUM)):
                logger.debug("Patching translation of enum %d to global table for %s" %
                    (arg.intValue[0], function_name))
                translation_table = translation_tables['global']
                translated_value = translation_table.get(arg.intValue[0], None)

            # Keep in order, some options have higher priority than others

            # When all of intValue, charValue and isArray are set, a pointer is
            # passed in with existing char contents
            # This is used for glShaderSource, glPushGroupMarker, etc

            # When all of intValue, floatValue and isArray are set, a pointer is
            # passed in with existing float contents
            # This is used for glUniformMatrix4fv, etc
            if ((len(arg.floatValue) > 0) and (arg.isArray)):
                arg_name = "ptr%d" % allocated_vars
                allocated_vars += 1
                preamble_strings.append("static float %s[] = { %s }" % (
                    arg_name,
                    string.join([str(f) for f in arg.floatValue], ", ")))
                args_strings.append(arg_name)

            # When rawbytes is set, initialized data is passed in
            # (glTexSubImage2D, glTexImage2D, etc)
            elif (len(arg.rawBytes) > 0):
                dwords = bytes_to_dwords(arg.rawBytes[0])
                arg_name = "ptr%d" % allocated_vars
                allocated_vars += 1
                args_strings.append(arg_name)
                preamble_strings.append("static const unsigned int %s[] = { %s }" % (
                    arg_name,
                    string.join([hex(dword) for dword in dwords], ", ")))

            # When isArray is set, the parameter is passed by reference and
            # contains a return value, which is held in the xxxValue part
            # Those need to be stored in variables in case they are used
            # in the future
            # Note booleans have both len(intValue) and len(boolValue) greater
            # than zero
            elif ((arg.isArray) and ((len(arg.intValue) > 0) or (len(arg.boolValue) > 0) or
                    len(arg.charValue) > 0)):
                var_name = "var%d" % allocated_vars
                allocated_vars += 1
                # XXX Missing initializers for all but charvalue?
                if (len(arg.boolValue) > 0):
                    preamble_strings.append("GLboolean %s[%d]" % (var_name , len(arg.boolValue)))
                elif (len(arg.charValue) > 0):
                    if ("\n" in arg.charValue[0]):
                        initializer = '"\\\n  %s\\n"' % arg.charValue[0].replace("\n", "\\\n  ")
                    else:
                        initializer = '"%s"' % arg.charValue[0]
                    preamble_strings.append("static GLchar %s[] = %s" % (var_name, initializer))
                elif (len(arg.intValue) > 0):
                    if (arg.type == gltrace_pb2.GLMessage.DataType.VOID):
                        # the parser patches some pointers to void from INTs to
                        # VOID
                        preamble_strings.append("GLvoid* %s[1]" % var_name)
                    else:
                        preamble_strings.append("GLint %s[%d] = {%s}" %
                                    (var_name , len(arg.intValue),
                                     string.join([str(i) for i in arg.intValue], ", ")))
                args_strings.append(var_name)

            elif (arg.isArray):
                raise Exception("unhandled array argument %s for %s" % (arg, msg))

            elif (len(arg.charValue) > 0):
                # charValue with isArray set to false is only used for the
                # special case of glSetShaderSource, in which case we need
                # a pointer to pointer to const chars (const qualifier is not
                # ignored across pointers)
                arg_name = "var%d" % allocated_vars
                allocated_vars += 1
                if ("\n" in arg.charValue[0]):
                    initializer = '"\\\n  %s\\n"' % arg.charValue[0].replace("\n", "\\\n  ")
                else:
                    initializer = '"%s"' % arg.charValue[0]
                preamble_strings.append("const GLchar* %s[] = {%s} " % (
                    arg_name,
                    initializer))
                args_strings.append(arg_name)

            elif (len(arg.intValue) > 0):
                # XXX Don't hard-code this only to intValues
                if (translated_value is not None):
                    args_strings.append(str(translated_value))
                else:
                    if (arg.type == gltrace_pb2.GLMessage.DataType.ENUM):
                        args_strings.append(hex(arg.intValue[0]))
                    elif (arg.type == gltrace_pb2.GLMessage.DataType.VOID):
                        args_strings.append("(GLvoid*) 0x%x" % ctypes.c_uint32(arg.intValue[0]).value)
                    else:
                        args_strings.append(str(arg.intValue[0]))

            elif (len(arg.floatValue) > 0):
                args_strings.append(str(arg.floatValue[0]))

            elif (len(arg.boolValue) > 0):
                if (translated_value is not None):
                    args_strings.append(str(translated_value))
                else:
                    if (arg.boolValue[0]):
                        args_strings.append("GL_TRUE")
                    else:
                        args_strings.append("GL_FALSE")

            else:
                raise Exception("unhandled argument %s" % arg)

            # Insert in the translation if necessary
            insertion = translation_insertion.get(arg_index, None)
            if (insertion is not None):
                assert(arg.isArray)

                table_name = insertion['table']
                field_name = insertion['field']
                # Append the context to the table name
                try:
                    context_index = insertion['context']
                    table_name = "%s_%d" % (table_name, msg.args[context_index].intValue[0])
                except KeyError:
                    # No context, ignore
                    pass
                try:
                    table = translation_tables[table_name]
                except KeyError:
                    table = {}
                    translation_tables[table_name] = table

                values = getattr(arg, field_name);

                for value_index, value in enumerate(values):
                    table[value] = "%s[%d]" % (var_name, value_index)
                    logger.debug("Updated table %s entry %d to value %s" %
                        (table_name, value, table[value]))

        # Insert a translation for the return value if necessary
        # Note this will keep overwriting the translation for id = -1
        # (eg the id of an inactive uniform/attrib), but that is fine as it's
        # invalid to pass inactive uniform/attribs as parameters to functions
        # XXX Should we ignore adding translations & code for id = -1?
        insertion = translation_insertion.get(-1, None)
        if (insertion is not None):
            table_name = insertion['table']
            field_name = insertion['field']
            # Append the context to the table name
            try:
                context_index = insertion['context']
                table_name = "%s_%d" % (table_name, msg.args[context_index].intValue[0])
            except KeyError:
                # No context, ignore
                pass

            try:
                table = translation_tables[table_name]
            except KeyError:
                # Create the table
                table = {}
                translation_tables[table_name] = table
            values = getattr(msg.returnValue, field_name);

            # We only expect one value being returned
            assert(len(values) == 1)
            value = values[0]

            # Create a new variable to hold the return value
            var_name = "var%d" % allocated_vars
            allocated_vars += 1
            preamble_strings.append("unsigned int %s" % var_name)

            table[value] = var_name
            logger.debug("Updated table %s entry %d to return value %s" %
                (table_name, value, table[value]))

            function_string = "%s=%s" % (var_name, function_string)

        logger.debug("Found return %s" % msg.returnValue)

        for preamble in preamble_strings:
            logger.debug("%s;" % preamble)
            print "%s;" % preamble
        program_line = "%s(%s);" % (function_string, string.join(args_strings, ", "))
        print 'LOGI("0x%%x: %s", glGetError());' % program_line
        print program_line
        logger.debug(program_line)
        ## print 'glFinish();'

        # Add draw check
        if (function_name in ['glDrawElements', 'glDrawArrays']):
            print "if (draw_count++ > draw_limit) { return; }"


if (__name__ == "__main__"):
    logging_format = "%(asctime).23s %(levelname)s:%(filename)s(%(lineno)d) [%(thread)d]: %(message)s"

    logger_handler = logging.StreamHandler()
    logger_handler.setFormatter(logging.Formatter(logging_format))
    logger.addHandler(logger_handler)

    main()
