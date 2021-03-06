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

# https://android.googlesource.com/platform/frameworks/native/+/master/opengl/libs/GLES_trace/DESIGN.txt
# https://android.googlesource.com/platform/frameworks/native/+/master/opengl/libs/GLES_trace/gltrace.proto

# https://cvs.khronos.org/svn/repos/ogl/trunk/doc/registry/public/api/gl.xml

import ctypes
import errno
import hashlib
import logging
import os
import re
import string
import struct
import sys
import xml.etree.ElementTree

import utils

logger = logging.getLogger(__name__)

PROTOBUFF_DIR = "external/google"
sys.path.append(os.path.join(sys.path[0],PROTOBUFF_DIR))
# XXX This is so when invoked from the test dir it can find the protobuf, fix
#     in a more elgant way
sys.path.append(os.path.join(sys.path[0],"..", PROTOBUFF_DIR))
try:
    import gltrace_pb2
except ImportError as error:
    logger.error(error)
    logger.error("Protobuf Python package not found (install with 'pip protobuf') or "
                 "the protobuff gltrace Python module %s/gltrace_pb2.py doesn't exist, "
                 "generate it with\n"
                 "  %s/protoc %s/gltrace.proto --python_out=%s" %
                 (PROTOBUFF_DIR, PROTOBUFF_DIR, PROTOBUFF_DIR, PROTOBUFF_DIR))
    # XXX Generate it automatically?
    sys.exit()

def update_translation_machinery_from_xml(translation_tables, translation_lookups):
    # XXX Pickle this to disk so it doesn't need to be parsed every time, takes 29s
    #     under the profiler

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
        # XXX Missing masks like GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT
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
    GL_XML_FILEPATH = "external/khronos/gl.xml"
    # XXX This is so it can be executed from the tests directory, find a
    #     way of making this transparent
    if (not os.path.exists(GL_XML_FILEPATH)):
        GL_XML_FILEPATH = os.path.join("..", GL_XML_FILEPATH)
    with utils.xopen(GL_XML_FILEPATH, "r") as xml_file:
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

def hash_asset(asset_bytes):
    hash = hashlib.md5()
    hash.update(asset_bytes)

    return hash.digest()

def allocate_asset(allocated_assets, allocated_asset_filenames, assets_dir,
                   asset_buffer_ptr, asset_filename, asset_buffer_ptr_type,
                   asset_variable_ptr, asset_bytes, global_decls):
    """!
    Register the given asset and unregister
    """
    # Free a possible asset allocated to this id
    # XXX Hash the assets and reuse them if they have the same content?
    code = []
    if (asset_variable_ptr in allocated_assets):
        code.extend(free_asset(allocated_assets, asset_variable_ptr, asset_buffer_ptr))
    else:
        # It's the first time we see this asset, generate code to create this
        # asset variable
        # XXX Note this fails when the asset is recycled across types in two ways:
        #     - it may not declare the buffer pointer variable
        #     - it overwrites a live pointer (so the asset really has to
        #       have a different name, not enough with declaring the buffer pointer)
        #     Additionally, all assets with delayed deallocation should have
        #     different namespaces or it will fail too (eg textures with int pointers
        #     and vertex buffers with int pointers, if such thing exists).
        #     The solution is to use a per-resource type asset and buffer pointer, eg
        #     global_int_ptr_texture_0, global_int_ptr_index_0, etc
        global_decls.append("AAsset* %s = NULL" % asset_variable_ptr)
        global_decls.append("%s %s = NULL" % (asset_buffer_ptr_type, asset_buffer_ptr))
    allocated_assets.add(asset_variable_ptr)

    asset_hash = hash_asset(asset_bytes)
    # XXX This assumes there are no collisions
    # XXX This should be done for all assets, not just for asset files
    try:
        asset_filename = allocated_asset_filenames[asset_hash]
    except KeyError:
        allocated_asset_filenames[asset_hash] = asset_filename

    # Save the asset to a file
    with open(os.path.join(assets_dir, asset_filename), "wb") as f:
        f.write(asset_bytes)

    # Generate the instructions to load that asset
    # XXX Change the asset manager to global so it makes deinlining less verbose?
    #     (less parameters).
    # XXX Note we use openAndGetAssetBuffer to simplify the code deinlining, as
    #     otherwise there can be aliasing problems as follows:
    #       openAsset(pMgr, "filename", &pAsset)
    #       getAssetBuffer(pAsset,
    #     is deinlined as
    #       void subframe(pMgr, &pAsset, param_AAsset_ptr, param_AAsset_ptr_ptr)
    #           openAsset(pMgr, "filename", param_AAsset_ptr_ptr)
    #           getAssetBuffer(param_AAsset_ptr
    #     Note how getAssetBuffer calls using a temporary variable that is no
    #     longer updated by the call to openAsset
    #     This could be solved by taking aliasing into account when removing
    #     redundant parameters.
    code.append('openAndGetAssetBuffer(%s, "%s", &%s, (const void**) &%s)' %
                ("param_DrawState_ptr_0", asset_filename, asset_variable_ptr,
                 asset_buffer_ptr))

    return code

def free_asset(allocated_assets, asset_variable_ptr, asset_buffer_ptr):
    allocated_assets.remove(asset_variable_ptr)

    return ["closeAsset(%s)" % asset_variable_ptr,
            "%s = NULL" % asset_variable_ptr, "%s = NULL" % asset_buffer_ptr]

# XXX Missing other parameters like asset file vs. variable size threshold
def glparse(trace_filepath, output_dir, assets_dir, gl_contexts_to_trace):
    """!
    @param gl_contexts_to_trace: *list* of *integers* with the contexts to trace
            or None to trace all.
    """
    # Number of temporary variables that have been allocated, we need this
    # so we don't generate a variable with the same name twice
    num_allocated_vars = 0
    allocated_assets = set()
    # Asset filenames indexed by the hash of the contents
    # This is used for asset file coalescing (point two different assets to the
    # same file if they have the same contents)
    allocated_asset_filenames = {}

    logger.info("Tracing file %s" % trace_filepath)
    logger.info("Output dir %s" % output_dir)
    logger.info("Assets dir %s" % assets_dir)
    logger.info("Tracing contexts %s" % gl_contexts_to_trace)

    logger.info("Starting")
    trace = utils.xopen(trace_filepath)

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
        #  WAR: The trace contains the context id in the second parameter instead
        #      of the return value, treat this as if the value was being returned
        #      and special case it later
        "eglCreateContext"  : { -1 : { "field" : "intValue", "table" : "contexts"  }},

        "glCreateShader"    : { -1 : { "field" : "intValue", "table" : "shaders"  }},
        "glCreateProgram"   : { -1 : { "field" : "intValue", "table" : "programs" }},

        # Insertions to the current context
        "glGenBuffers"      : { 1 : { "field" : "intValue", "table" : "buffers"      }},
        "glGenFramebuffers" : { 1 : { "field" : "intValue", "table" : "framebuffers" }},
        "glGenRenderbuffers": { 1 : { "field" : "intValue", "table" : "renderbuffers"}},
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
        "glBindFramebuffer" : { 1 : { "field" : "intValue", "table" : "framebuffers" }},
        "glBindRenderbuffer" : { 1 : { "field" : "intValue", "table" : "renderbuffers" }},
        "glBindTexture"     : { 1 : { "field" : "intValue", "table" : "textures"     }},

        "glCompileShader"   : { 0 : { "field" : "intValue", "table" : "shaders"      }},

        "glDeleteBuffers"   : { 1 : { "field" : "intValue", "table" : "buffers"      }},
        "glDeleteFramebuffers"   : { 1 : { "field" : "intValue", "table" : "framebuffers" }},
        "glDeleteProgram"   : { 0 : { "field" : "intValue", "table" : "programs"     }},
        "glDeleteRenderbuffers" : { 1 : { "field" : "intValue", "table" : "renderbuffers"      }},
        "glDeleteShader"    : { 0 : { "field" : "intValue", "table" : "shaders"     }},
        "glDeleteTextures"   : { 1 : { "field" : "intValue", "table" : "textures" }},
        "glDetachShader"    : { 0 : { "field" : "intValue", "table" : "programs"     },
                                1 : { "field" : "intValue", "table" : "shaders"      }},
        "glEGLImageTargetTexture2DOES" : { 1 : { "field" : "intValue", "table" : "textures" }},
        "glFramebufferRenderbuffer" : { 3 : { "field" : "intValue", "table" : "renderbuffers" }},
        "glFramebufferTexture2D" : { 3 : { "field" : "intValue", "table" : "textures" }},

        "glGetActiveAttrib" : { 0: { "field" : "intValue", "table" : "programs"      },
                                1: { "field" : "intValue", "context" : 0, "table" : "attribs" }},
        # XXX Could the returned values be different at runtime than at trace time and cause
        # buffer overflows for glGetActiveUniform?
        # (the buffer limits are passed in by the program, maybe glparser should patch
        # them to the obtained values or create the variables wrt the passed in values)
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

        # Note the trace introduces calls to get the active attributes and active
        # uniforms in order to help the debugger, see
        # https://android.googlesource.com/platform/frameworks/native/+/3365c56716432d3bfdf41bb82fb08df821f41d0c/opengl/libs/GLES_trace/src/gltrace_fixup.cpp#305
        "glLinkProgram"     : { 0 : { "field" : "intValue", "table" : "programs"     }},

        "glShaderBinary"    : { 1 : { "field" : "intValue", "table" : "shaders"      }},
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

    # Create the asset directory, ignore if it already exists
    # Note the invoker should point to an existing parent path, fail otherwise
    try:
        os.mkdir(assets_dir)
    except OSError as e:
        if (e.errno != errno.EEXIST):
            raise

    #
    # Configuration options
    #

    max_frame_count = sys.maxint
    ##max_frame_count = 250
    # This can be disabled to save ~5s of time
    # XXX This needs fixing so it doesn't use global tables with enums that gles2
    #     doesn't have
    use_human_friendly_gl_enums = True

    # XXX Use min/max asset sizes for shaders?
    # XXX Move many of these to parameters or a config object
    use_assets_for_shaders = True

    use_assets_for_floats = True
    # Don't bother storing small floats in assets
    min_float_asset_size_in_floats = 64
    # Don't blow the stack if inlining floats
    max_float_inlined_size_in_floats = 512

    use_assets_for_ints = True
    # Don't bother storing small ints in assets
    min_int_asset_size_in_bytes = 256
    # Don't blow the stack if inlining ints
    max_int_inlined_size_in_bytes = 2048

    generate_empty_textures = False
    insert_glfinish_after_gl_functions = False
    insert_alog_after_gl_functions = False
    if (use_human_friendly_gl_enums):
        update_translation_machinery_from_xml(translation_tables, translation_lookups)

    logger.info("Starting trace parsing")

    current_state = { 'program' : None, 'context' : None }
    frame_count = 0
    function_enum_type = gltrace_pb2.GLMessage.DESCRIPTOR.enum_types_by_name['Function']
    code = []
    code_frames = [code]
    global_decls = []

    # XXX These should probably be in some state-dependent table so it gets
    #     switched in and out (or in some framebuffer-dependent state?)
    # Currently bound framebuffer
    current_framebuffer = 0
    # Current and max viewport state
    current_viewport_x = 0
    current_viewport_y = 0
    current_viewport_width = 0
    current_viewport_height = 0
    max_viewport_width = 0
    max_viewport_height = 0
    # Current and max scissor state
    current_scissor_x = 0
    current_scissor_y = 0
    current_scissor_width = 0
    current_scissor_height = 0
    max_scissor_width = 0
    max_scissor_height = 0

    while True:
        buffer_length = trace.read(4)
        if (buffer_length == ""):
            break
        buffer_length = struct.unpack('!i', buffer_length)[0]
        logger.debug("unpacked %d bytes" % buffer_length)
        buffer = trace.read(buffer_length)
        try:
            # The protobuff will be truncated if the app was terminated, etc
            # ignore the exception
            msg = gltrace_pb2.GLMessage.FromString(buffer)
        except:
            logger.warning("Decode error, truncated protobuff, trace will be incomplete")
            break

        assert None is logger.debug("Found message %s" % msg)

        function_name = function_enum_type.values_by_number[msg.function].name
        function_string = function_name

        logger.debug("Found function %s" % function_name)

        if ((gl_contexts_to_trace is not None) and (msg.context_id not in gl_contexts_to_trace)):
            logger.warning("Ignoring function %s for ignored context %d" %
                (function_name, msg.context_id))
            continue

        args_strings = []
        preamble_strings = []
        epilogue_strings = []

        # Append to the frames and check if this is the final frame
        if (function_name == "eglSwapBuffers"):
            frame_count += 1
            logger.info("Parsing frame %d" % frame_count)
            if (frame_count >= max_frame_count):
                break
            # Create a new code[] list and append a reference to it in the
            # code_frames list. Future modifications of code[] will be reflected
            # in code_frames[] automatically
            code = []
            code_frames.append(code)
            continue

        if ((function_name in ["glVertexAttrib1fv",
                               "glVertexAttrib2fv",
                               "glVertexAttrib3fv",
                               "glVertexAttrib4fv"]) and not msg.args[1].isArray):
            # WAR: glVertexAttrib4fv doesn't provide data, ignore it
            logger.warning("Ignoring glVertexAttribNv function as the trace doesn't provide the value")
            logger.debug(msg)
            continue

        if (function_name == "glGetActiveUniform"):
            logger.warning("Ignoring glGetActiveUniform as the trace doesn't provide a pointer")
            logger.debug(msg)
            continue

        if (function_name == "glDiscardFramebufferEXT"):
            # WAR: glDiscardFrameBufferEXT doesn't provide the frambufferse to
            #      discard, ignore
            logger.warning("Ignoring glDiscardFrameBufferEXT as the trace doesn't provide the value")
            logger.debug(msg)
            continue

        if ((function_name in ["glGetTexParameteriv", "glGetTexParameterfv"])):
            # glGetTexParameterXX provides an int as destination instead of a pointer, ignore.
            # XXX Is this an error in the capture or in glparse?
            logger.warning("Ignoring glGetTexParameterXX function as the trace doesn't provide a pointer")
            logger.debug(msg)
            continue

        if ((function_name in ["glGetVertexAttribfv"])):
            # glGetVertexAttribfv(GL_CURRENT_VERTEX_ATTRIB, ) provides an int as destination instead of a pointer, ignore.
            logger.warning("Ignoring glGetVertexAttribfv function as the trace doesn't provide a pointer")
            logger.debug(msg)
            continue

        if (function_name == "eglMakeCurrent"):
            # First and only parameter is context index
            function_string = "eglOverriddenMakeCurrent"
            args_strings.append("param_DrawState_ptr_0")

            # If we were to support non-shared contexts, this should swap the
            # translation tables so non-sharing contexts don't have common
            # translations. Note that the trace doesn't have information on which
            # contexts are sharing and which are not, so all contexts share.

        if (function_name == "eglCreateContext"):
            # First parameter is EGL version, second is returned context index
            # WAR: There's no information about:
            #     - the surface
            #     - the config
            #     - whether to share or not
            # Create a shared context using the default configuration
            function_string = "eglOverriddenCreateContext"

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

        translation_insertion = translation_insertions.get(function_name, {})
        translation_lookup = translation_lookups.get(function_name, {})

        for arg_index, arg in enumerate(msg.args):

            # Converting from tree element to string doubles the execution time,
            # only do it in debug
            assert None is logger.debug("Found arg %s" % str(arg))

            # Patch wrong functions
            # XXX Use function code rather than function name

            if (function_name == "glBindFramebuffer"):
                if (arg_index == 1):
                    current_framebuffer = arg.intValue[0]
                    # Always reset the viewport and scissor when switching
                    # framebuffers, as it could have the scaled version set
                    if (current_framebuffer == 0):
                        code.append("glScaledViewport(%d, %d, %d, %d)" %
                            (current_viewport_x,
                             current_viewport_y,
                             current_viewport_width,
                             current_viewport_height))
                        code.append("glScaledScissor(%d, %d, %d, %d)" %
                            (current_scissor_x,
                             current_scissor_y,
                             current_scissor_width,
                             current_scissor_height))
                    else:
                        code.append("glViewport(%d, %d, %d, %d)" %
                            (current_viewport_x,
                             current_viewport_y,
                             current_viewport_width,
                             current_viewport_height))
                        code.append("glScissor(%d, %d, %d, %d)" %
                            (current_scissor_x,
                             current_scissor_y,
                             current_scissor_width,
                             current_scissor_height))

            elif (function_name == "glViewport"):
                # Collect the maximum viewport so it can be scaled when
                # framebuffer 0 is bound
                # XXX Optionally, this could scale all framebuffers, not just
                #     framebuffer 0
                if (arg_index == 0):
                    current_viewport_x = arg.intValue[0]

                elif (arg_index == 1):
                    current_viewport_y = arg.intValue[0]

                elif (arg_index == 2):
                    current_viewport_width = arg.intValue[0]

                elif (arg_index == 3):
                    current_viewport_height = arg.intValue[0]
                    # Use the first call as heuristic to framebuffer 0 width and
                    # height
                    # XXX Viewport size tracking should be smarter, it
                    #     should track the viewport size just before rendering to
                    #     framebuffer 0, not just when calling glViewport, but
                    #     some apps may even use bigger viewport sizes when they
                    #     do that, so it's not fail-proof
                    # XXX A known offender is GTAVC, where the first viewport
                    #     is not the full one. A later viewport inside the trace
                    #     is full.
                    if (max_viewport_height == 0):
                        max_viewport_width = current_viewport_width
                        max_viewport_height = current_viewport_height

                    # We need to scale the viewport if rendering to framebuffer 0
                    if (current_framebuffer == 0):
                        function_string = "glScaledViewport"

            elif (function_name == "glScissor"):
                # Collect the maximum scissor so it can be scaled when
                # framebuffer 0 is bound
                # XXX Optionally, this could scale all framebuffers, not just
                #     framebuffer 0
                if (arg_index == 0):
                    current_scissor_x = arg.intValue[0]

                elif (arg_index == 1):
                    current_scissor_y = arg.intValue[0]

                elif (arg_index == 2):
                    current_scissor_width = arg.intValue[0]

                elif (arg_index == 3):
                    current_scissor_height = arg.intValue[0]
                    # Use the first call as heuristic to framebuffer 0 width and
                    # height
                    # XXX scissor size tracking should be smarter, it
                    #     should track the scissor size just before rendering to
                    #     framebuffer 0, not just when calling glScissor, but
                    #     some apps may even use bigger scissor sizes when they
                    #     do that, so it's not fail-proof
                    if (max_scissor_height == 0):
                        max_scissor_width = current_scissor_width
                        max_scissor_height = current_scissor_height

                    # We need to scale the scissor if rendering to framebuffer 0
                    if (current_framebuffer == 0):
                        function_string = "glScaledScissor"

            elif (function_name == "glDisable"):
                # Allow overriding dithering
                if (arg.intValue[0] == 0x0BD0):
                    function_string = "glOverriddenDisable"
                    args_strings.append("param_DrawState_ptr_0")

            elif (function_name == "glEnable"):
                # Allow overriding dithering
                if (arg.intValue[0] == 0x0BD0):
                    function_string = "glOverriddenEnable"
                    args_strings.append("param_DrawState_ptr_0")

            elif ((function_name == "glGetVertexAttribiv") and (arg_index == 2)):
                # XXX The trace sends intValue with isArray false
                logger.debug("Patching function %s" % function_name)
                arg.isArray = True

            elif ((function_name == "glGetActiveUniform") and (arg_index == 7)):
                # WAR: The trace sends an extra int with some index?
                continue

            elif ((function_name == "glGetActiveAttrib") and (arg_index == 7)):
                # WAR: The trace sends an extra int with some index?
                continue

            elif ((function_name == "glDrawElements") and (arg_index == 3)):
                if (not arg.isArray):
                    # When using index buffers, the last parameter can be an offset
                    # instead of an array of indices, convert to pointer to void
                    # to prevent gcc warnings
                    arg.type = gltrace_pb2.GLMessage.DataType.VOID

            elif (function_name == "glGetFloatv"):
                if (arg_index == 0):
                    is_aliased_point_size_range = True
                elif ((arg_index == 1) and (is_aliased_point_size_range)):
                    # XXX The trace sends a single float array, but the spec says two
                    #     elements
                    is_aliased_point_size_range = False
                    arg.floatValue.append(0.0)

            elif ((function_name == "glGetShaderInfoLog") or
                  (function_name == "glGetProgramInfoLog")):
                # WAR: the two last glGetShader/ProgramInfoLog arguments in the
                #      trace are ints instead array of int and array of char,
                #      convert to those
                if (arg_index == 1):
                    # Store the max length for later
                    get_shader_info_log_max_length = arg.intValue[0]
                    logger.debug("Found shader_info_log_max_length %d" % get_shader_info_log_max_length)
                if (arg_index == 2):
                    # Convert to pointer to int
                    logger.debug("WAR: glGetShaderPrecisionFormat arg %d" % arg_index)
                    arg.isArray = True
                elif (arg_index == 3):
                    # Convert to pointer to char
                    logger.debug("WAR: glGetShaderPrecisionFormat arg %d" % arg_index)
                    arg.isArray = True
                    arg.charValue.append("?" * get_shader_info_log_max_length)

            elif (function_name == "glGetAttachedShaders"):
                # WAR: The last two parameters are ints instead of pointers,
                #      convert to those and set the count (second parametre) to 1,
                #      since the result is not necessary and the trace doesn't
                #      contain it
                # XXX Alternatively we could get the size from the second argument
                #     and create arrays of that size, but the result is not used
                #     at replay time anyway so ignore it.
                if (arg_index == 1):
                    logger.debug("WAR: glGetAttachedShaders arg %d" % arg_index)
                    arg.intValue[0] = 1

                elif (arg_index == 2):
                    logger.debug("WAR: glGetAttachedShaders arg %d" % arg_index)
                    arg.isArray = True

                elif (arg_index == 3):
                    logger.debug("WAR: glGetAttachedShaders arg %d" % arg_index)
                    arg.isArray = True

            elif ((function_name == "glGetShaderPrecisionFormat")):
                # WAR: The last two parameters should be pointers but the trace
                #      makes them ints
                if ((arg_index == 2) or (arg_index == 3)):
                    logger.debug("WAR: glGetShaderPrecisionFormat arg %d" % arg_index)
                    arg.isArray = True

            elif ((function_name == "glInvalidateFramebuffer")):
                # WAR: The last two parameters should be pointers but the trace
                #      makes them ints
                if (arg_index == 2):
                    logger.debug("WAR: glInvalidateFramebuffer arg %d" % arg_index)
                    arg.isArray = True

            elif (function_name == "glGetVertexAttribPointerv"):
                # WAR: the last parameter in the trace is an INT instead of a pointer
                #      to pointer, convert to pointer to int
                if (arg_index == 2):
                    logger.debug("WAR: glGetVertexAttribPointerv arg %d" % arg_index)
                    arg.isArray = True
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

                # Always set the length pointer to zero, as we don't need it
                # and passing random pointers causes errors otherwise
                if (arg_index == 3):
                    if (len(arg.intValue) > 0):
                        arg.intValue[0] = 0
                    else:
                        arg.int64Value[0] = 0

            elif (function_name == "glVertexAttribPointerData"):
                # The C function only understands a few types, make sure we catch
                # this issue at trace generation time
                if ((arg_index == 2) and
                    # GL_BYTE, GL_UNSIGNED_BYTE, GL_SHORT, GL_UNSIGNED_SHORT, GL_FIXED, GL_FLOAT
                    (arg.intValue[0] not in [0x1400, 0x1401, 0x1402, 0x1403, 0x140C, 0x1406])):
                    raise Exception("Unhandled type 0x%x in message %s" % (arg.intValue[0], msg))

            elif ((function_name == "glTexParameteri") and (arg_index == 2)):
                # glTexParameteri has an INT as last parameter but in real life
                # it's always an ENUM
                # Switch to ENUM so it gets translated
                arg.type = gltrace_pb2.GLMessage.DataType.ENUM

            elif  (((function_name == "glTexImage2D") and (arg_index == 8)) or
                   ((function_name == "glTexSubImage2D") and (arg_index == 8)) or
                   ((function_name == "glTexImage3D") and (arg_index == 9)) or
                   ((function_name == "glTexSubImage3D") and (arg_index == 10)) or
                   ((function_name == "glCompressedTexImage2D") and (arg_index == 7)) or
                   ((function_name == "glCompressedTexSubImage2D") and (arg_index == 8))):

                # If the trace contains pointers instead of rawBytes, it means
                # the trace was generated without texture data, force all textures
                # to empty to prevent access violations when accessing stale pointers
                if ((not generate_empty_textures) and
                    ((len(arg.rawBytes) == 0) and (
                        ((len(arg.intValue) > 0) and (arg.intValue[0] != 0)) or
                        ((len(arg.int64Value) > 0) and (arg.int64Value[0] != 0))))
                     ):
                    logger.warning("Trace doesn't contain texture data for %s, forcing texture to empty" %
                        function_name)
                    logger.debug(msg)
                    # Don't just set generate_empty_textures, as some traces have
                    # normal texture data but not compressed data
                    arg.type = gltrace_pb2.GLMessage.DataType.VOID
                    arg.isArray = False
                    if (len(arg.int64Value) != 0):
                        arg.int64Value[0] = 0
                    else:
                        arg.intValue[0] = 0

                if (generate_empty_textures):
                    # Set the texture pointer to NULL
                    arg.type = gltrace_pb2.GLMessage.DataType.VOID
                    arg.isArray = False
                    arg.intValue[0] = 0

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
                # Converting from tree element to string doubles the execution time,
                # only do it in debug
                assert None is logger.debug("Getting field %s" % str(field_name))
                value = getattr(arg, field_name)

                if (len(value) == 0):
                    logger.warning("Unexpected arg %s in function %s" % (str(arg), function_name))
                else:
                    # For array values we need to do this multiple times and create
                    # a local var that will contain an array with all the translated
                    # values
                    translated_values = []
                    for single_value in value:
                        if (field_name == "boolValue"):
                            single_value = bool(single_value)
                        else:
                            single_value = int(single_value)
                        logger.debug("Looking up translation for 0x%x in %s" % (single_value, table_name))
                        # The entry will not exist eg if we are binding back the NULL object
                        # XXX This could be changed so there's a default 0-entry in all
                        #     translation tables
                        translation_table = translation_tables.get(table_name, {})
                        try:
                            translated_value = translation_table[single_value]
                            # Converting from tree element to string doubles the execution time,
                            # only do it in debug
                            assert None is logger.debug("Translated %s to %s via %s" % (str(single_value), translated_value, table_name))
                            translated_values.append(translated_value)
                        except KeyError:
                            pass

                    if (arg.isArray and (len(translated_values) > 0)):
                        logger.debug("Generating local array to hold translated values %s" % translated_values)
                        # Create a temporary variable to hold all the translations
                        # and use that one
                        # XXX Check type
                        var_name = "local_GLuint_ptr_%d" % num_allocated_vars
                        preamble_strings.append("GLuint %s[] = { %s }" % (
                            var_name,
                            string.join(translated_values, ", ")))
                        num_allocated_vars += 1
                        translated_value = var_name

            # Fall-back to the global enums for untranslated enums
            # (this can happen eg for Google's fake AttribPointerData functions,
            # but also for functions out of gles2 which are not explicitly inserted
            # at initialization time)
            # Don't use the generic lookup for return values (isArray)
            if ((translated_value is None) and (not arg.isArray) and
                    (arg.type == gltrace_pb2.GLMessage.DataType.ENUM)):
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
            # This is also used for glGetFloatv, etc so it cannot be declared
            # const
            if ((len(arg.floatValue) > 0) and (arg.isArray)):
                if ((use_assets_for_floats and
                    (len(arg.floatValue) > min_float_asset_size_in_floats)) or
                    (len(arg.floatValue) > max_float_inlined_size_in_floats)):
                    arg_name = "global_float_ptr_F"
                    asset_filename = "float_asset_%d" % num_allocated_vars

                    # Allocate one asset specifically for floats, since the pointer
                    # variable declaration is keyed off the asset variable name

                    preamble_strings.extend(allocate_asset(allocated_assets,
                                                           allocated_asset_filenames,
                                                           assets_dir,
                                                           arg_name,
                                                           asset_filename,
                                                           "float*",
                                                           "global_AAsset_ptr_F",
                                                           string.join([struct.pack("f", f) for f in arg.floatValue],""),
                                                           global_decls))

                else:
                    # XXX Change this to use the global pointer?
                    arg_name = "local_float_ptr_%d" % num_allocated_vars
                    preamble_strings.append("float %s[] = { %s }" % (
                        arg_name,
                        string.join([str(f) for f in arg.floatValue], ", ")))

                args_strings.append(arg_name)
                num_allocated_vars += 1

            # When rawbytes is set, initialized data is passed in
            # (glTexSubImage2D, glTexImage2D with BYTE, glBufferData with VOID, etc)
            # Note isArray is set to False above when NULLing textures, so ignore
            # those
            elif ((len(arg.rawBytes) > 0) and (arg.isArray)):
                if ((use_assets_for_ints and
                    (len(arg.rawBytes[0]) > min_int_asset_size_in_bytes)) or
                    (len(arg.rawBytes[0]) > max_int_inlined_size_in_bytes)):
                    asset_filename = "int_asset_%d" % num_allocated_vars

                    if (function_name == "glVertexAttribPointerData"):
                        arg_name = "global_const_unsigned_int_ptr_%d" % msg.args[0].intValue[0]

                        preamble_strings.extend(allocate_asset(allocated_assets,
                                                               allocated_asset_filenames,
                                                               assets_dir,
                                                               arg_name,
                                                               asset_filename,
                                                               "const unsigned int*",
                                                               "global_AAsset_ptr_%d" % msg.args[0].intValue[0],
                                                               arg.rawBytes[0],
                                                               global_decls))
                        # The asset will be freed when it's allocated again with
                        # that name
                        # XXX Need to free the assets at the end of the trace
                    else:
                        arg_name = "global_const_unsigned_int_ptr_I"
                        # Allocate one asset specifically for ints, since the pointer
                        # variable declaration is keyed off the asset variable name
                        preamble_strings.extend(allocate_asset(allocated_assets,
                                                               allocated_asset_filenames,
                                                               assets_dir,
                                                               arg_name,
                                                               asset_filename,
                                                               "const unsigned int*",
                                                               "global_AAsset_ptr_I",
                                                               arg.rawBytes[0],
                                                               global_decls))
                        # This is a short-lived asset only used in this GL call, could
                        # be freed after the call, but that complicates the asset
                        # variable declaration, so we just free it the next time
                        # an asset with this name is allocated
                else:
                    # XXX Change this to use the global pointer?
                    arg_name = "local_const_char_ptr_%d" % num_allocated_vars
                    preamble_strings.append("const char %s[%d] = { %s }" % (
                        arg_name,
                        len(arg.rawBytes[0]),
                        string.join([hex(ord(b)) for b in arg.rawBytes[0]], ", ")))

                args_strings.append(arg_name)
                num_allocated_vars += 1

            # When isArray is set, the parameter is passed by reference and
            # contains a return value, which is held in the xxxValue part
            # Those need to be stored in variables in case they are used
            # in the future
            # One special case is glDrawElements, where an array is passed in,
            # but with values already
            # XXX We actually don't need to initialize the arrays passed by reference
            #     can we tell the difference between glGenTextures and glDrawElements?
            # Note booleans have both len(intValue) and len(boolValue) greater
            # than zero
            # Note translated array values (eg glDeleteTextures) have already
            # been put into a single array variable, so they don't need to be
            # redeclared here
            elif ((arg.isArray) and (translated_value is None) and
                      ((len(arg.intValue) > 0) or (len(arg.boolValue) > 0) or
                       (len(arg.charValue) > 0) or (len(arg.int64Value) > 0))):

                # XXX Missing initializers for all but charvalue?
                if (len(arg.boolValue) > 0):
                    var_name = "local_boolean_ptr_%d" % num_allocated_vars
                    preamble_strings.append("GLboolean %s[%d]" % (var_name , len(arg.boolValue)))
                elif (len(arg.charValue) > 0):
                    var_name = "local_char_ptr_%d" % num_allocated_vars
                    if ("\n" in arg.charValue[0]):
                        initializer = '"\\\n  %s\\n"' % arg.charValue[0].replace("\n", "\\\n  ")
                    else:
                        initializer = '"%s"' % arg.charValue[0]
                    preamble_strings.append("GLchar %s[] = %s" % (var_name, initializer))
                elif ((len(arg.intValue) > 0) or (len(arg.int64Value) > 0)):
                    if (len(arg.intValue) > 0):
                        argIntValue = arg.intValue
                    else:
                        argIntValue = arg.int64Value
                    if (arg.type == gltrace_pb2.GLMessage.DataType.VOID):
                        var_name = "local_void_ptr_%d" % num_allocated_vars
                        # the parser patches some pointers to void from INTs to
                        # VOID
                        preamble_strings.append("GLvoid* %s[1]" % var_name)
                    else:
                        # This is used for generating texture ids, buffer ids, etc,
                        # so it needs to preserve the data across invocations,
                        # store in global variables
                        # XXX Where else is static needed?
                        # XXX This is not true for cases like glGetProgram/ShaderInfoLog
                        #     probably others?
                        # Remove the local prefix
                        var_name = "global_unsigned_int_ptr_%d" % num_allocated_vars
                        var_type = "GLuint"
                        var_size = 4
                        pack_type = "I"
                        # glDrawElements can use different element sizes, use
                        # the proper type
                        # XXX Is there any other function with different int sizes?
                        if (function_name == "glDrawElements"):

                            # GL_UNSIGNED_SHORT 0x1403
                            if (msg.args[2].intValue[0] == 0x1403):
                                var_size = 2
                                var_type = "GLushort"
                                var_name = "global_GLushort_ptr_%d" % num_allocated_vars
                                pack_type = "H"

                            # GL_UNSIGNED_BYTE 0x1401
                            elif (msg.args[2].intValue[0] == 0x1401):
                                var_type = "GLubyte"
                                var_name = "global_GLubyte_ptr_%d" % num_allocated_vars
                                var_size = 1
                                pack_type = "B"

                            else:
                                raise Exception("unhandled glDrawElements element type 0x%x" % msg.args[2].intValue[0])

                        var_size *= len(argIntValue)

                        # Using assets is specially important in the case of
                        # glDrawElements, although is not special-cased here,
                        # it will use whatever min/max check is done on integer
                        # assets
                        if ((use_assets_for_ints and
                            (var_size > min_int_asset_size_in_bytes)) or
                            (var_size > max_int_inlined_size_in_bytes)):
                            # Store in a short-lived asset if for glDrawElements index
                            # buffer and above the minimum asset size
                            var_name = "global_const_unsigned_int_ptr_I"
                            asset_filename = "int_asset_%d" % num_allocated_vars
                            # Allocate one asset specifically for ints, since the pointer
                            # variable declaration is keyed off the asset variable name
                            preamble_strings.extend(allocate_asset(allocated_assets,
                                                                   allocated_asset_filenames,
                                                                   assets_dir,
                                                                   var_name,
                                                                   asset_filename,
                                                                   "const %s*" % var_type,
                                                                   "global_AAsset_ptr_I",
                                                                   string.join([struct.pack(pack_type, i) for i in argIntValue],""),
                                                                   global_decls))
                            # This is a short-lived asset only used in this GL call, could
                            # be freed after the call, but that complicates the asset
                            # variable declaration, so we just free it the next time
                            # an asset with this name is allocated

                        else:
                            # XXX This can be moved to a local for glDrawElements
                            #     only, but would that make things harder for the
                            #     inliner?
                            global_decls.append("static %s %s[%d] = {%s}" %
                                        (var_type, var_name , len(argIntValue),
                                         string.join([str(i) for i in argIntValue], ", ")))
                args_strings.append(var_name)
                num_allocated_vars += 1

            elif ((arg.isArray) and (translated_value is None)):
                raise Exception("unhandled array argument %s for %s" % (arg, msg))

            elif (len(arg.charValue) > 0):
                # charValue with isArray set to false is only used for the
                # special case of glSetShaderSource, in which case we need
                # a pointer to pointer to const chars (const qualifier is not
                # ignored across pointers)
                if (use_assets_for_shaders):
                    asset_filename = "char_asset_%d" % num_allocated_vars
                    arg_name = "global_const_char_ptr_C"
                    # Allocate one asset specifically for chars, since the pointer
                    # variable declaration is keyed off the asset variable name
                    # Note we zero-terminate the string as required by
                    # glSetShaderSource when length is NULL
                    preamble_strings.extend(allocate_asset(allocated_assets,
                                                           allocated_asset_filenames,
                                                           assets_dir,
                                                           arg_name,
                                                           asset_filename,
                                                           "GLchar const *",
                                                           "global_AAsset_ptr_C",
                                                           arg.charValue[0] + "\0",
                                                           global_decls))
                    # glSetShaderSource requires a pointer to pointer
                    arg_name = "&%s" % arg_name
                else:
                    # XXX Change this to use the global pointer?
                    arg_name = "local_char_ptr_%d" % num_allocated_vars
                    if ("\n" in arg.charValue[0]):
                        initializer = '"\\\n  %s\\n"' % arg.charValue[0].replace("\n", "\\n\\\n  ")
                    else:
                        initializer = '"%s"' % arg.charValue[0]

                    preamble_strings.append("const GLchar* %s[] = {%s} " % (
                        arg_name,
                        initializer))

                args_strings.append(arg_name)
                num_allocated_vars += 1

            elif (len(arg.int64Value) > 0):
                if (translated_value is not None):
                    args_strings.append(str(translated_value))
                else:
                    args_strings.append("(GLvoid*) 0x%x" % ctypes.c_uint32(arg.int64Value[0]).value)

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

                values = getattr(arg, field_name)

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

            # WAR: eglCreateContext is a special case, the CONTEXT_ID value
            #      should be in the return value, but the trace actually passes
            #      it in the second parameter
            if (function_name == "eglCreateContext"):
                values = msg.args[1].intValue
                var_name = "global_EGLContext_%d" % num_allocated_vars
                var_decl = "static EGLContext %s" % var_name
                args_strings = ["param_DrawState_ptr_0"]

            else:

                values = getattr(msg.returnValue, field_name)
                # Create a new variable to hold the return value
                var_name = "global_unsigned_int_%d" % num_allocated_vars
                var_decl = "static unsigned int %s" % var_name

            # We only expect one value being returned
            assert(len(values) == 1)
            value = values[0]
            num_allocated_vars += 1
            global_decls.append(var_decl)

            table[value] = var_name
            logger.debug("Updated table %s entry %d to return value %s" %
                (table_name, value, table[value]))

            function_string = "%s=%s" % (var_name, function_string)

        logger.debug("Found return %s" % msg.returnValue)

        code.extend(preamble_strings)
        program_line = "%s(%s)" % (function_string, string.join(args_strings, ", "))
        code.append(program_line)
        if (insert_alog_after_gl_functions):
            code.append('gl_error=glGetError()')
            code.append('LOGI("0x%%x: %s", gl_error)' % program_line)
        if (insert_glfinish_after_gl_functions):
            code.append("glFinish()")
        code.extend(epilogue_strings)
        logger.debug(program_line)

        # Add draw check
        if (function_name in ['glDrawElements', 'glDrawArrays']):
            # XXX Implement drawXXX stop motion
            ## print "if (draw_count == draw_limit) { return; }"
            pass

    logger.info("Writing code")

    # Generate some global declarations only known at trace end time
    # Note some traces don't have scissor calls, so always use the maximum of both
    egl_width = max(max_viewport_width, max_scissor_width)
    egl_height = max(max_viewport_height, max_scissor_height)
    global_decls.append("static const GLsizei max_viewport_width  = %d" % egl_width)
    global_decls.append("static const GLsizei max_viewport_height = %d" % egl_height)
    global_decls.append("static const GLsizei max_scissor_width  = %d" % egl_width)
    global_decls.append("static const GLsizei max_scissor_height = %d" % egl_height)
    # These are exposed to the EGL surface creation
    global_decls.append("int egl_width  = %d" % egl_width)
    global_decls.append("int egl_height = %d" % egl_height)
    global_decls.append("GLenum gl_error = 0")

    # Generate the global declarations
    lines = []
    for decl in global_decls:
        lines.append("%s;" % decl)
    lines.append("")

    # Generate each frame
    for (frame_count, code) in enumerate(code_frames):
        lines.append("void frame%s(DrawState* param_DrawState_ptr_0)" % frame_count)
        lines.append("{")
        for line in code:
            lines.append("    %s;" % line)
        lines.append("}")

    # Generate the code that calls each frame
    lines.append("void draw(DrawState* param_DrawState_ptr_0)")
    lines.append("{")
    lines.append("    switch (param_DrawState_ptr_0->frame_limit)")
    lines.append("    {")
    for frame_index in xrange(len(code_frames)):
        lines.append("        case %d: " % frame_index)
        lines.append("            frame%d(param_DrawState_ptr_0);" % frame_index)
        lines.append("        break;")
    lines.append("        default: ")
    lines.append('            LOGI("Reached frame %d end of replay, exiting", param_DrawState_ptr_0->frame_limit);')
    lines.append('            exit(EXIT_SUCCESS);')
    lines.append("    }")
    lines.append("}")
    lines.append("")

    logger.info("Done")

    return lines

if (__name__ == "__main__"): # pragma: no cover
    ## trace_filepath = "_out/bmk_hw_layer_use_color_hw_layer.gltrace.gz"
    ## trace_filepath"_out/com.amazon.kindle.otter.gltrace.gz"
    ## trace_filepath"_out\contactsShowcaseAnimation.gltrace.gz"
    ## trace_filepath"_out\bmk_hw_layer.gltrace.gz"
    ## trace_filepath ="_out/bmk_bitmap.gltrace.gz"
    ## trace_filepath ="_out/kipo.gltrace.gz"
    ## trace_filepath ="_out/gl2morphcubeva.gltrace.gz"
    ## trace_filepath ="_out/kipo-full.gltrace"
    ## trace_filepath"_out\otter.gltrace.gz"
    ## trace_filepath ="_out/GTAVC.gltrace.gz"
    ## trace_filepath ="_out/venezia.gltrace.gz"
    ## trace_filepath ="_out/glcap.gltrace"
    ## trace_filepath ="_out/navigate-home.gltrace.gz"
    ## trace_filepath ="_out/com.amazon.tv.launcher.notextures.gltrace.gz"
    ## trace_filepath ="_out/com.amazon.tv.launcher.gltrace.gz"
    ## trace_filepath = "_out/com.vectorunit.blue-60s-textures.gltrace.gz"
    trace_filepath = "twocontexts.gltrace.gz"
    output_dir = "_out"
    gl_contexts_to_trace = None

    logging_format = "%(asctime).23s %(levelname)s:%(filename)s(%(lineno)d) [%(thread)d]: %(message)s"

    logger_handler = logging.StreamHandler()
    logger_handler.setFormatter(logging.Formatter(logging_format))
    logger.addHandler(logger_handler)
    # XXX This should be passed via parameter
    logger.setLevel(logging.INFO)

    # Param 1 is trace name
    if (len(sys.argv) > 1):
        trace_filepath = sys.argv[1]

    # Param 2 is output root directory (for assets, etc),
    if (len(sys.argv) > 2):
        output_dir = sys.argv[2]

    # Param 3 is the OpenGL context index to trace
    if (len(sys.argv) > 3):
        gl_contexts_to_trace = [int(item) for item in sys.argv[3].split(",")]

    assets_dir = os.path.join(output_dir, "assets")

    lines = glparse(trace_filepath, output_dir, assets_dir, gl_contexts_to_trace)

    for line in lines:
        print(line)
