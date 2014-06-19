/**
 *
 * Copyright 2014 Antonio Tejada
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * https://android.googlesource.com/platform/frameworks/native/+/master/opengl/libs/GLES_trace/DESIGN.txt
 * https://android.googlesource.com/platform/frameworks/native/+/master/opengl/libs/GLES_trace/gltrace.proto
 *
 * https://cvs.khronos.org/svn/repos/ogl/trunk/doc/registry/public/api/gl.xml
 */
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>

#include <android/log.h>

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "native-activity", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "native-activity", __VA_ARGS__))

#ifndef GL_RED
// GLES2 headers don't have this one, but GLES3 do
#define GL_RED 0x1903
#endif
#ifndef GL_PIXEL_UNPACK_BUFFER
#define GL_PIXEL_UNPACK_BUFFER 0x88ef
#endif
#ifndef GL_UNPACK_ROW_LENGTH
#define GL_UNPACK_ROW_LENGTH 0xcf2
#endif
#ifndef GL_DEPTH_COMPONENT24
#define GL_DEPTH_COMPONENT24 GL_DEPTH_COMPONENT24_OES
#endif
#ifndef GL_RGB565_OES
#define GL_RGB565_OES GL_RGB565
#endif

GL_APICALL void GL_APIENTRY glStartTilingQCOM (GLuint x, GLuint y, GLuint width, GLuint height, GLbitfield preserveMask)
{
}

GL_APICALL void GL_APIENTRY glEndTilingQCOM (GLbitfield preserveMask)
{
}

void glPushGroupMarkerEXT(GLsizei length, const char *marker)
{
}

void glInsertEventMarkerEXT(GLsizei length, const char *marker)
{

}

void glPopGroupMarkerEXT()
{
}

// The trace uses the non OES names, convert them to OES which are the ones exported
// by gl2.h
#define glMapBuffer glMapBufferOES
#define glUnmapBuffer glUnmapBufferOES

GL_APICALL void GL_APIENTRY glDiscardFramebufferEXT(GLenum target, GLsizei numAttachments, const GLenum *attachments)
{
}

void glVertexAttribPointerData(GLuint index,  GLint size,  GLenum type,  GLboolean normalized,  GLsizei stride,  const GLvoid * pointer)
{
    // The trace stores a non-zero stride, but the attributes are actually
    // tightly packed, ignore the stride and send zero instead.
    glVertexAttribPointer(index, size, type, normalized, 0, pointer);
}

void draw(int draw_limit, int frame_limit)
{
    int draw_count = 0;
    int frame_count = 0;
    #include "../../_out/trace.inc"
}
