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

 /**
  * @see http://en.wikibooks.org/wiki/OpenGL_Programming/Android_GLUT_Wrapper
  * @see http://android-developers.blogspot.ie/2011/11/jni-local-reference-changes-in-ics.html
  */
#include <android/sensor.h>
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <errno.h>
#include <jni.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <time.h>
#include <zlib.h>

#include "common.h"
#include "intent.h"

// XXX These are defined in trace.c, move them to some common file
extern int trace_width;
extern int trace_height;

/**
 * Our saved state data.
 */
struct saved_state {
    float angle;
    int32_t x;
    int32_t y;
};

/**
 * Shared state for our app.
 */
 struct engine {
    struct android_app* app;
    DrawState drawState;

    ASensorManager* sensorManager;
    const ASensor* accelerometerSensor;
    ASensorEventQueue* sensorEventQueue;

    bool animating;
    int32_t width;
    int32_t height;
    struct saved_state state;

    EGLSyncKHR sync;
};

// GL configuration default parameters
bool gl_disable_dither = false;
bool gl_enable_dither = false;
// 0: Don't insert do glGetError
// 1: Insert glGetError on every swapbuffers
// XXX In the future also have gl_get_error on every gl command, etc
int gl_get_error = 1;
// Log the GL context (renderer, etc) when created
bool gl_log_context = true;

PFNEGLCREATESYNCKHRPROC eglCreateSyncKHR;
PFNEGLDESTROYSYNCKHRPROC eglDestroySyncKHR;
PFNEGLGETSYNCATTRIBKHRPROC eglGetSyncAttribKHR;

// EGL configuration default parameters, overrides will be loaded at startup
// -1 means EGL_DONT_CARE
// -N means N or greater
bool egl_swap_preserve_bit = false;
bool egl_window_bit = true;
bool egl_pbuffer_bit = false;
int egl_green_size = 8;
int egl_blue_size = 8;
int egl_red_size = 8;
int egl_alpha_size = 8;
int egl_depth_size = -16;
int egl_stencil_size = EGL_DONT_CARE;
// 0 width and height means use display resolution
// (egl_width and egl_height are defined in the trace, as they are initialized
// to the trace's width & height)
extern int egl_width;
extern int egl_height;
int egl_samples = 0;

// Type of sync on pbuffer swapbuffers
// 0: No sync
// 1: readpixels
// 2: EGLSync
// 3: glFinish
#define EGL_SWAPBUFFERS_SYNC_NONE 0
#define EGL_SWAPBUFFERS_SYNC_READPIXELS 1
#define EGL_SWAPBUFFERS_SYNC_EGLSYNC 2
#define EGL_SWAPBUFFERS_SYNC_GLFINISH 3
int egl_swapbuffers_sync = EGL_SWAPBUFFERS_SYNC_NONE;

// Runtime configuration parameters
int draw_limit = 0;
int frame_limit = 0;
bool stop_motion = true;
int capture_frequency = 0;
bool capture_compressed = true;

GLbyte* g_captured_pixels = NULL;
typedef struct timespec timespec_t;
timespec_t g_frame_start_time;

// Linux normally defines PATH_MAX as 4096, that's a lot to put on the stack
// use some other value instead (but always use with length-safe versions)
// This is normally used for things like 
//      /data/data/com.example.native_activity/files/XXXXX.XXX.XXX
// which is around 60 chars. 
#define PATH_MEDIUM 128

#define ARRAY_LENGTH(a) (sizeof(a) / sizeof((a)[0]))
#define MAKE_EGL_ATTRIBUTE_INFO(a) { #a, a }
#define STRNCAT_MASK(string, len, value, mask) do {                           \
            strncat(string, ((value & mask) != 0) ? " " #mask "," : "", len); \
            string[len-1] = 0;                                                \
        } while (0)
#define STRNCAT_LITERAL(string, len, value, literal) do {                                \
            strncat(string, (value == literal) ? " " #literal "," : "", len); \
            string[len-1] = 0;                                                \
        } while (0)
typedef struct
{
    const char* name;
    EGLint value;
} EGLAttributeInfo;

EGLAttributeInfo egl_string_attribute_infos[] = {
    MAKE_EGL_ATTRIBUTE_INFO(EGL_VENDOR),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_VERSION),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_CLIENT_APIS),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_EXTENSIONS),
};

EGLAttributeInfo egl_config_attribute_infos[] = {
    MAKE_EGL_ATTRIBUTE_INFO(EGL_CONFIG_ID),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_CONFORMANT),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_CONFIG_CAVEAT),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_RENDERABLE_TYPE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_SURFACE_TYPE),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_LEVEL),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_COLOR_BUFFER_TYPE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_BUFFER_SIZE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_SAMPLES),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_SAMPLE_BUFFERS),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_RED_SIZE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_GREEN_SIZE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_BLUE_SIZE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_ALPHA_SIZE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_ALPHA_MASK_SIZE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_LUMINANCE_SIZE),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_TRANSPARENT_TYPE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_TRANSPARENT_RED_VALUE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_TRANSPARENT_GREEN_VALUE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_TRANSPARENT_BLUE_VALUE),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_STENCIL_SIZE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_DEPTH_SIZE),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_BIND_TO_TEXTURE_RGB),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_BIND_TO_TEXTURE_RGBA),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_MIN_SWAP_INTERVAL),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_MAX_SWAP_INTERVAL),
    
    MAKE_EGL_ATTRIBUTE_INFO(EGL_MAX_PBUFFER_WIDTH),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_MAX_PBUFFER_HEIGHT),
};

EGLAttributeInfo egl_surface_attribute_infos[] = {
    MAKE_EGL_ATTRIBUTE_INFO(EGL_CONFIG_ID),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_WIDTH),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_HEIGHT),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_HORIZONTAL_RESOLUTION),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_VERTICAL_RESOLUTION),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_PIXEL_ASPECT_RATIO),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_RENDER_BUFFER),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_MIPMAP_TEXTURE),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_TEXTURE_FORMAT),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_TEXTURE_TARGET),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_SWAP_BEHAVIOR),
    MAKE_EGL_ATTRIBUTE_INFO(EGL_MULTISAMPLE_RESOLVE),
};

EGLAttributeInfo egl_context_attribute_infos[] = {
    MAKE_EGL_ATTRIBUTE_INFO(EGL_CONFIG_ID),

    MAKE_EGL_ATTRIBUTE_INFO(EGL_CONTEXT_CLIENT_TYPE),
    MAKE_EGL_ATTRIBUTE_INFO( EGL_CONTEXT_CLIENT_VERSION),

    MAKE_EGL_ATTRIBUTE_INFO( EGL_RENDER_BUFFER),
};

static int engine_log_egl_strings(const EGLDisplay display, int logLevel)
{
    int j;
    for (j = 0; j < ARRAY_LENGTH(egl_string_attribute_infos); ++j)
    {
        const EGLAttributeInfo* pAttribInfo = &egl_string_attribute_infos[j];
        const char* configValueString = eglQueryString(display, pAttribInfo->value);
        if (configValueString == NULL)
        {
            configValueString = "ERROR";
        }
        __android_log_print(logLevel, "native-activity", "\t\t%s: %s", pAttribInfo->name, configValueString);
    }
}

static int engine_log_egl_config(const EGLDisplay display, EGLConfig config, int logLevel)
{
    int j;
    for (j = 0; j < ARRAY_LENGTH(egl_config_attribute_infos); ++j)
    {
        const EGLAttributeInfo* pAttribInfo = &egl_config_attribute_infos[j];
        EGLint configValue = EGL_NOT_INITIALIZED;
        char configValueString[200] = "";
        const int configValueStringLen = sizeof(configValueString);
        if (eglGetConfigAttrib(display, config, pAttribInfo->value, &configValue))
        {
            switch (pAttribInfo->value)
            {
                case EGL_COLOR_BUFFER_TYPE:
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_RGB_BUFFER);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_LUMINANCE_BUFFER);
                break;
                case EGL_SURFACE_TYPE:
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_MULTISAMPLE_RESOLVE_BOX_BIT);
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_PBUFFER_BIT);
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_PIXMAP_BIT);
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_SWAP_BEHAVIOR_PRESERVED_BIT);
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_VG_ALPHA_FORMAT_PRE_BIT);
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_VG_COLORSPACE_LINEAR_BIT);
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_WINDOW_BIT);
                break;
                case EGL_CONFIG_CAVEAT:
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_NONE);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_SLOW_CONFIG);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_NON_CONFORMANT_CONFIG);
                break;
                case EGL_RENDERABLE_TYPE:
                case EGL_CONFORMANT:
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_OPENGL_BIT);
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_OPENGL_ES_BIT);
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_OPENGL_ES2_BIT);
                    STRNCAT_MASK(configValueString, configValueStringLen, configValue, EGL_OPENVG_BIT);
                break;
                case EGL_TRANSPARENT_TYPE:
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_TRANSPARENT_RGB);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_NONE);
                break;
            }
            STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_NOT_INITIALIZED);
        }
        else
        {
            strncpy(configValueString, "ERROR", configValueStringLen);
            configValueString[sizeof(configValueString) - 1] = 0;
        }
        __android_log_print(logLevel, "native-activity", "\t\t%s: %d%s", pAttribInfo->name, configValue, configValueString);
    }
}

static int engine_log_egl_surface(const EGLDisplay display, const EGLSurface surface, int logLevel)
{
    int j;
    for (j = 0; j < ARRAY_LENGTH(egl_surface_attribute_infos); ++j)
    {
        const EGLAttributeInfo* pAttribInfo = &egl_surface_attribute_infos[j];
        // Catch the call returning EGL_TRUE but not filling in a value by
        // initializing to EGL_NOT_INITIALIZED
        // (this is known to happen for EGL_TEXTURE_FORMAT and EGL_TEXTURE_TARGET 
        // on both Imagination and Qualcomm)
        EGLint configValue = EGL_NOT_INITIALIZED;
        char configValueString[200] = "";
        const int configValueStringLen = sizeof(configValueString);
        if (eglQuerySurface(display, surface, pAttribInfo->value, &configValue))
        {
            switch (pAttribInfo->value)
            {
                case EGL_MULTISAMPLE_RESOLVE:
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_MULTISAMPLE_RESOLVE_DEFAULT);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_MULTISAMPLE_RESOLVE_BOX);
                break;
                case EGL_RENDER_BUFFER:
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_BACK_BUFFER);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_SINGLE_BUFFER);
                break;
                case EGL_SWAP_BEHAVIOR:
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_BUFFER_PRESERVED);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_BUFFER_DESTROYED);
                break;
                case EGL_TEXTURE_FORMAT:
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_NO_TEXTURE);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_TEXTURE_RGB);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_TEXTURE_RGBA);
                break;
                case EGL_TEXTURE_TARGET :
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_NO_TEXTURE);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_TEXTURE_2D);
                break;
                case EGL_HORIZONTAL_RESOLUTION: 
                case EGL_VERTICAL_RESOLUTION:
                case EGL_PIXEL_ASPECT_RATIO:
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_UNKNOWN);
                break;
            }
            STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_NOT_INITIALIZED);
        }
        else
        {
            strncpy(configValueString, "ERROR", configValueStringLen);
            configValueString[sizeof(configValueString) - 1] = 0;
        }
        __android_log_print(logLevel, "native-activity", "\t\t%s: %d%s", pAttribInfo->name, configValue, configValueString);
    }
}

int engine_log_egl_context(const EGLDisplay display, const EGLContext context, int logLevel)
{
    int j;
    for (j = 0; j < ARRAY_LENGTH(egl_context_attribute_infos); ++j)
    {
        const EGLAttributeInfo* pAttribInfo = &egl_context_attribute_infos[j];
        // Catch the call returning EGL_TRUE but not filling in a value by
        // initializing to EGL_NOT_INITIALIZED
        EGLint configValue = EGL_NOT_INITIALIZED;
        char configValueString[200] = "";
        const int configValueStringLen = sizeof(configValueString);
        if (eglQueryContext(display, context, pAttribInfo->value, &configValue))
        {
            switch (pAttribInfo->value)
            {
                case EGL_CONTEXT_CLIENT_TYPE:
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_OPENGL_API);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_OPENGL_ES_API);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_OPENVG_API);
                break;
                case EGL_RENDER_BUFFER:
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_BACK_BUFFER);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_SINGLE_BUFFER);
                    STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_NONE);
                break;
            }
            STRNCAT_LITERAL(configValueString, configValueStringLen, configValue, EGL_NOT_INITIALIZED);
        }
        else
        {
            strncpy(configValueString, "ERROR", configValueStringLen);
            configValueString[sizeof(configValueString) - 1] = 0;
        }
        __android_log_print(logLevel, "native-activity", "\t\t%s: %d%s", pAttribInfo->name, configValue, configValueString);
    }
}

/**
 * Find a configuration that exactly matches the inputs, EGL_FALSE otherwise
 *
 * This is necessary as opposed to eglChooseConfig because, eg Imagination returns 
 * configs without pbuffer bit even if pbuffer is requested (!).
 * The spec also says to return bigger framebuffers first even if 565 was requested.
 */
static EGLBoolean eglFindConfig(EGLDisplay display, const EGLint* attribs, EGLConfig* config)
{
    EGLConfig* configs = NULL;
    EGLBoolean ret = EGL_FALSE;
    EGLint numConfigs;

    // Fetch all the configurations
    if (!eglGetConfigs(display, NULL, 0, &numConfigs))
    {
        LOGE("eglGetConfigs failed");

        goto done;
    }
    if (numConfigs == 0)
    {
        LOGE("eglGetConfigs returned 0 configs, error 0x%x", eglGetError());

        goto done;
    }
    configs = calloc(numConfigs, sizeof(EGLConfig));
    eglGetConfigs(display, configs, numConfigs, &numConfigs);

    // Iterate through each configuration, checking each attribute
    int i;
    bool match = false;
    for (i = 0; (!match && (i < numConfigs)); ++i)
    {
        LOGD("Examining config %p", configs[i]);
        int j;
        match = true;
        // Check each attribute
        for (j = 0; (match && (attribs[j*2] != EGL_NONE)); ++j)
        {
            EGLint attrib = attribs[j*2];
            EGLint requestedValue = attribs[j*2+1];
            EGLint configValue = EGL_NOT_INITIALIZED;

            eglGetConfigAttrib(display, configs[i], attrib, &configValue);

            LOGD("Comparing requested attrib %d value %d to %d\n", attrib, requestedValue, configValue);

            switch (attrib)
            {
                // Masks
                case EGL_CONFORMANT:
                case EGL_RENDERABLE_TYPE:
                case EGL_SURFACE_TYPE:
                    // Check that the requested bits are a subset of the config bits
                    match = (match && ((requestedValue == EGL_DONT_CARE) ||
                                      ((~configValue & requestedValue) == 0)));
                break;
                // Non-masks
                default:
                    // Note that -N means a request for greater than or equal to N
                    match = (match && ((requestedValue == EGL_DONT_CARE) || 
                                       ((requestedValue < -1) && (-requestedValue <= configValue)) ||
                                       (configValue == requestedValue)));
                break;
            }
        }
    }
    if (match)
    {
        *config = configs[i-1];
        ret = EGL_TRUE;
    }

done:
    free(configs);
     
    return ret;
}

/**
 * Initialize an EGL context for the current display.
 */
static int engine_init_display(struct engine* engine) 
{
    int ret = -1;
    EGLint attribs[] = {
            EGL_SURFACE_TYPE, (egl_window_bit) ? EGL_WINDOW_BIT : 0 | 
                              (egl_pbuffer_bit) ? EGL_PBUFFER_BIT : 0 | 
                              (egl_swap_preserve_bit) ? EGL_SWAP_BEHAVIOR_PRESERVED_BIT : 0,
            EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
            EGL_BLUE_SIZE, egl_blue_size,
            EGL_GREEN_SIZE, egl_green_size,
            EGL_RED_SIZE, egl_red_size,
            EGL_ALPHA_SIZE, egl_alpha_size,
            EGL_DEPTH_SIZE, egl_depth_size,
            EGL_STENCIL_SIZE, egl_stencil_size,
            EGL_SAMPLES, egl_samples,
            EGL_NONE
    };
    EGLint format;
    EGLint numConfigs;
    EGLConfig config;
    EGLSurface surface;

    EGLDisplay display = eglGetDisplay(EGL_DEFAULT_DISPLAY);

    eglInitialize(display, 0, 0);

    eglCreateSyncKHR = (PFNEGLCREATESYNCKHRPROC) eglGetProcAddress("eglCreateSyncKHR");
    if (eglCreateSyncKHR == NULL)
    {
        LOGE("Unable to eglCreateSyncKHR, error 0x%x", eglGetError());
        exit(EXIT_FAILURE);
    }
    eglDestroySyncKHR = (PFNEGLDESTROYSYNCKHRPROC) eglGetProcAddress("eglDestroySyncKHR");
    if (eglDestroySyncKHR== NULL)
    {
        LOGE("Unable to eglCreateSyncKHR, error 0x%x", eglGetError());
        exit(EXIT_FAILURE);
    }
    eglGetSyncAttribKHR = (PFNEGLGETSYNCATTRIBKHRPROC) eglGetProcAddress("eglGetSyncAttribKHR");
    if (eglGetSyncAttribKHR == NULL)
    {
        LOGE("Unable to eglCreateSyncKHR, error 0x%x", eglGetError());
        exit(EXIT_FAILURE);
    }

    // Dump EGL information
    LOGI("EGL information on display %p", display);
    engine_log_egl_strings(display, ANDROID_LOG_INFO);

    // Dump EGL configurations
    EGLConfig* configs = NULL;
    if (!eglGetConfigs(display, NULL, 0, &numConfigs))
    {
        LOGE("eglGetConfigs failed");
        goto done;
    }
    if (numConfigs == 0)
    {
        LOGE("eglGetConfigs returned 0 configs, error 0x%x", eglGetError());
        goto done;
    }
    configs = calloc(numConfigs, sizeof(EGLConfig));
    eglGetConfigs(display, configs, numConfigs, &numConfigs);
    int i;
    LOGD("EGL configurations %d", numConfigs);
    for (i = 0; i < numConfigs; ++i)
    {
        LOGD("\tConfig %p index %d", configs[i], i);
        engine_log_egl_config(display, configs[i], ANDROID_LOG_VERBOSE);
    }

    if (!eglFindConfig(display, attribs, &config))
    {
        LOGW("Couldn't find an exact config match, trying eglChooseConfig\n");

        // Convert all attribs smaller than -1 to positive, as eglChooseConfig
        // doesn't have the convention "-N means greater than or equal to N"
        GLint* pAttrib;
        for (pAttrib = attribs; *pAttrib != EGL_NONE; pAttrib += 2)
        {
            // -1 is EGL_DONT_CARE, don't convert those
            if (pAttrib[1] < -1)
            {
                pAttrib[1] = abs(pAttrib[1]);
            }
        }
        eglChooseConfig(display, attribs, configs, numConfigs, &numConfigs);
        if (numConfigs == 0)
        {   
            LOGE("Unable to find a matching EGL configuration, error 0x%x", eglGetError());
            goto done;
        }
        config = configs[0];
    }

    LOGI("Using config %p of %d configs", config, numConfigs);
    engine_log_egl_config(display, config, ANDROID_LOG_INFO);
    
    if (egl_pbuffer_bit)
    {
        LOGI("Creating pbuffer surface as pbuffer_bit is set");
        EGLint pbuffer_attrib_list[] = {
            EGL_WIDTH, egl_width,
            EGL_HEIGHT, egl_height,
            EGL_NONE,
        };
        surface = eglCreatePbufferSurface(display, config, pbuffer_attrib_list);
    }
    else
    {
        LOGI("Creating window surface as pbuffer_bit is not set");

        /* EGL_NATIVE_VISUAL_ID is an attribute of the EGLConfig that is
         * guaranteed to be accepted by ANativeWindow_setBuffersGeometry().
         * As soon as we picked a EGLConfig, we can safely reconfigure the
         * ANativeWindow buffers to match, using EGL_NATIVE_VISUAL_ID. */
        eglGetConfigAttrib(display, config, EGL_NATIVE_VISUAL_ID, &format);

        // By passing non-zero width and height, it will trigger using the hw scaler, 
        // see http://android-developers.blogspot.com/2013_09_01_archive.html
        ANativeWindow_setBuffersGeometry(engine->app->window, egl_width, egl_height, format);
        surface = eglCreateWindowSurface(display, config, engine->app->window, NULL);
    }

    if (surface == EGL_NO_SURFACE)
    {
        LOGE("Unable to create the surface, error 0x%x", eglGetError());
        goto done;
    }

    // Preserving the backbuffer for Android view apps is necessary since Android 3.0, 
    // on architectures supporting it (Imagination doesn't, Qualcomm and NVIDIA do)
    // @see http://android.googlesource.com/platform/frameworks/base.git/+/244ada1d35419b7be9de0fc833bb03955b725ffa%5E!/
    // @see http://stackoverflow.com/questions/5359361/android-opengl-blending-similar-to-iphone
    if (egl_swap_preserve_bit)
    {
        eglSurfaceAttrib(display, surface, EGL_SWAP_BEHAVIOR, EGL_BUFFER_PRESERVED);
    }

    // Dump EGL surface information
    LOGI("EGL Surface %p information", surface);
    engine_log_egl_surface(display, surface, ANDROID_LOG_INFO);

    // Get the width & height in case the requested values were zero 
    // Do this only if they are zero, as Imagination is known to return always 
    // the display size instead of the surface size
    // XXX This could be obtained from the GL viewport state, as it's supposed
    //     default to the surface size
    if ((egl_width == 0) || (egl_height == 0))
    {
        eglQuerySurface(display, surface, EGL_WIDTH, &egl_width);
        eglQuerySurface(display, surface, EGL_HEIGHT, &egl_height);
        LOGI("Zero egl_width or egl_height provided, getting from EGLsurface %dx%d",
            egl_width, egl_height);
    }

    // Now that the EGL config is chosen, update all the program config parameters 
    // to match
    // XXX Missing updating egl_pbuffer_bit and egl_window_bit? (we currently 
    //     don't use them afterwards, but if we do, we will need to make the 
    // difference between requested and provided
    GLint egl_surface_type = 0;
    eglGetConfigAttrib(display, config, EGL_SURFACE_TYPE, &egl_surface_type);
    egl_swap_preserve_bit = egl_surface_type & EGL_SWAP_BEHAVIOR_PRESERVED_BIT;
    eglGetConfigAttrib(display, config, EGL_RED_SIZE, &egl_red_size);
    eglGetConfigAttrib(display, config, EGL_BLUE_SIZE, &egl_blue_size);
    eglGetConfigAttrib(display, config, EGL_GREEN_SIZE, &egl_green_size);
    eglGetConfigAttrib(display, config, EGL_GREEN_SIZE, &egl_green_size);
    eglGetConfigAttrib(display, config, EGL_RED_SIZE, &egl_red_size);
    eglGetConfigAttrib(display, config, EGL_ALPHA_SIZE, &egl_alpha_size);
    eglGetConfigAttrib(display, config, EGL_DEPTH_SIZE, &egl_depth_size);
    eglGetConfigAttrib(display, config, EGL_STENCIL_SIZE, &egl_stencil_size);
    eglGetConfigAttrib(display, config, EGL_SAMPLES, &egl_samples);

    // Allocate memory for capturing pixels
    if (capture_frequency > 0)
    {
        free(g_captured_pixels);
        g_captured_pixels = malloc(egl_width * egl_height * ((egl_alpha_size == 8) ? 4 : ((egl_red_size == 8) ? 3 : 2)));
    }

    engine->width = egl_width;
    engine->height = egl_height;
    engine->state.angle = 0;

    engine->drawState.display = display;
    engine->drawState.config = config;
    engine->drawState.surface = surface;
    engine->drawState.num_contexts = 0;
    engine->drawState.contexts = NULL;
    // XXX What's the lifecycle of this, does it need to be recopied?
    engine->drawState.pAssetManager = engine->app->activity->assetManager;

    engine->drawState.gl_enable_dither = gl_enable_dither;
    engine->drawState.gl_disable_dither = gl_disable_dither;
    engine->drawState.gl_log_context = gl_log_context;

    ret = 0;

done:

    free(configs);

    return ret;
}

timespec_t timespec_delta(timespec_t start, timespec_t end)
{
    timespec_t temp;
    if ((end.tv_nsec - start.tv_nsec) < 0) 
    {
        temp.tv_sec = end.tv_sec - start.tv_sec - 1;
        temp.tv_nsec = 1000000000 + end.tv_nsec - start.tv_nsec;
    } 
    else 
    {
        temp.tv_sec = end.tv_sec - start.tv_sec;
        temp.tv_nsec = end.tv_nsec - start.tv_nsec;
    }
    return temp;
}

void draw(DrawState* pDrawState);

/**
 * Capture the current frame
 */
static int capture_frame(const char* filedir, unsigned int frame_index)
{
    int ret = -1;

    if (g_captured_pixels == NULL)
    {
        LOGE("Unable to capture, temp buffer is NULL");
        goto done;
    }
    
    // Capture the pixels
    // XXX Set & restore the right framebuffer object
    GLint oldPackAlignment;
    glGetIntegerv(GL_PACK_ALIGNMENT, &oldPackAlignment);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    GLenum format = (egl_alpha_size == 0) ? GL_RGB : GL_RGBA;
    GLenum type = (egl_red_size == 8) ? GL_UNSIGNED_BYTE : ((egl_alpha_size == 1) ? GL_UNSIGNED_SHORT_5_5_5_1 : GL_UNSIGNED_SHORT_5_6_5);
    GLsizei bpp = (egl_alpha_size == 8) ? 4 : ((egl_red_size == 8) ? 3 : 2);
    LOGD("Reading pixels format 0x%x type 0x%x bpp %d", format, type, bpp);
    glReadPixels(0, 0, egl_width, egl_height, format, type, g_captured_pixels);
    glPixelStorei(GL_PACK_ALIGNMENT, oldPackAlignment);
    LOGI("glReadPixels GL error is 0x%x", glGetError());

    // Save to disk
    char filename[PATH_MEDIUM] = "";
    snprintf(filename, ARRAY_LENGTH(filename), "%s/frame_%d_%d@%d_%d.raw%s",
             filedir, egl_width, egl_height, bpp, frame_index, capture_compressed ? ".gz" : "");
    filename[ARRAY_LENGTH(filename)-1] = 0;
    if (capture_compressed)
    {
        gzFile f;
        LOGD("Saving compressed pixels to %s", filename);
        f = gzopen(filename, "wb9");
        if (f != NULL)
        {
            gzwrite(f, g_captured_pixels, egl_width * egl_height * bpp);
            gzclose(f);
            ret = 0;
        }
    }
    else
    {
        FILE* f;
        LOGD("Saving pixels to %s", filename);
        f = fopen(filename, "wb");
        if (f != NULL)
        {
            fwrite(g_captured_pixels, 1, egl_width * egl_height * bpp, f);
            fclose(f);
            ret = 0;
        }
    }

    // We need to chmod the file so it's accessible by adb pull
    if (ret == 0)
    {
        chmod(filename, S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH);
    }
    else
    {
        LOGW("Unable to create file %s for writing pixels", filename);
    }

done:

    return ret;
}

/**
 * Just the current frame in the display.
 */
static void engine_draw_frame(struct engine* engine) {
    if (engine->drawState.display == EGL_NO_DISPLAY)
    {
        // No display.
        LOGW("No display!");
        return;
    }

    if (!stop_motion || (frame_limit % 3 == 0))
    {
        int input_adjusted_frame_limit = frame_limit;
        if (stop_motion)
        {
            // A tap is a few events, down + up
            input_adjusted_frame_limit = frame_limit / 3;
        }
        
        clock_gettime(CLOCK_MONOTONIC, &g_frame_start_time);

        engine->drawState.draw_limit = INT_MAX;
        engine->drawState.frame_limit = input_adjusted_frame_limit;

        draw(&engine->drawState);
        if (gl_get_error > 0)
        {
            LOGI("Frame %d GL error is 0x%x", input_adjusted_frame_limit, glGetError());
        }

        timespec_t frame_end_time;
        clock_gettime(CLOCK_MONOTONIC, &frame_end_time);
        timespec_t frame_delta = timespec_delta(g_frame_start_time, frame_end_time);
        LOGI("Frame %d time is %3.3fms", input_adjusted_frame_limit, 
                                         ((frame_delta.tv_sec * 1000.0 + frame_delta.tv_nsec / 1000000.0)));

        // Before swapping, capture the frame if necessary
        bool capture_this_frame = ((capture_frequency > 0) && 
                                   ((input_adjusted_frame_limit % capture_frequency) == 0));
        if (capture_this_frame)
        {
            capture_frame(engine->app->activity->internalDataPath, input_adjusted_frame_limit);
        }

        // Prevent optimizations that don't render anything when offscreen
        // (Tegra4, Mali 450)
        if (egl_pbuffer_bit)
        {
            LOGI("Doing egl_swapbuffers_sync %d", egl_swapbuffers_sync);
            if (egl_swapbuffers_sync == EGL_SWAPBUFFERS_SYNC_READPIXELS)
            {
                // XXX This assumes there's a context current
                GLenum format = (egl_alpha_size == 0) ? GL_RGB : GL_RGBA;
                GLenum type = (egl_red_size == 8) ? GL_UNSIGNED_BYTE : ((egl_alpha_size == 1) ? GL_UNSIGNED_SHORT_5_5_5_1 : GL_UNSIGNED_SHORT_5_6_5);
                GLsizei bpp = (egl_alpha_size == 8) ? 4 : ((egl_red_size == 8) ? 3 : 2);
                GLubyte pixel[bpp];
                GLint oldPackAlignment;
                glGetIntegerv(GL_PACK_ALIGNMENT, &oldPackAlignment);
                glPixelStorei(GL_PACK_ALIGNMENT, 1);
                LOGD("Reading pixels format 0x%x type 0x%x bpp %d", format, type, bpp);
                glReadPixels(0, 0, 1, 1, format, type, pixel);
                glPixelStorei(GL_PACK_ALIGNMENT, oldPackAlignment);
                LOGI("Read pixels, GL error is 0x%x", glGetError());
            }
            else if (egl_swapbuffers_sync == EGL_SWAPBUFFERS_SYNC_EGLSYNC)
            {
                EGLSyncKHR sync;
                if (engine->sync != EGL_NO_SYNC_KHR)
                {
                    eglDestroySyncKHR(engine->drawState.display, engine->sync);
                    engine->sync = EGL_NO_SYNC_KHR;
                }
                sync = eglCreateSyncKHR(engine->drawState.display, EGL_SYNC_FENCE_KHR, NULL);
                if (sync == EGL_NO_SYNC_KHR)
                {
                    LOGE("Unable to create EGLSyncKHR, error 0x%x", eglGetError());
                    exit(EXIT_FAILURE);
                }
                engine->sync = sync;
                EGLint status;
                if (!eglGetSyncAttribKHR(engine->drawState.display, sync, EGL_SYNC_STATUS_KHR, &status))
                {
                    LOGE("Unable to eglGetSyncAttribKHR, error 0x%x", eglGetError());
                    exit(EXIT_FAILURE);
                }
            }
            else if (egl_swapbuffers_sync == EGL_SWAPBUFFERS_SYNC_GLFINISH)
            {
                // XXX This assumes there's a context current and it's the one
                //     that did the OpenGL rendering
                glFinish();
            }
        }

        // Swap this frame
        eglSwapBuffers(engine->drawState.display, engine->drawState.surface);

        timespec_t swap_end_time;
        clock_gettime(CLOCK_MONOTONIC, &swap_end_time);
        timespec_t swap_delta = timespec_delta(g_frame_start_time, swap_end_time);
        LOGI("Swap %d time is %3.3fms", input_adjusted_frame_limit, 
                                        ((swap_delta.tv_sec * 1000.0) + swap_delta .tv_nsec / 1000000.0));
    }

    // XXX Allow looping, eg
    //          loop_start_frame = 200
    //          loop_end_frame = 400
    //          loop_count = 0 (infinite)
    //     or combine with start_frame and end_frame (discard frames - but not state-
    //     until start)
    draw_limit++;
    frame_limit++;
    engine->animating = !stop_motion;
}

/**
 * Tear down the EGL context currently associated with the display.
 */
static void engine_term_display(struct engine* engine) {
    if (engine->drawState.display != EGL_NO_DISPLAY)
    {
        eglMakeCurrent(engine->drawState.display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        // XXX Missing destroying all the created contexts, but it's not clear
        //     how to recreate them afterwards?
        if (engine->drawState.surface != EGL_NO_SURFACE)
        {
            eglDestroySurface(engine->drawState.display, engine->drawState.surface);
        }
        eglTerminate(engine->drawState.display);
    }
    engine->animating = false;
    engine->drawState.display = EGL_NO_DISPLAY;
    engine->drawState.surface = EGL_NO_SURFACE;
}

/**
 * Process the next input event.
 */
static int32_t engine_handle_input(struct android_app* app, AInputEvent* event) 
{
    struct engine* engine = (struct engine*)app->userData;
    LOGI("Handling input");
    if (AInputEvent_getType(event) == AINPUT_EVENT_TYPE_MOTION)
    {
        LOGI("Motion input");
        engine->animating = true;
        engine->state.x = AMotionEvent_getX(event, 0);
        engine->state.y = AMotionEvent_getY(event, 0);
        return 1;
    }
    return 0;
}

/**
 * Process the next main command.
 */
static void engine_handle_cmd(struct android_app* app, int32_t cmd) {
    struct engine* engine = (struct engine*)app->userData;
    switch (cmd) 
    {
        case APP_CMD_SAVE_STATE:
            // The system has asked us to save our current state.  Do so.
            engine->app->savedState = malloc(sizeof(struct saved_state));
            *((struct saved_state*)engine->app->savedState) = engine->state;
            engine->app->savedStateSize = sizeof(struct saved_state);
            break;
        case APP_CMD_INIT_WINDOW:
            // The window is being shown, get it ready.
            if (engine->app->window != NULL) 
            {
                if (engine_init_display(engine) != 0)
                {
                    LOGF("Display failed to initialize, aborting");
                    exit(EXIT_FAILURE);
                }
                engine_draw_frame(engine);
            }
            break;
        case APP_CMD_TERM_WINDOW:
            // The window is being hidden or closed, clean it up.
            engine_term_display(engine);
            break;
        case APP_CMD_GAINED_FOCUS:
            // When our app gains focus, we start monitoring the accelerometer.
            if (engine->accelerometerSensor != NULL) 
            {
                ASensorEventQueue_enableSensor(engine->sensorEventQueue,
                        engine->accelerometerSensor);
                // We'd like to get 60 events per second (in us).
                ASensorEventQueue_setEventRate(engine->sensorEventQueue,
                        engine->accelerometerSensor, (1000L/60)*1000);
            }
            break;
        case APP_CMD_LOST_FOCUS:
            // When our app loses focus, we stop monitoring the accelerometer.
            // This is to avoid consuming battery while not being used.
            if (engine->accelerometerSensor != NULL) 
            {
                ASensorEventQueue_disableSensor(engine->sensorEventQueue,
                        engine->accelerometerSensor);
            }
            // Also stop animating.
            engine->animating = false;
            engine_draw_frame(engine);
            break;
    }
}

/**
 *
 * @see http://stackoverflow.com/questions/12841240/android-pass-parameter-to-native-activity
 */
jobject activity_get_intent(JNIEnv* env, const ANativeActivity* activity)
{
    jobject me = activity->clazz;
    jclass acl = (*env)->GetObjectClass(env, me);
    jmethodID giid = (*env)->GetMethodID(env, acl, "getIntent", "()Landroid/content/Intent;");
    jobject j_intent = (*env)->CallObjectMethod(env, me, giid);

    return j_intent;
}

/**
 * Load the configuration from the command line.
 *
 * For the EGL int values, -1 is the same as EGL_DONT_CARE 
 */
void activity_load_config(JNIEnv* env, ANativeActivity* activity)
{
    LOGI("Loading activity configuration");

    // Load the configuration from the intent's extra parameters

    jobject intent = activity_get_intent(env, activity);

    egl_swap_preserve_bit = intent_get_boolean_extra(env, intent, "egl_swap_preserve_bit", egl_swap_preserve_bit);
    egl_window_bit = intent_get_boolean_extra(env, intent, "egl_window_bit", egl_window_bit);
    egl_pbuffer_bit = intent_get_boolean_extra(env, intent, "egl_pbuffer_bit", egl_pbuffer_bit);

    egl_samples = intent_get_int_extra(env, intent, "egl_samples", egl_samples);

    egl_swapbuffers_sync = intent_get_int_extra(env, intent, "egl_swapbuffers_sync", egl_swapbuffers_sync);

    egl_width = intent_get_int_extra(env, intent, "egl_width", egl_width);
    egl_height = intent_get_int_extra(env, intent, "egl_height", egl_height);

    egl_red_size      = intent_get_int_extra(env, intent, "egl_red_size", egl_red_size);
    egl_blue_size     = intent_get_int_extra(env, intent, "egl_blue_size", egl_blue_size);
    egl_green_size    = intent_get_int_extra(env, intent, "egl_green_size", egl_green_size);
    egl_alpha_size    = intent_get_int_extra(env, intent, "egl_alpha_size", egl_alpha_size);
    egl_depth_size    = intent_get_int_extra(env, intent, "egl_depth_size", egl_depth_size);
    egl_stencil_size  = intent_get_int_extra(env, intent, "egl_stencil_size", egl_stencil_size);

    gl_enable_dither  = intent_get_boolean_extra(env, intent, "gl_enable_dither", gl_enable_dither);
    gl_disable_dither = intent_get_boolean_extra(env, intent, "gl_disable_dither", gl_disable_dither);
    gl_log_context    = intent_get_boolean_extra(env, intent, "gl_log_context", gl_log_context);
    gl_get_error      = intent_get_int_extra(env, intent, "gl_get_error", gl_get_error);

    draw_limit        = intent_get_int_extra(env, intent, "draw_limit", draw_limit);
    frame_limit       = intent_get_int_extra(env, intent, "frame_limit", frame_limit);
    stop_motion       = intent_get_boolean_extra(env, intent, "stop_motion", stop_motion);
    capture_frequency = intent_get_int_extra(env, intent, "capture_frequency", capture_frequency);
    capture_compressed = intent_get_boolean_extra(env, intent, "capture_compressed", capture_compressed);

    LOGI("EGL configuration");

    LOGI("\tegl_swap_preserve_bit: %d", egl_swap_preserve_bit);
    LOGI("\tegl_window_bit: %d", egl_window_bit);
    LOGI("\tegl_pbuffer_bit: %d", egl_pbuffer_bit);
    LOGI("\tegl_width: %d", egl_width);
    LOGI("\tegl_height: %d", egl_height);

    LOGI("\tegl_red_size: %d", egl_red_size);
    LOGI("\tegl_green_size: %d", egl_green_size);
    LOGI("\tegl_blue_size: %d", egl_blue_size);
    LOGI("\tegl_alpha_size: %d", egl_alpha_size);
    LOGI("\tegl_depth_size: %d", egl_depth_size);
    LOGI("\tegl_stencil_size: %d", egl_stencil_size);

    LOGI("\tegl_swapbuffers_sync: %d", egl_swapbuffers_sync);

    LOGI("GL configuration");

    LOGI("\tgl_enable_dither: %d", gl_enable_dither);
    LOGI("\tgl_disable_dither: %d", gl_disable_dither);
    LOGI("\tgl_get_error: %d", gl_get_error);
    LOGI("\tgl_log_context: %d", gl_log_context);

    LOGI("Runtime configuration");

    LOGI("\tdraw_limit:        %d", draw_limit);
    LOGI("\tframe_limit:       %d", frame_limit);
    LOGI("\tstop_motion:       %d", stop_motion);
    LOGI("\tcapture_frequency: %d", capture_frequency);
    LOGI("\tcapture_compressed: %d", capture_compressed);
}

/**
 * This is the main entry point of a native application that is using
 * android_native_app_glue.  It runs in its own thread, with its own
 * event loop for receiving input events and doing other things.
 */
void android_main(struct android_app* state) 
{
    struct engine engine;

    LOGI("Starting android_main");
    LOGI("  Activity %p", state->activity);
    LOGI("  VM %p", state->activity->vm);
    LOGI("  JNIEnv %p", state->activity->env);

    // Make sure glue isn't stripped.
    app_dummy();    

    // Allow adb pull access to the files directory
    LOGD("Changing permissions for the internal storage at %s", state->activity->internalDataPath);
    chmod(state->activity->internalDataPath, S_IRUSR | S_IWUSR | S_IXUSR |
                                             S_IRGRP | S_IWGRP | S_IXGRP |
                                             S_IROTH | S_IWOTH | S_IXOTH);


    // Attach the current thread to the VM, as activity->env can only be used
    // from the callbacks (as per native_activity.h). Using it from here causes
    //      JNI ERROR: non-VM thread making JNI call (GetObjectClass)
    LOGI("Attaching entry point thread to JNIEnv");
    JNIEnv* env;
    ANativeActivity* activity = state->activity;
    JavaVM* vm = activity->vm; 
    (*vm)->AttachCurrentThread(vm, &env, 0);

    activity_load_config(env, activity);

    memset(&engine, 0, sizeof(engine));
    state->userData = &engine;
    state->onAppCmd = engine_handle_cmd;
    state->onInputEvent = engine_handle_input;
    engine.app = state;

    engine.sync = EGL_NO_SYNC_KHR;

    // Prepare to monitor accelerometer
    engine.sensorManager = ASensorManager_getInstance();
    engine.accelerometerSensor = ASensorManager_getDefaultSensor(engine.sensorManager,
            ASENSOR_TYPE_ACCELEROMETER);
    engine.sensorEventQueue = ASensorManager_createEventQueue(engine.sensorManager,
            state->looper, LOOPER_ID_USER, NULL, NULL);

    if (state->savedState != NULL) 
    {
        // We are starting with a previous saved state; restore from it.
        engine.state = *(struct saved_state*)state->savedState;
    }

    // loop waiting for stuff to do.
    while (1) 
    {
        // Read all pending events.
        int ident;
        int events;
        struct android_poll_source* source;

        // If not animating, we will block forever waiting for events.
        // If animating, we loop until all events are read, then continue
        // to draw the next frame of animation.
        while ((ident=ALooper_pollAll(engine.animating ? 0 : -1, NULL, &events,
                (void**)&source)) >= 0) 
        {

            // Process this event.
            if (source != NULL) 
            {
                source->process(state, source);
            }

            // If a sensor has data, process it now.
            if (ident == LOOPER_ID_USER) 
            {
                if (engine.accelerometerSensor != NULL) 
                {
                    ASensorEvent event;
                    while (ASensorEventQueue_getEvents(engine.sensorEventQueue,
                            &event, 1) > 0) 
                    {
                        /*LOGI("accelerometer: x=%f y=%f z=%f",
                                event.acceleration.x, event.acceleration.y,
                                event.acceleration.z);*/

                    }
                }
            }

            // Check if we are exiting.
            if (state->destroyRequested != 0) 
            {
                engine_term_display(&engine);
                return;
            }
        }

        if (engine.animating) 
        {
            LOGI("Animating");
            // Done with events; draw next animation frame.
            engine.state.angle += .01f;
            if (engine.state.angle > 1) 
            {
                engine.state.angle = 0;
            }

            // Drawing is throttled to the screen update rate, so there
            // is no need to do timing here.
            engine_draw_frame(&engine);
            // XXX Do frame statistics (vertices, calls, texel downloads...)
            // XXX When done all frames, do full statistics (captured, replayed)
        }
    }
}
