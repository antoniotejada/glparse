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

// From Desktop GL (SonicDash sends those (!))
#define GL_MAX_SAMPLES                    0x8D57
#define GL_ALPHA_TEST                     0x0BC0
#define GL_POINT_BIT                      0x00000002
#define GL_REPLACE_OLDEST_SUN             0x0003
#define GL_FRAGMENT_SHADER_DERIVATIVE_HINT 0x8B8B
#define GL_SAMPLE_BUFFERS_SGIS            0x80A

// From Dekstop GL (Need for Speed sends those (?))
#define GL_SAMPLE_ALPHA_TO_MASK_SGIS     0x809E
#define GL_SAMPLE_MASK_SGIS 0x80A0
#define GL_BLEND_COLOR_EXT 0x8005
#define GL_GENERATE_MIPMAP_HINT_SGIS 0x8192
#define GL_SAMPLE_MASK_VALUE_SGIS 0x80AA
#define GL_SAMPLE_MASK_INVERT_SGIS 0x80AB


#ifndef GL_RGBA8
#define GL_RGBA8 0x8058
#endif

extern int engine_log_egl_context(const EGLDisplay display, const EGLContext context, int logLevel);


// XXX There is a general problem with extensions: they appear in the GL ES
//     trace but the code generator needs to retrieve the pointers and call
//     them since they are not part of the .so files

GL_APICALL void GL_APIENTRY glStartTilingQCOM (GLuint x, GLuint y, GLuint width, GLuint height, GLbitfield preserveMask)
{
}

GL_APICALL void GL_APIENTRY glEndTilingQCOM (GLbitfield preserveMask)
{

}

GL_APICALL void glBindVertexArrayOES(GLuint array)
{

}

// XXX This is actually of ES 3.0, so it could work using a 3.0 SDK
GL_APICALL void glInvalidateFramebuffer(GLenum target, GLsizei numAttachments,
 	const GLenum *attachments)
{
}

GL_APICALL void GL_APIENTRY glDiscardFramebufferEXT(GLenum target, GLsizei numAttachments,
    const GLenum *attachments)
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

int openAndGetAssetBuffer(DrawState* pDrawState, const char* filename, AAsset** ppAsset, const void** ppBuffer)
{
    AAssetManager* pAssetManager = pDrawState->pAssetManager;
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

// XXX Implement this
void *glMapBufferRange(GLenum target, GLintptr offset, GLsizeiptr length, GLbitfield access)
{

}

/**
 * glVertexAttribPointerData is a fake call that Android inserts before glDrawXXXXX 
 * to supply the glVertexAttribPointer data, see
 * http://stackoverflow.com/questions/14382208/what-is-glvertexattribpointerdata
 * http://androidxref.com/4.4_r1/xref/frameworks/native/opengl/libs/GLES_trace/src/gltrace_fixup.cpp#473
 */
void glVertexAttribPointerData(GLuint index,  GLint size,  GLenum type,  
                               GLboolean normalized, GLsizei stride,  
                               const GLvoid * pointer, int minIndex, int maxIndex)
{
    // For indexed geometry calls (eg glDrawElements) the buffer captured in 
    // the trace only contains vertices present in the index buffer, we need
    // to rebase the pointer so unrebased indices are still valid
    // (another option would be to rebase the indices, but that is not possible
    // if the index buffer is a buffer object - although probably minIndex is 
    // zero in that case as the trace capture cannot get to the indices either - 
    // or if any part of the shader pipeline acts differently depending on the 
    // index value)

    int rebaseInBytes = 0;
    // Don't bother calculating the rebase if the buffer doesn't need to be rebased
    if (minIndex != 0)
    {
        // Trace capture tightly packs the attributes in the buffer, the passed-in 
        // stride is the original one, thus unreliable, calculate it
        
        // GL_FIXED and GL_FLOAT are size 4, the trace code generator should 
        // catch invalid types at code generation time
        int elementSize = (((type == GL_BYTE) || (type == GL_UNSIGNED_BYTE)) ? 1 : 
                           (((type == GL_SHORT)|| (type == GL_UNSIGNED_SHORT)) ? 2 : 4));
        rebaseInBytes = minIndex * elementSize * size;
    }
 
    // The trace stores a non-zero stride, but the attributes are actually
    // tightly packed by the trace capture, ignore the stride and send zero instead.   
    glVertexAttribPointer(index, size, type, normalized, 0, 
                          (((char*) pointer) - rebaseInBytes));
}

EGLContext eglOverriddenCreateContext(DrawState* pDrawState);
void eglOverriddenMakeCurrent(DrawState* pDrawState, EGLContext ctx);

void glScaledViewport(GLint x, GLint y, GLsizei width, GLsizei height);
void glScaledScissor(GLint x, GLint y, GLsizei width, GLsizei height);
void glOverriddenDisable(DrawState* pDrawState, GLenum cap);
void glOverriddenEnable(DrawState* pDrawState, GLenum cap);

// Deinliner removes casts, avoid warnings about passing typed pointer to pointer
// instead of void pointer to pointer  by casting explicitly
// XXX This should be fixed by having a smarter parser in the deinliner that
// preserves the casts generated by glparser
#define openAndGetAssetBuffer(pDrawState, filename, ppAsset, ppBuffer) \
        openAndGetAssetBuffer(pDrawState, filename, ppAsset, (const void**) ppBuffer)

#include "trace2.inc"

#undef openAndGetAssetBuffer

void eglOverriddenMakeCurrent(DrawState* pDrawState, EGLContext context)
{
    eglMakeCurrent(pDrawState->display, pDrawState->surface, pDrawState->surface, context);
    LOGI("Context %p made current on surface %p, error 0x%x", context, pDrawState->surface, eglGetError());

    // In general, try not to pollute GL execution with unnecessary GL calls,
    // so this can be captured and replayed multiple times without piling up
    // internal GL calls
    // XXX Enable this on a configuration option
    if (false)
    {
        // Dump GL information
        LOGI("GL information");
        LOGI("\tRenderer: %s", glGetString(GL_RENDERER));
        LOGI("\tVendor: %s", glGetString(GL_VENDOR));
        LOGI("\tVersion: %s", glGetString(GL_VERSION));
        LOGI("\tShading Language: %s", glGetString(GL_SHADING_LANGUAGE_VERSION));
        LOGI("\tExtensions: %s", glGetString(GL_EXTENSIONS));

        // Initialize GL state.
        if (pDrawState->gl_enable_dither)
        {
            glEnable(GL_DITHER);
        }
        else if (pDrawState->gl_disable_dither)
        {
            glDisable(GL_DITHER);
        }

        // glEnable(GL_CULL_FACE);
        // glDisable(GL_DEPTH_TEST);
    }
}
/**
 * Create a context compatible with the current context and sharing resources
 * with it
 * WAR: Android OpenGL ES traces for eglCreateContext only contain the version
 *      and the EGL_CONTEXT_ID resulting from the creation at trace recording time,
 *      so there's little more that can be done (eg non sharing, using a different
 *      config, etc).
 */
EGLContext eglOverriddenCreateContext(DrawState* pDrawState)
{
    EGLint context_attrib_list[] = {
        EGL_CONTEXT_CLIENT_VERSION, 2,
        EGL_NONE
    };

    EGLDisplay display = pDrawState->display;
    EGLConfig config = pDrawState->config;
    EGLContext sharee = (pDrawState->contexts != NULL) ?  pDrawState->contexts[0] : EGL_NO_CONTEXT;

    EGLContext context = eglCreateContext(display, config, sharee, context_attrib_list);
    if (context == EGL_NO_CONTEXT)
    {
        LOGE("Unable to create the context, error 0x%x", eglGetError());
        exit(EXIT_FAILURE);
    }

    // Dump EGL context information
    LOGI("Created context %p, error 0x%x", context, eglGetError());
    engine_log_egl_context(display, context, ANDROID_LOG_INFO);

    pDrawState->contexts = realloc(pDrawState->contexts,
                                   sizeof(EGLContext) * (pDrawState->num_contexts + 1));
    pDrawState->contexts[pDrawState->num_contexts] = context;
    pDrawState->num_contexts++;

    return context;
}

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

void glOverriddenEnable(DrawState* pDrawState, GLenum cap)
{
    switch (cap)
    {
        case GL_DITHER:
            if (!pDrawState->gl_disable_dither)
            {
                glEnable(cap);
            }
        break;
        default:
            LOGE("Unhandled overridden enable 0x%d", cap);
        break;
    }
}

void glOverriddenDisable(DrawState* pDrawState, GLenum cap)
{
    switch (cap)
    {
        case GL_DITHER:
            if (!pDrawState->gl_enable_dither)
            {
                glDisable(cap);
            }
        break;
        default:
            LOGE("Unhandled overridden disable 0x%d", cap);
        break;
    }
}
