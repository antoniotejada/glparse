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

"""!

Code deinliner.

Takes a C file with one or more functions and deinlines the code (refactors by
converting most used blocks into functions) until the iteration limit is reached
or until none of the remaining deinlining options will decrease the code size.

The realization is that any sequential code block repeated in several places can
always be factored out into a function (deinlined), given enough function parameters.

Deinlining can be seen as a dictionary compression method where functions are the
dictionary, so any caveats (np-hard, use heuristics) and approaches used for
dictionary compression can be used (suffix trees, gzip-like single-pass compression,
etc).

Limitations:
- The C parser reading the source file is very simple and whatever doesn't understand
  (variable declarations, assignments, etc) is seen as a function name, so will
  make deinlining harder.
- To ease deinlining, convert assignments into functions and instead of return
  values, use variables passed by reference.
- To workaround aliasing issues, convert sequences of pointer to pointer variable
  and that same pointer variable to single function calls.
  There's a parameter aliasing bug when a deinlined block contains both a pointer
  written to by reference and that same pointer being used directly afterwards,
  in that case the pointer will be passed as two different parameters, a pointer
  to pointer (for the reference) and a plain pointer.
  Because the plain pointer now lives in the stack, the pointer won't be modified
  by the pointer to pointer, hence the bug.

Todo/Improvements:
- More matching can be done if conditionals are introduced, so divergent code is
  possible, and the conditions passed as formal parameters. This would be similar
  to doing a diff and deciding the diff to use depending on parameters
- More matching can be done if function calls are sorted so there's a higher chance
  of a sequence of calls matching. This is normally possible many cases, but
  the sorting needs to know the sequence points that barrier the sorting

@see http://en.wikipedia.org/wiki/Longest_common_substring_problem
@see http://en.wikipedia.org/wiki/Generalised_suffix_tree

"""

import array
import logging
import operator
import re
import string
import sys

logger = logging.getLogger(__name__)

# The code is an array of arrays of strings, the first argument of each line is
# the function name, subsequent items are the arguments
# XXX Missing passing window size, increment
def deinline(trace_filepath):

    ## FUNCTION_PARAMETERS_REGEXP = re.compile(r"\s*(?P<function_name>[^(]+)\((?P<function_args>.*)\)")
    FUNCTION_PARAMETERS_REGEXP = re.compile(r"\s*(?P<function_name>[^(]+)(?P<function_args>\(.*)")
    FUNCTION_PROTOTYPE_REGEXP = re.compile(r"\s*(?P<function_name_and_return_type>[^(]+)\((?P<function_arg_type_and_names>.*)\)")

    def dump_code(frame_strings, frame_prototypes, frame_actual_parameters, frame_local_decls, global_decls):
        lines = []
        for decl in global_decls:
            lines.append(decl)
        # Add the function declarations, otherwise gcc guesses the types wrong
        # (doubles instead of floats, etc)
        lines.append("")

        # Initialize the function name to formal parameter c types to some
        # functions that are known to take multiple types have their parameters
        # type-casted and don't cause compiler error/warnings
        # XXX This is not ideal, since it's GL-specific, another option would be
        #     to provide these as function prototypes in the input file, but they
        #     would need to be parsed
        # XXX Note that using GL types forces the caller to always cast, since
        #     get_c_type_from_mangled_name only returns basic C types for immediate
        #     values
        function_formal_parameter_c_types = {
            'glDrawElements' : [ "GLenum", "GLsizei", "GLenum", "const GLvoid*" ],
            'glVertexAttribPointer' : ["GLuint", "GLint", "GLenum", "GLboolean", "GLsizei", "const GLvoid*"],
            'glTexImage2D' : ["GLenum", "GLint", "GLint", "GLsizei", "GLsizei", "GLint", "GLenum", "GLenum", "const GLvoid*" ],
            'openAndGetAssetBuffer' : ["DrawState*", "const char*", "AAsset**", "const void**"],
            'glDiscardFrameBufferEXT' : ["GLenum", "GLsizei", "const GLenum*"]
        }
        for (frame_index, frame_string) in enumerate(frame_prototypes):
            # Add the prototypes to the code
            lines.append("%s;" % frame_prototypes[frame_index])

            # Generate the list of formal parameter types for this function to
            # be used later whenever actual parameter casting is required
            m = FUNCTION_PROTOTYPE_REGEXP.match(frame_string)
            function_name = m.group('function_name_and_return_type').split(" ")[-1]
            function_type_and_formal_parameters = m.group('function_arg_type_and_names').strip()
            # This will be empty if there are no parameters
            if (function_type_and_formal_parameters != ""):
                function_type_and_formal_parameters = function_type_and_formal_parameters.split(",")
                function_formal_parameter_c_types[function_name] = []
                assert None is logger.debug("Building c types for prototype %s" % function_name)
                for param_index, formal_parameter in enumerate(function_type_and_formal_parameters):
                    formal_parameter_mangled_name = formal_parameter.split(" ")[-1]
                    formal_parameter_c_type = get_c_type_from_mangled_name(formal_parameter_mangled_name)
                    function_formal_parameter_c_types[function_name].append(formal_parameter_c_type)
                assert None is logger.debug("Generated formal parameter c types for %s %s" %
                                            (function_name, function_formal_parameter_c_types[function_name]))

        lines.append("")
        # Add the function definitions
        for (frame_index, frame_string) in enumerate(frame_strings):
            lines.append("%s" % frame_prototypes[frame_index])
            lines.append("{")
            # Note that only the original frames have local declarations, deinlined
            # functions don't create new ones.
            if (frame_index < len(frame_local_decls)):
                for line in frame_local_decls[frame_index]:
                    lines.append("    %s" % line)
            for c_index, c in enumerate(frame_string):
                # Don't assume all functions have parameters, as generated functions
                # can have all parameters removed
                if ((len(frame_actual_parameters[frame_index][c_index]) > 0) and
                    (frame_actual_parameters[frame_index][c_index][0] == "-")):
                    lines.append("    %s" % char_to_function[c])
                elif ((len(frame_actual_parameters[frame_index][c_index]) > 0) and
                      (frame_actual_parameters[frame_index][c_index][0] == "void")):
                    lines.append("    %s();" % char_to_function[c])
                elif (char_to_function[c] == "switch"):
                    # Don't semi-colon terminate switches
                    lines.append("    %s(%s)" % (char_to_function[c], string.join(frame_actual_parameters[frame_index][c_index], ", ")))
                else:
                    # Look for the callee function and add type casting if the
                    # actual parameter and formal parameter types differ
                    # Some OpenGL functions take integers or pointers indistinctly
                    # (eg glDrawElements), a casting is needed to avoid compiler
                    # errors when warnings are treated as errors
                    # Get the formal parameter type by extracting the formal parametre
                    # type name and unmangling
                    # Some functions
                    casted_actual_parameters = []
                    # Leaf functions don't have prototypes, no need to do typecasting
                    # for those (leaf functions that should be type casted are done
                    # initializing function_formal_parameter_c_types)
                    formal_parameter_c_types = function_formal_parameter_c_types.get(char_to_function[c], None)
                    assert None is logger.debug("Casting %s actual parameters %s to formal c types %s " %
                                                (char_to_function[c],
                                                 repr(frame_actual_parameters[frame_index][c_index]),
                                                 repr(formal_parameter_c_types)))
                    for actual_param_index, actual_parameter in enumerate(frame_actual_parameters[frame_index][c_index]):
                        if (formal_parameter_c_types is None):
                            # Don't even try to get the actual_parameter_c_type
                            # since this may be a function whose parameters don't
                            # understand (EXIT_SUCCESS, etc)
                            formal_parameter_c_type = None
                            actual_parameter_c_type = None
                        else:
                            actual_parameter_c_type = get_c_type_from_mangled_name(actual_parameter)
                            formal_parameter_c_type = formal_parameter_c_types[actual_param_index]
                        assert None is logger.debug("Type casting for parameter %d, %s vs. %s" %
                                                    (actual_param_index,
                                                     actual_parameter_c_type,
                                                     formal_parameter_c_type))
                        if (formal_parameter_c_type != actual_parameter_c_type):
                            casted_actual_parameters.append("(%s) %s" % (formal_parameter_c_type, actual_parameter))
                        else:
                            casted_actual_parameters.append("%s" % actual_parameter)

                    lines.append("    %s(%s);" % (char_to_function[c], string.join(casted_actual_parameters, ", ")))
            lines.append("}")
            lines.append("")

        return lines

    def get_c_type_from_mangled_name(mangled_name):
        """!
        Extract a literal (integer, float, enum or string) or the string of space
        separated qualifiers plus type name from a mangled variable name.

        Mangled name are like
            [&]?[global|local|param][_type]+_NNNN[\[NNN\]]?
        Eg
            global_char_ptr
            local_unsigned_int
            &param_AAssetManager_ptr

        @todo check for more complex indexing
        """

        # See if this is a mangled variable name or a literal
        if (re.match(r"(.?global_|.?local_|.?param_).*", mangled_name) is None):
            # If it doesn't match a mangled variable name, it has to be a literal
            # (integer, float, enum or string)
            if (mangled_name[0] == '"'):
                c_type = "const char *"
            elif (mangled_name[0] == "'"):
                c_type = "char"
            elif (mangled_name.startswith("GL_")):
                # XXX Should this trap other enums like EXIT_SUCCESS?
                c_type = "GLenum"
            else:
                try:
                    i = int(mangled_name)
                    c_type = "int"
                except ValueError:
                    try:
                        i = int(mangled_name, 16)
                        c_type = "unsigned int"

                    except ValueError:
                        f = float(mangled_name)
                        c_type = "float"
        else:

            mangles = mangled_name.split("_")

            # XXX We should probably accept ptr anywhere in the mangled name (eg
            # ptr_int_ptr)
            c_types = []
            # Ignore first and last mangles (param/global/local and the index)
            for mangle in mangles[1:-1]:
                if (mangle == "ptr"):
                    c_types.append("*")
                else:
                    c_types.append(mangle)

            # Using address-of operator adds an extra indirection
            if (mangles[0].startswith("&")):
                c_types.append("*")

            # XXX This should also accept "*" for completeness, but note that
            #     then you can have complex prefixes like *&ptr and the above
            #     simple startswith needs changing

            # Using content-of operator removes one indirection
            if (mangles[0].startswith("*")):
                c_types.remove("*")

            # Using index-of operator removes one indirection
            if (mangles[-1].endswith("]")):
                c_types.remove("*")

            c_type = string.join(c_types, " ")

        return c_type;

    def get_mangled_type_from_mangled_name(mangled_name):
        c_type = get_c_type_from_mangled_name(mangled_name)

        return c_type.replace(" ", "_").replace("*", "ptr")


    def parse_c_function_call(line):
        # Split into function and arguments
        # XXX This doesn't work for multiline
        # XXX This breaks switch indentation (case, break and instructions
        #     are set to the same indentation)

        m = FUNCTION_PARAMETERS_REGEXP.match(line)
        if (m is not None):
            function_name = m.group('function_name').strip()
            function_args_string = m.group('function_args').strip()

        if ((m is not None) and (function_name not in ['switch', 'if'])):

            function_args = []

            # Remove parenthesis/type casts
            # XXX We would still like to preserve
            #     (const void**) casts when invoking openAndGetAssetBuffer
            #     (void*) 0x0
            paren_nest_level = 0
            inside_quotes = False
            arg = ""
            for c in function_args_string:
                append_arg = False
                if ((c == '"') or inside_quotes):
                    arg = arg + c
                    if (c == '"'):
                        if (inside_quotes):
                            append_arg = True

                        inside_quotes = not inside_quotes

                elif (c == "("):
                    paren_nest_level += 1

                elif (c == ")"):
                    append_arg = (paren_nest_level == 1)
                    paren_nest_level -= 1

                elif (c == ","):
                    append_arg = True

                elif (c.isspace()):
                    pass

                elif (paren_nest_level == 1):
                    arg = arg + c

                if ((append_arg) and (arg != "")):
                    function_args.append(arg)
                    arg = ""

            # Set functions with no arguments to void to differentiate
            # from non-functions
            if (len(function_args) == 0):
                function_args = ["void"]

            assert None is logger.debug("Found function %s args %s call %s" %
                                        (function_name, function_args, repr(line)))

        else:
            assert None is logger.debug("Found assignment, comments... %s" % repr(line))
            # XXX This is passing comments as functions which will make
            #     harder to deinline

            # Pass non-function calls verbatim
            function_name = line
            # XXX This is a hack so we don't cause lack of sync between
            #     lists and lists of lists when a list of lists contains
            #     an empty list
            function_args = ["-"]

        return function_name, function_args

    def parse_c_file(filename, frames, frame_prototypes, frame_local_decls, global_decls):
        """!
        Parse a C file and return a list of functions, function prototypes and
        global declarations.

        @todo The parser should probably be more robust, or the code should
              be given already parsed or we should use pycparser or clang's
              Python bindings, but the deinliner doesn't support complex code
              anyway.

        @see https://pypi.python.org/pypi/clang
        @see https://pypi.python.org/pypi/pycparser
        """
        LOCAL_DECLARATION_REGEXP = re.compile(r"(?P<local_type>.*?)(?P<local_name>local_[^=]*)=(?P<local_value>.*);$")
        with open(filename, "r") as f:

            brace_nest_level = 0
            for line in f:

                # Ignore first-level braces and tag function end if needed
                line = line.rstrip()
                if (line == ""):
                    assert None is logger.debug("Found empty line")

                elif (line[0] == "{"):
                    brace_nest_level += 1
                    if (brace_nest_level == 1):
                        frame = []
                        function_decls = []
                        frame_prototypes.append(prev_line)
                        assert None is logger.debug("Found function prototype %s" % repr(prev_line))
                        if (len(frames) == 0):
                            # Remove the last global_decl, as it's the prototype
                            # of the first function
                            global_decls.pop()

                    assert None is logger.debug("Found opening brace %s" % repr(line))

                elif (line[0] == "}"):
                    assert None is logger.debug("Found closing brace %s" % repr(line))
                    brace_nest_level -= 1
                    assert(brace_nest_level >= 0)
                    if (brace_nest_level == 0):
                        # Finish this frame and append
                        frames.append(frame)
                        frame_local_decls.append(function_decls)

                else:
                    line = line.lstrip()
                    if (brace_nest_level == 0):
                        assert None is logger.debug("Found global declaration %s" % repr(line))
                        prev_line = line
                        # Append to the global declarations until we've found a frame
                        if (len(frames) == 0):
                            global_decls.append(line)

                    elif (LOCAL_DECLARATION_REGEXP.match(line) is not None):
                        # XXX This assumes that the local declarations can be
                        #     moved above the code. This is the case with the
                        #     trace generated one since it uses SSA names, but
                        #     ideally it should only move declarations that are safe
                        #     to move.
                        logger.debug("Found local declaration %s" % repr(line))
                        function_decls.append(line)

                    else:
                        function_name, function_args = parse_c_function_call(line)

                        frame.append([function_name] + function_args)


    def build_histogram_slow(substring_histogram, frame_strings): # pragma: no cover
        # Don't bother with very short substrings
        min_substring_length = 2
        substring_hash_histogram = {}
        best_substring_and_factor = [ 0, None ]
        for (frame_index, frame_string) in enumerate(frame_strings):
            frame_string_len = len(frame_string)
            for substring_length in xrange(min_substring_length, frame_string_len + 1):
                # Iterate through all the start positions for the substrings of
                # length substring_length

                # Keep track of where the previous start position of a given
                # substring was, which allows discarding overlaps in order to
                # prevent double-counting when evaluating the compresion ratio.

                # This is reset on every new substring length because:
                # - overlaps only happen of a block of code with itself (so
                #   necessarily the code it overlaps with has to have the same
                #   length and content - the content matching part is achieved
                #   by storing the start for each substring)
                # - overlap can't happen across frames
                substring_hash_prev_start = {}
                for i in xrange(0, frame_string_len - substring_length + 1):
                    # Using a hash instead of the substring to index the dictionary
                    # consumes less memory for keys, but it's still too much for gtavc
                    # Note Python's hash causes collisions. Adding the substring_length
                    # is enough to remove those.
                    ##substring_hash = (hash(frame_string[i:i+substring_length]) + substring_length)
                    substring_hash = frame_string[i:i+substring_length]
                    try:
                        # If this is already in the histogram, increment if this substring
                        # doesn't overlap another occurrence of itself, so the compression
                        # factor calculated later doesn't double count
                        # By construction of the algorithm, the substring will only
                        # overlap if it starts inside the previous start of this substring
                        prev_start = substring_hash_prev_start.get(substring_hash, -substring_length)
                        if (i >= prev_start + substring_length):
                            substring_hash_histogram[substring_hash][0] += 1
                            substring_hash_prev_start[substring_hash] = i

                    except KeyError:
                        substring_hash_histogram[substring_hash]= [1,
                                                                   frame_string,
                                                                   i,
                                                                   substring_length]
                        substring_hash_prev_start[substring_hash] = i

        # Look for the best compression factor
        max_compression = 0
        best_substring_and_count = None
        for (substring_hash, (count, frame_string, start, length)) in substring_hash_histogram.iteritems():
            ##if (substring_and_count[1] > 1):
            ##    print "----------------- %d -------------" % substring_and_count[1]
            ##    for c in substring_and_count[0]:
            ##        print "    %s" % char_to_function[c]
            # The compression achieved is
            #   + number of lines factored out * number of invocations
            #   - number of lines factored out (for the function code)
            #   - number of invocations (for the function calls)
            this_compression = length * (count - 1) - count
            if (max_compression < this_compression):
                best_substring_and_count = (frame_string[start:start+length], count)
                max_compression = this_compression

        if (best_substring_and_count is not None):
            substring_histogram[best_substring_and_count[0]] = best_substring_and_count[1]

    def build_histogram(substring_histogram, frame_strings):

        def find_insertion_point(suffix_array, substring):
            index = 0
            min = 0
            max = len(suffix_array) - 1
            while True:
                if (max < min):
                    return min
                index = (min + max) // 2

                frame_index_and_start = suffix_array[index]

                this_suffix_frame_index = frame_index_and_start >> 16
                this_suffix_start = (frame_index_and_start & 0xFFFF)

                r = frame_strings[frame_index_and_start >> 16][frame_index_and_start & 0xFFFF:]
                comp = cmp(r, substring)
                if (comp < 0):
                    min = index  + 1
                elif (comp > 0):
                    max = index - 1
                else:
                    return index

        def build_suffix_array(suffix_array):
            for frame_index, frame_string in enumerate(frame_strings):
                frame_string_length = len(frame_string)
                for start in xrange(frame_string_length):
                    assert(frame_index <= 0xFFFF)
                    assert(start <= 0xFFFF)
                    # Insert sorted by char
                    index = find_insertion_point(suffix_array, frame_string[start:])

                    suffix_array.insert(index, (frame_index << 16) | start)

        assert None is logger.debug(frame_strings)

        # Create a suffix array containing the frame the string came from and the
        # start position of the string, packed in a 32bit value
        logger.debug("Creating suffix array")
        suffix_array = array.array("L")
        build_suffix_array(suffix_array)

        if (__debug__):
            logger.debug(suffix_array)
            for frame_index_and_start in suffix_array:
                frame_index = frame_index_and_start >> 16
                start = frame_index_and_start & 0xFFFF
                logger.debug("%s (%d,%d)" % (repr(frame_strings[frame_index][start:]), frame_index, start))

        # The suffix array can be empty if all the functions in the window are
        # empty, the code below assumes the suffix array is not emtpy, so
        # ignore the histogram and move to the next window
        if (len(suffix_array) == 0):
            logger.debug("Suffix Array empty, ignoring histogram")
            return

        logger.debug("Building histogram with suffix array")

        # Find the substring with the largest compression factor
        #   N = Non overlapped occurrences of the substring
        #   L = Length of the substring
        #   factor = N * L - N - L
        # Given a suffix array split by frame, we can find the substring with the
        # largest compression factor by walking each character of each entry
        # of the array
        # 1. If this character in the previous entry match, increment the count
        #    for the current unless this is an overlap.
        # 2. If they don't match, it means that the previous entry was the last
        #    occurrence of the substring of that length and we can remove it from
        #    the histogram unless it's the best compression factor

        # Previous start of the substring of length l
        substring_length_prev_starts = [ [] for i in xrange(len(frame_strings)+1)]
        # Number of occurrences of the substring of length l
        substring_length_histogram = [ ]
        best_substring_and_factor = [ (0,0,0), 0]
        suffix_array_index = 0

        # Setup next suffix information for the first iteration
        next_frame_index_and_start = suffix_array[0]
        next_frame_index = next_frame_index_and_start >> 16
        next_start = next_frame_index_and_start & 0xFFFF
        next_frame_string_length = len(frame_strings[next_frame_index])
        # Setup this suffix information for the first iteration
        frame_index = 0
        start = 0
        frame_string_length = 0

        for frame_index_and_start in suffix_array:
            # For every substring, increment the number of occurrences if it doesn't
            # overlap the previous occurrence

            # Update prev suffix information
            prev_frame_index = frame_index
            prev_start = start
            prev_frame_string_length = frame_string_length

            # Update this suffix information
            frame_index = next_frame_index
            start = next_start
            frame_string_length = next_frame_string_length

            # Update next suffix information
            try:
                next_frame_index_and_start = suffix_array[suffix_array_index + 1]
                next_frame_index = next_frame_index_and_start >> 16
                next_start = next_frame_index_and_start & 0xFFFF
                next_frame_string_length = len(frame_strings[next_frame_index])
            except IndexError:
                next_frame_string_length = 0

            assert None is logger.debug("-- %s (%d,%d) --" % (repr(frame_strings[frame_index][start:]), frame_index, start))
            assert None is logger.debug("prev: %d,%d [%d]" % (prev_frame_index, prev_start, prev_frame_string_length))
            assert None is logger.debug("next: %d,%d [%d]" % (next_frame_index, next_start, next_frame_string_length))

            substring_end = start + 1
            prev_suffix_char_matches = True
            # Go through all substrings from the current suffix start to the end
            # of the suffix
            while (substring_end <= frame_string_length):
                substring_len = substring_end - start
                absolute_index = substring_len - 1
                this_char = frame_strings[frame_index][substring_end - 1]

                # If this char doesn't match the one in the same position of the
                # previous suffix, it means that we are done with all the substrings
                # length (substring_end - start) onwards.
                # Delete all temporary information about them, but don't bother
                # doing this if it has already been done for this suffix
                if (prev_suffix_char_matches and
                    ((prev_start + absolute_index >= prev_frame_string_length) or
                     (frame_strings[prev_frame_index][prev_start + absolute_index] != this_char))):

                    assert None is logger.debug("Resetting dictionaries from length %d onwards" % absolute_index)
                    del substring_length_histogram[absolute_index:]
                    # XXX This is not worth creating some indexing structure because
                    #     it's only 1.29% of the total time on kipo
                    for substring_length_prev_start in substring_length_prev_starts:
                        del substring_length_prev_start[absolute_index:]

                    prev_suffix_char_matches = False

                # If this char doesn't match the previous or next suffixes, it
                # means that this and any larger substrings only match once, so
                # ignore them, because single occurrences will never be worth
                # replacing (the compression factor would be negative because of
                # having to add the function body plus the function call)
                if (((next_start + absolute_index >= next_frame_string_length) or
                     (frame_strings[next_frame_index][next_start + absolute_index] != this_char)) and
                     not prev_suffix_char_matches):
                    if (__debug__):
                        logger.debug("Early exiting")
                        try:
                            logger.debug("prev is %s vs. %s" % (
                                frame_strings[prev_frame_index][prev_start + substring_end - start - 1],
                                frame_strings[frame_index][substring_end-1]))

                        except IndexError:
                            pass

                        try:
                            logger.debug("next is %s vs. %s" % (
                                frame_strings[next_frame_index][next_start + substring_end - start - 1],
                                frame_strings[frame_index][substring_end-1]))

                        except IndexError:
                            pass
                    break

                # substrings appear from the end first, so this substring has
                # to be len before the previous
                assert None is logger.debug("%s [%d,%d:%d]" % (frame_strings[frame_index][start:substring_end], frame_index, start, substring_end))

                assert(len(substring_length_prev_starts[frame_index]) >= absolute_index)
                if (absolute_index == len(substring_length_prev_starts[frame_index])):
                    substring_length_prev_starts[frame_index].append(start - substring_len)

                substring_prev_start = substring_length_prev_starts[frame_index][absolute_index]

                if (abs(start - substring_prev_start) >= substring_len):
                    substring_length_prev_starts[frame_index][absolute_index] = start
                    assert(len(substring_length_histogram) >= absolute_index)
                    if (absolute_index == len(substring_length_histogram)):
                        # No need to check against best if this is the first time
                        # it appears (a single occurrence substring is never a
                        # best substring), will be checked once it's over 1
                        # occurrences
                        substring_length_histogram.append(1)

                    else:
                        substring_length_histogram[absolute_index] += 1
                        assert None is logger.debug("%s count is now %d" % (
                            frame_strings[frame_index][start:substring_end],
                            substring_length_histogram[absolute_index]))
                        # factor = N * L - N - L = N * (L - 1) - L
                        this_factor = (substring_length_histogram[absolute_index] * (substring_len - 1) -
                                       substring_len)

                        if (best_substring_and_factor[1] < this_factor):
                            assert None is logger.debug("Replaced %s factor %d with %s factor %d" %
                                (frame_strings[best_substring_and_factor[0][0]][best_substring_and_factor[0][1]:best_substring_and_factor[0][2]],
                                 best_substring_and_factor[1],
                                 frame_strings[frame_index][start:substring_end],
                                 this_factor))
                            best_substring_and_factor[0] = (frame_index, start, substring_end)
                            best_substring_and_factor[1] = this_factor

                else:
                    assert None is logger.debug("%s [%d:] overlaps [%d:]" %
                            (frame_strings[frame_index][start:substring_end],
                             start,
                             substring_prev_start))

                substring_end += 1

            suffix_array_index += 1
            assert None is logger.debug("best: %s factor %d" % (
                                 frame_strings[best_substring_and_factor[0][0]][best_substring_and_factor[0][1]:best_substring_and_factor[0][2]],
                                 best_substring_and_factor[1]))
            assert None is logger.debug("histogram: %s" % substring_length_histogram)
            assert None is logger.debug("prev_start: %s" % substring_length_prev_starts)

        # Put the best string in the histogram
        if (best_substring_and_factor[0] is not None):
            # XXX Setting the right count is overkill, but helps comparing vs.
            #     previous, remove when this algorithm is robust
            #   factor = N * L - N - L = N * (L - 1) - L -> N = (factor + L) / (L - 1)
            substring = frame_strings[best_substring_and_factor[0][0]][best_substring_and_factor[0][1]:best_substring_and_factor[0][2]]
            count = ((best_substring_and_factor[1] + len(substring)) / (len(substring) - 1))
            substring_histogram[substring] = count

    def replace_code(frame_strings, frame_prototypes, substring):
        """!
        Replace substring in frame_strings, appending the new code as a new frame_string
        and frame_prototype
        """

        def replace_caller_occurrences_and_gather_actual_parameters(frame_strings,
                                                                    frame_actual_parameters,
                                                                    substring,
                                                                    all_actual_parameters,
                                                                    best_substring_parameters,
                                                                    best_substring_function_char):

            """!
            Replace the occurrences of substring in frame_strings and gather all the
            actual parameters, the common parameters and the formal parameters for
            the best substring function

            @param[in] frame_strings *list* of strings for all the frames
            @param[in] frame_actual_parameters *list* with actual parameters for
                       all the frames
            @param[in] substring Best substring to replace in the frame_strings
            @param[out] all_actual_parameters *list* of items referencing elements
                        from in frame_actual_parameters
            @param[out] best_substring_parameters *list* with the Initial formal
                        parameters of the substring function (all the actual parameters),
                        calculated from the first occurrence of substring found
                        in frame_strings
            @param[in] best_substring_function_char *unichar* assigned to the new
                       function for substring.
            """

            best_substring_len = len(substring)
            # Go through each frame, see if the best substring occurs there, if so
            # collect the parameters used on every instruction in the occurrence and
            # replace the occurrence with a function call to the substring's new
            # function (note the best substring can appear several times in a single
            # frame)
            # XXX This takes 50% of the time on small window runs, should be able
            #     to use the suffix array to at least find all the positions to
            #     substitute, optionally removing them and appending the new
            #     substring incrementally to the suffix array

            for (frame_index, frame_string) in enumerate(frame_strings):
                i = 0
                frame_string_len = len(frame_string)
                # Speculatively collect frame_string and its actual parameters into
                # new_frame_string in case frame_string contains the substring
                new_frame_string = []
                new_frame_actual_parameters = []
                old_frame_actual_parameters = frame_actual_parameters[frame_index]
                while (i < frame_string_len):
                    # Don't bother doing a substring comparison if this frame cannot
                    # fit the substring
                    if ((i + best_substring_len > frame_string_len) or
                        (substring != frame_string[i:best_substring_len+i])):
                        # The substring doesn't start in this instruction of the frame,
                        # speculatively add this instruction to the new frame in case
                        # the substring is later found (or was already found) in this
                        # frame and we need to replace the call-sites
                        new_frame_string.append(frame_string[i])
                        new_frame_actual_parameters.append(old_frame_actual_parameters[i])
                        i += 1

                    else:
                        # The substring appears in this frame, gather the parameters
                        # used in this occurrence, replace the occurrence with a call
                        # to the substring's new function

                        this_best_substring_parameters = old_frame_actual_parameters[i:best_substring_len+i]
                        # Flatten all the actual parameters into a single dimension
                        # list
                        actual_parameters = [param for params in this_best_substring_parameters for param in params]
                        if (len(best_substring_parameters) == 0):
                            # Initially the new function takes as parameters each parameter
                            # of each function in the code being replaced, this will
                            # be optimized below to remove the parameters that are common
                            # across call-sites
                            # The code and actual parameters are "the same" in all
                            # occurrences, it's enough with setting this to the first
                            # occurrence found, common parameters will be properly
                            # removed later
                            # XXX There's an innocuous corner case that causes
                            #     the trace to be different depending on which
                            #     substring occurrence is used: when the occurrences
                            #     contain invocations to functions taking void*
                            #     parameters, it can happen that the substring
                            #     is invoked with an int* in one occurrence and
                            #     with a char* in another.
                            #     This happens with glVertexAttribPointerData,
                            #     glVertexAttribPointer,....
                            #     It's not clear if this should be fixed in the
                            #     code generator so it does a casting to void*,
                            #     or here so it assumes that multiple types
                            #     mean void*
                            #     This issue is minor because it just causes a
                            #     compiler warning because of mixing pointer types.
                            best_substring_parameters.extend(this_best_substring_parameters)

                        new_frame_actual_parameters.append(actual_parameters)
                        # Keep a reference to those so we can remove the parameters
                        # that are common
                        all_actual_parameters.append(actual_parameters)

                        new_frame_string.append(best_substring_function_char)

                        i += best_substring_len

                frame_strings[frame_index] = string.join(new_frame_string, "")
                frame_actual_parameters[frame_index] = new_frame_actual_parameters

        def optimize_caller_actual_parameters(all_actual_parameters, actual_parameter_indices):
            """!
            Find an optimized actual parameter set and replace all the call-sites
            with that set

            @param[in,out] all_actual_parameters *list* of lists with parameter names
                           for each occurrence of substring in frame_strings
                           Each list is actually a reference to frame_actual_parameters
                           for the new function cal
            @param[out] actual_parameter_indices *list* of mappings from actual to
                       formal parameter or -1 if that actual parameter is common
                       across invocations and doesn't have a formal parameter
                       The index can make reference to a previous parameter in
                       case the formal parameter is not required because it was
                       coalesced.
                       Non -1 indices appear in the list monotonically increasing,
                       but not tightly packed either because there were previous
                       parameters common across invocations or coalesced (in both
                       cases, that parameter index is skipped)
            """
            # Go through all the actual parameters (the actual parameters of each
            # call-site), remove parameters that are common across all call-sites,
            # coalesce identical parameters into a single actual parameter

            # Initialize the actual_parameter_indices to the unoptimized default
            # This allows selectively removing optimizations
            actual_parameter_indices.extend(xrange(len(all_actual_parameters[0])))

            assert None is logger.debug("actual_parameter_indices after initialization %s" %
                                actual_parameter_indices)

            # Flag common parameters in actual_parameter_indices as -1
            for param_index in actual_parameter_indices:
                param = all_actual_parameters[0][param_index]
                is_common = True
                for actual_parameters in all_actual_parameters[1:]:
                    if (actual_parameters[param_index] != param):
                        is_common = False
                        break

                # Note that local variables or parameters still need to be passed
                # as parameters even if they are common to all callers
                # XXX This could also do aliasing avoidance for the case described
                #     above by replacing aliased parameters (a variable and a pointer
                #     to it) with a reference to the variable and the pointer to
                #     the variable
                # XXX The regexp check could be compiled, but it's not even 0.1%
                # XXX The regexp check could be done before checking is_common
                if (is_common and not (re.match(".?local_|.?param", param))):
                    actual_parameter_indices[param_index] = -1

            assert None is logger.debug("actual_parameter_indices after common detection %s" %
                                actual_parameter_indices)

            # Coalesce all parameters that are the same as a previous one in
            # all the occurrences
            for param_index in actual_parameter_indices:
                if (param_index != -1):

                    param = all_actual_parameters[0][param_index]

                    # An actual parameter can be coalesced to a previous one
                    # if they have matching names in this and the other of the
                    # best substring occurrences (the names need to match inside
                    # the same substring occurrence, but not across substring occurrences)
                    # Eg for best substring occurrence 0
                    #   a(param_int_0[0], param_int_1[1], param_int_0[2]);
                    # and best substring occurrence 1
                    #   a(param_int_2[0], param_int_3[1], param_int_2[2]);
                    # parameter index [2] can be coalesced into parameter index [0]
                    # so the new function only needs to take two parameters, not
                    # three

                    # Check if this parameter's name matches a previous parameter
                    # in this substring occurrence
                    for prev_param_index in actual_parameter_indices[0:param_index - 1 + 1]:
                        if (prev_param_index != -1):
                            is_coalesceable = False
                            logger.debug("Coalesce testing %s vs %s" %
                                                 (all_actual_parameters[0][param_index],
                                                  all_actual_parameters[0][prev_param_index])
                                                 )
                            if (param == all_actual_parameters[0][prev_param_index]):
                                is_coalesceable = True
                                # Check if the same parameter indices also match in
                                # all the other substring occurrences
                                for actual_parameters in all_actual_parameters[1:]:
                                    logger.debug("Coalesce testing %s vs %s" %
                                                 (actual_parameters[param_index],
                                                  actual_parameters[prev_param_index])
                                                 )
                                    if (actual_parameters[param_index] != actual_parameters[prev_param_index]):
                                        is_coalesceable = False
                                        break

                            if (is_coalesceable):
                                # Flag as coalesceable to prev_param_index
                                assert None is logger.debug("Coalescing parameter %s[%d] into %s[%d]" %
                                                           (all_actual_parameters[0][param_index],
                                                            param_index,
                                                            all_actual_parameters[0][prev_param_index],
                                                            prev_param_index))
                                assert(prev_param_index != param_index)

                                # coalesce to the previous occurrence
                                actual_parameter_indices[param_index] = prev_param_index
                                break

            assert None is logger.debug("actual_parameter_indices after coalescing %s" % repr(actual_parameter_indices))

            # Delete common parameters and coalesceable parameters, starting from
            # the end to prevent indices from going out of sync
            actual_parameter_index_index = len(actual_parameter_indices) - 1
            for actual_parameter_index in reversed(actual_parameter_indices):
                if ((actual_parameter_index == -1) or
                    (actual_parameter_index != actual_parameter_index_index)):
                    if (actual_parameter_index == -1):
                        assert None is logger.debug("Removing constant parameter %s" %
                                                    all_actual_parameters[0][actual_parameter_index_index])
                    else :
                        assert None is logger.debug("Removing coalesced parameter %s[%d]" %
                                                    (all_actual_parameters[0][actual_parameter_index_index],
                                                     actual_parameter_index_index))
                    # The parameter was coalesced or is constant, can be deleted
                    # from the actual parameters
                    for actual_parameters in all_actual_parameters:
                        del actual_parameters[actual_parameter_index_index]

                actual_parameter_index_index -= 1

            # In case all the actual parameters were removed, add a void parameter
            # at the end to prevent going out of sync when actual parameters are
            # flattened if this function call is ever deinlined
            # XXX Actually, fix the parameter handling so it deals properly with
            #     empty sublists
            if (len(all_actual_parameters[0]) == 0):
                for actual_parameters in all_actual_parameters:
                    actual_parameters.append("void")

            assert None is logger.debug("Actual parameters are %s" % all_actual_parameters)

        def gather_callee_actual_and_formal_parameters(actual_parameter_indices,
                                                       best_substring_actual_parameters,
                                                       best_substring_formal_parameters):
            """!
            Gather the formal parameters, replace the substring's non-common
            actual parameters with the formal parameters, leave the common actual
            parameters the same, coalesce parameters in the same invocation that
            refer to the same parameter

            @param[out] actual_parameter_indices *list* of mappings from actual to
                       formal parameter or -1 if that actual parameter is common
                       across invocations and doesn't have a formal parameter
                       The index can make reference to a previous parameter in
                       case the formal parameter is not required because it was
                       coalesced.
                       Non -1 indices appear in the list monotonically increasing,
                       but not tightly packed either because there were previous
                       parameters common across invocations or coalesced (in both
                       cases, that parameter index is skipped)

            @param[in,out] best_substring_actual_parameters *list* of the actual
                        parameters for each line in the best substring
            @param[in,out] frame_formal_parameters *list* of formal parameters for
                       the best_substring function
            """

            # Update the new function body to use formal parameters for the non-common
            # actual parameters, the common ones don't need to be passed as parameters
            param_flat_index = 0
            formal_param_count = 0
            actual_param_index_to_formal = {}
            # Allocate actual parameters for each function call inside the new
            # function body
            for params in best_substring_actual_parameters:
                for param_index, param in enumerate(params):
                    # If this parameter is not common, swap it with a formal parameter
                    actual_param_index = actual_parameter_indices[param_flat_index]
                    if (actual_param_index != -1):
                        # Translate from parameter indices with gaps to parameter
                        # indices with no gaps
                        formal_param_index = actual_param_index_to_formal.get(actual_param_index, formal_param_count)
                        # Prefix the parameter name with param_ so any code using it
                        # is never regarded as a common parameter and always passed
                        # as actual parameter
                        params[param_index] = "param_%s_%d" % (
                            get_mangled_type_from_mangled_name(param),
                            formal_param_index)

                        # Only add non-coalesced parameters to the formal parameters
                        if (param_flat_index == actual_param_index):
                            # Append this formal parameter
                            param_type_and_name = "%s %s" % (get_c_type_from_mangled_name(param),
                                                             params[param_index])
                            best_substring_formal_parameters.append(param_type_and_name)
                            actual_param_index_to_formal[actual_param_index] = formal_param_count
                            formal_param_count += 1

                    param_flat_index += 1


        def coalesce_aliased_occurrences(all_actual_parameters,
                                         best_substring_actual_parameters,
                                         best_substring_formal_parameters):
            """!
            Coalesce in a pointer-aliasing aware way
            This is necessary because eg in
              openAndGetAssetBuffer(param_DrawState_ptr_0, "int_asset_24", &global_AAsset_ptr_I, &global_const_unsigned_int_ptr_I);
              glTexImage2D(GL_TEXTURE_2D, 0, 6408, 16, 16, 0, GL_RGBA, GL_UNSIGNED_BYTE, global_const_unsigned_int_ptr_I);
            which can be deinlined as
              void subframe(p1, filename, ppAsset, ppI, pI)
                 openAndGetAssetBuffer(..., ppI)
                 glTexImage(...., pI)
            Note how glTexImage2D calls using a temporary variable that is no longer
            because the aliasing between *ppI and pI was lost when deinlining
            """

            def are_aliased(prev_param, param):
                return ((prev_param == ("&" + param)) or
                        (re.match(prev_param+ r"\[\d+\]", param) is not None))

            # For every actual parameter, check if a previously occurrence aliases
            # its contents, eg
            #   f(&a)
            #   h(a)
            # In that case, we need to coalesce a into &a[0]
            #   f(&a)
            #   h(&a[0])
            # XXX Note cases where deinlining code where there are aliased and non
            #    aliased occurrences is not supported and will throw an exception
            for actual_parameters in all_actual_parameters:
                for actual_parameter_index, actual_parameter in enumerate(actual_parameters):
                    for prev_actual_parameter_index, prev_actual_parameter in enumerate(actual_parameters[:actual_parameter_index]):
                        # If this parameter was aliased in a previous instruction
                        if (are_aliased(prev_actual_parameter, actual_parameter)):
                            assert None is logger.debug("%s aliases to %s, " % (prev_actual_parameter, actual_parameter))

                            # Coalesce the aliased parameter into the pointer
                            for aliased_actual_parameters in all_actual_parameters:
                                this_prev_actual_parameter = aliased_actual_parameters[prev_actual_parameter_index]
                                this_actual_parameter = aliased_actual_parameters[actual_parameter_index]
                                # We don't support a mix of aliased and non-aliased
                                # occurrences, error out if so
                                if (not are_aliased(this_prev_actual_parameter, this_actual_parameter)):
                                    raise Exception("Unsupported mix of aliased and non-aliased occurrences, %s and %s vs. %s and %s" % (
                                        prev_actual_parameter, actual_parameter,
                                        this_prev_actual_parameter, this_actual_parameter
                                    ))

                                # Remove from the actual parameters, the callee
                                # is changed below to use indirection on the
                                # alias instead
                                del aliased_actual_parameters[actual_parameter_index]

                            formal_param_type, formal_param_name = best_substring_formal_parameters[actual_parameter_index].rsplit(" ", 1)
                            prev_formal_param_type, prev_formal_param_name = best_substring_formal_parameters[prev_actual_parameter_index].rsplit(" ", 1)

                            # Change all the occurrences in the new function body
                            # to dereference the pointer
                            for best_actual_parameters in best_substring_actual_parameters:
                                for best_actual_parameter_index, best_actual_parameter in enumerate(best_actual_parameters):
                                    if (best_actual_parameter == formal_param_name):
                                        best_actual_parameters[best_actual_parameter_index] = prev_formal_param_name + "[0]"

                            # Remove the formal parameter from the new function
                            del best_substring_formal_parameters[actual_parameter_index]

        #
        # Remove each occurrence of the best substring from the function strings
        # by replacing it with a new function
        #
        char_to_function_len = len(char_to_function)
        best_substring_frame_index = len(frame_strings)
        best_substring_function_name = "subframe%d" % best_substring_frame_index
        best_substring_function_char = unichr(char_to_function_len)

        # List of references to items in frame_actual_parameters
        all_actual_parameters = []
        # List of flattened actual parameters that are common across call-sites
        # with None for entries that are not common
        actual_parameter_indices = []
        best_substring_actual_parameters = []

        replace_caller_occurrences_and_gather_actual_parameters(frame_strings,
                                                                frame_actual_parameters,
                                                                substring,
                                                                all_actual_parameters,
                                                                best_substring_actual_parameters,
                                                                best_substring_function_char)

        # Note all_actual_parameters is a list of references to items in
        # frame_actual_parameters, so modifying the first updates the second too
        optimize_caller_actual_parameters(all_actual_parameters, actual_parameter_indices)

        best_substring_formal_parameters = []
        gather_callee_actual_and_formal_parameters(actual_parameter_indices,
                                                   best_substring_actual_parameters,
                                                   best_substring_formal_parameters)

        assert None is logger.debug("Formal and actual parameters for new function %s are: %s %s" %
                                    (best_substring_function_name,
                                     str(best_substring_formal_parameters),
                                     str(best_substring_actual_parameters)))

        # Finally coalesce all aliased parameters to prevent the aliasing bug
        coalesce_aliased_occurrences(all_actual_parameters, best_substring_actual_parameters,
                                     best_substring_formal_parameters)

        assert None is logger.debug("Dealiased formal and actual parameters for new function %s are: %s %s" %
                                    (best_substring_function_name,
                                     str(best_substring_formal_parameters),
                                     str(best_substring_actual_parameters)))

        # Add the new function and its prototype to the global lists
        frame_strings.append(substring)
        frame_actual_parameters.append(best_substring_actual_parameters)
        frame_prototypes.append("void subframe%d(%s)" % (len(frame_prototypes),
                                                         string.join(best_substring_formal_parameters, ", ")))
        char_to_function[best_substring_function_char] = best_substring_function_name
        function_to_char[best_substring_function_name] = best_substring_function_char

        assert(len(frame_actual_parameters) == len(frame_strings))
        assert(len(frame_prototypes) == len(frame_strings))

    logger.info("Starting")

    frames = []
    frame_prototypes = []
    frame_local_decls = []
    global_decls = []

    # Read the code, extract functions, function prototypes and global declarations
    parse_c_file(trace_filepath, frames, frame_prototypes, frame_local_decls, global_decls)

    # XXX Simplify the code into a three-address code, turn inline operations into
    #     local variables

    # XXX Could sort the functions for higher matching likelihood, but needs
    #     sequence point information.

    # The realization is that, as long as the function sequence is the same, we
    # can always use enough formal parameters to be able to call it from any
    # different call-sites

    # Hash to convert from function name to function unichar
    function_to_char = {}
    # Hash to convert from function unichr to function name
    char_to_function = {}
    # List of strings with one unichar per function call, one string per item,
    # indexed by frame index
    frame_strings = []
    # List of lists of function parameters, one list per item, indexed by frame index
    frame_actual_parameters = []

    # Convert frames into strings by assigning one char to each function
    for frame in frames:
        this_frame_string = []
        this_frame_actual_parameters = []
        for line in frame:
            function_name = line[0]
            try:
                function_char = function_to_char[function_name]
            except:
                function_char = unichr(len(function_to_char))
                function_to_char[function_name] = function_char
                char_to_function[function_char] = function_name
            this_frame_string.append(function_char)
            this_frame_actual_parameters.append(line[1:])

        this_frame_string = string.join(this_frame_string, "")
        frame_strings.append(this_frame_string)
        frame_actual_parameters.append(this_frame_actual_parameters)

    initial_code_lines = sum([len(s) for s in frame_strings])
    logger.info("Initial code lines: %d" % initial_code_lines)

    # Sliding window parameters
    # kipo-all 117405
    # size=2, start=0, start_increment=5, size_increment=10 9463 1m4s
    # size=2, start=0, start_increment=1, size_increment=0 8457 12s
    # size=3, start=0, start_increment=1, size_increment=0 7329 12s
    # size=4, start=0, start_increment=1, size_increment=0 6910 13s
    # gtavc 1252989
    # size=2, start=0, start_increment=1, size_increment=0 57955 3.95m
    # size=4, start=0, start_increment=1, size_increment=0 45542 4.46m
    window_size = 2
    window_start = 0
    window_start_increment = 1
    window_size_increment = 0

    # XXX Should this 1000 iterations be a parameter?
    for k in xrange(1000):

        # Find the number of occurrences of each possible substring

        # Each entry in the histogram is
        # 'substring' : count
        # XXX We don't need to rebuild the histogram from scratch on every
        #     iteration, we should be able to go to the functions that contained
        #     the best substring and do a partial update of those
        #     But note that that requires going through the old code and removing all
        #     substrings and setting to zero the histogram for the best substring
        substring_histogram =  {}
        window_end = int(window_start) + int(window_size)
        logger.info("Building histogram for window [%d:%d]" % (window_start, window_end))
        build_histogram(substring_histogram,
                        frame_strings[int(window_start):window_end])

        # XXX Should this be incremented only on unsuccessful compression?
        window_start += window_start_increment
        window_size += window_size_increment

        # Go through the substring histogram and take the ones with the highest
        # compression ratio
        logger.debug("Searching for best substring")
        max_compression = 0
        best_substring_and_count = None

        for substring_and_count in substring_histogram.iteritems():
            ##if (substring_and_count[1] > 1):
            ##    print "----------------- %d -------------" % substring_and_count[1]
            ##    for c in substring_and_count[0]:
            ##        print "    %s" % char_to_function[c]
            # The compression achieved is
            #   + number of lines factored out * number of invocations
            #   - number of lines factored out (for the function code)
            #   - number of invocations (for the function calls)
            this_compression = len(substring_and_count[0]) * (substring_and_count[1] - 1) - substring_and_count[1]
            if (max_compression < this_compression):
                best_substring_and_count = substring_and_count
                max_compression = this_compression

        # Don't bother with small compressions
        min_compression = 0
        if (max_compression <= min_compression):
            if (window_end > len(frame_strings)):
                # No worthy compression found, done
                logger.info("Exhausted all the worthy compressions")
                break
            else:
                logger.debug("No compression found, sliding window only")
                continue

        # Convert the best substring into a new function and update
        # the necessary tables
        logger.debug("Converting best substring into a new function")
        replace_code(frame_strings, frame_prototypes, best_substring_and_count[0])

    # Print the new code
    lines = dump_code(frame_strings, frame_prototypes, frame_actual_parameters, frame_local_decls, global_decls)

    final_code_lines = sum([len(s) for s in frame_strings])
    logger.info("Initial code lines %d final %d compression ratio %3.3f" % (
        initial_code_lines, final_code_lines, float(initial_code_lines) / final_code_lines))

    return lines

if (__name__ == "__main__"): # pragma: no cover
    logging_format = "%(asctime).23s %(levelname)s:%(filename)s(%(lineno)d) [%(thread)d]: %(message)s"

    logger_handler = logging.StreamHandler()
    logger_handler.setFormatter(logging.Formatter(logging_format))
    logger.addHandler(logger_handler)

    LOG_LEVEL = logging.DEBUG
    logger.setLevel(LOG_LEVEL)

    trace_filepath = sys.argv[1]

    lines = deinline(trace_filepath)

    for line in lines:
        print line