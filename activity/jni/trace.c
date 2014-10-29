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
#include <android/asset_manager.h>
#include <android/log.h>
#include <EGL/egl.h>
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include <memory.h>
#include <stdbool.h>
#include <stdlib.h>

#include "common.h"

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
#ifndef GL_ARB_texture_swizzle
#define GL_TEXTURE_SWIZZLE_R              0x8E42
#define GL_TEXTURE_SWIZZLE_G              0x8E43
#define GL_TEXTURE_SWIZZLE_B              0x8E44
#define GL_TEXTURE_SWIZZLE_A              0x8E45
#define GL_TEXTURE_SWIZZLE_RGBA           0x8E46
#endif


#define GL_COMPRESSED_RGBA8_ETC2_EAC      0x9278
#define GL_COMPRESSED_RGB8_ETC2           0x9274

#ifndef GL_RGBA8
#define GL_RGBA8 0x8058
#endif

// XXX Move to some common config file
extern bool gl_enable_dither;
extern bool gl_disable_dither;

GL_APICALL void GL_APIENTRY glStartTilingQCOM (GLuint x, GLuint y, GLuint width, GLuint height, GLbitfield preserveMask)
{
}

GL_APICALL void GL_APIENTRY glEndTilingQCOM (GLbitfield preserveMask)
{

}

int openAsset(AAssetManager* pAssetManager, const char* filename, AAsset** ppAsset)
{
    int ret = 0;

    *ppAsset = AAssetManager_open(pAssetManager, filename, AASSET_MODE_BUFFER);
    if (*ppAsset == NULL)
    {
        LOGW("Unable to open asset %s", filename);

        ret = -1;
    }

    return ret;
}

int getAssetBuffer(AAsset* pAsset, const void** ppBuffer)
{
    int ret = 0;

    *ppBuffer = AAsset_getBuffer(pAsset);
    if (*ppBuffer == NULL)
    {
        LOGW("Unable to get buffer for asset %p", pAsset);

        ret = -1;
    }

    return ret;
}

int openAndGetAssetBuffer(AAssetManager* pAssetManager, const char* filename, AAsset** ppAsset, const void** ppBuffer)
{
    int ret = 0;
    ret = openAsset(pAssetManager, filename, ppAsset);
    if (ret == 0)
    {
        ret = getAssetBuffer(*ppAsset, ppBuffer);
    }

    return ret;
}

void closeAsset(AAsset* pAsset)
{
    AAsset_close(pAsset);
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

// XXX Implement this
void *glMapBufferRange(GLenum target, GLintptr offset, GLsizeiptr length, GLbitfield access)
{

}

void glVertexAttribPointerData(GLuint index,  GLint size,  GLenum type,  GLboolean normalized,  GLsizei stride,  const GLvoid * pointer)
{
    // The trace stores a non-zero stride, but the attributes are actually
    // tightly packed, ignore the stride and send zero instead.
    glVertexAttribPointer(index, size, type, normalized, 0, pointer);
}

void glScaledViewport(GLint x, GLint y, GLsizei width, GLsizei height);
void glScaledScissor(GLint x, GLint y, GLsizei width, GLsizei height);
void glOverriddenDisable(GLenum cap);
void glOverriddenEnable(GLenum cap);

#include "../../_out/trace2.inc"

/**
 * Function to scale viewport calls on framebuffer 0 by the ratio between
 * the EGL size and the maximum framebuffer 0 viewport found in the trace
 */
void glScaledViewport(GLint x, GLint y, GLsizei width, GLsizei height)
{
    glViewport((x * egl_width)/max_viewport_width, 
               (y * egl_height)/max_viewport_height, 
               (width * egl_width)/max_viewport_width, 
               (height * egl_height)/max_viewport_height);
}

/**
 * Function to scale scissor calls on framebuffer 0 by the ratio between
 * the EGL size and the maximum framebuffer 0 scissor found in the trace
 */
void glScaledScissor(GLint x, GLint y, GLsizei width, GLsizei height)
{
    glScissor((x * egl_width)/max_scissor_width, 
               (y * egl_height)/max_scissor_height, 
               (width * egl_width)/max_scissor_width, 
               (height * egl_height)/max_scissor_height);
}

void glOverriddenEnable(GLenum cap)
{
    switch (cap)
    {
        case GL_DITHER:
            if (!gl_disable_dither)
            {
                glEnable(cap);
            }
        break;
        default:
            LOGE("Unhandled overridden enable 0x%d", cap);
        break;
    }
}

void glOverriddenDisable(GLenum cap)
{
    switch (cap)
    {
        case GL_DITHER:
            if (!gl_enable_dither)
            {
                glDisable(cap);
            }
        break;
        default:
            LOGE("Unhandled overridden disable 0x%d", cap);
        break;
    }
}