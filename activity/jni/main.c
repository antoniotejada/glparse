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
#include <android_native_app_glue.h>
#include <stdlib.h>
#include <errno.h>
#include <EGL/egl.h>
#include <GLES2/gl2.h>
#include <jni.h>
#include <stdbool.h>

#include "common.h"
#include "intent.h"

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

    ASensorManager* sensorManager;
    const ASensor* accelerometerSensor;
    ASensorEventQueue* sensorEventQueue;

    int animating;
    EGLDisplay display;
    EGLSurface surface;
    EGLContext context;
    int32_t width;
    int32_t height;
    struct saved_state state;
};

// EGL configuration default parameters, overrides will be loaded at startup
int egl_swap_preserve_bit = false;
int egl_window_bit = true;
int egl_pbuffer_bit = false;
int egl_green_size = 8;
int egl_blue_size = 8;
int egl_red_size = 8;
int egl_alpha_size = 8;
int egl_depth_size = 24;
int egl_stencil_size = 0;
int egl_width = 0;
int egl_height = 0;

// Runtime configuration parameters
int draw_limit = 0;
int frame_limit = 0;
int stop_motion = false;
// XXX add other parameters (gl_dither_enable, etc)

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

static int engine_log_egl_strings(EGLDisplay display, int logLevel)
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

static int engine_log_egl_config(EGLDisplay display, EGLConfig config, int logLevel)
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

static int engine_log_egl_surface(EGLDisplay display, EGLSurface surface, int logLevel)
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
 * Initialize an EGL context for the current display.
 */
static int engine_init_display(struct engine* engine) 
{
    // initialize OpenGL ES and EGL

    /*
     * Here specify the egl_config_attribute_infos of the desired configuration.
     * Below, we select an EGLConfig with at least 8 bits per color
     * component compatible with on-screen windows
     */
    const EGLint attribs[] = {
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
            EGL_NONE
    };
    EGLint format;
    EGLint numConfigs;
    EGLConfig config;
    EGLSurface surface;
    EGLContext context;

    EGLDisplay display = eglGetDisplay(EGL_DEFAULT_DISPLAY);

    eglInitialize(display, 0, 0);

    // Dump EGL information
    LOGI("EGL information");
    engine_log_egl_strings(display, ANDROID_LOG_INFO);

    // Dump EGL configurations
    EGLConfig* configs = NULL;
    if (!eglGetConfigs(display, NULL, 0, &numConfigs))
    {
        LOGE("eglGetConfigs failed");
        return -1;
    }
    if (numConfigs == 0)
    {
        LOGE("eglGetConfigs returned 0 configs");
        return -1;
    }
    configs = calloc(numConfigs, sizeof(EGLConfig));
    eglGetConfigs(display, configs, numConfigs, &numConfigs);
    int i;
    LOGD("EGL configurations %d", numConfigs);
    for (i = 0; i < numConfigs; ++i)
    {
        int j;
        LOGD("\tConfig %p index %d", configs[i], i);
        engine_log_egl_config(display, configs[i], ANDROID_LOG_VERBOSE);
    }
    free(configs);

    /* Here, the application chooses the configuration it desires. In this
     * sample, we have a very simplified selection process, where we pick
     * the first EGLConfig that matches our criteria */
    eglChooseConfig(display, attribs, &config, 1, &numConfigs);

    if (numConfigs == 0)
    {   
        LOGE("Unable to find a matching EGL configuration");
        return -1;
    }
    LOGI("Using config %p of %d configs", config, numConfigs);
    engine_log_egl_config(display, config, ANDROID_LOG_INFO);

    /* EGL_NATIVE_VISUAL_ID is an attribute of the EGLConfig that is
     * guaranteed to be accepted by ANativeWindow_setBuffersGeometry().
     * As soon as we picked a EGLConfig, we can safely reconfigure the
     * ANativeWindow buffers to match, using EGL_NATIVE_VISUAL_ID. */
    eglGetConfigAttrib(display, config, EGL_NATIVE_VISUAL_ID, &format);

    // By passing non-zero width and height, it will trigger using the hw scaler, 
    // see http://android-developers.blogspot.com/2013_09_01_archive.html
    ANativeWindow_setBuffersGeometry(engine->app->window, egl_width, egl_height, format);

    int attrib_list[] = {
        EGL_CONTEXT_CLIENT_VERSION, 2,
        EGL_NONE
    };

    surface = eglCreateWindowSurface(display, config, engine->app->window, NULL);
    context = eglCreateContext(display, config, EGL_NO_CONTEXT, attrib_list);
    
    // Preserving the backbuffer for Android view apps is necessary since Android 3.0, 
    // on architectures supporting it (Imagination doesn't, Qualcomm and NVIDIA do)
    // @see https://android.googlesource.com/platform/frameworks/base.git/+/244ada1d35419b7be9de0fc833bb03955b725ffa%5E!/
    // @see http://stackoverflow.com/questions/5359361/android-opengl-blending-similar-to-iphone
    if (egl_swap_preserve_bit)
    {
        eglSurfaceAttrib(display, surface, EGL_SWAP_BEHAVIOR, EGL_BUFFER_PRESERVED);
    }

    // Dump EGL surface information
    LOGI("EGL Surface information");
    engine_log_egl_surface(display, surface, ANDROID_LOG_INFO);

    // Get the width & height in case the requested values were zero or modified
    // by EGL
    eglQuerySurface(display, surface, EGL_WIDTH, &egl_width);
    eglQuerySurface(display, surface, EGL_HEIGHT, &egl_height);

    if (eglMakeCurrent(display, surface, surface, context) == EGL_FALSE) 
    {
        LOGW("Unable to eglMakeCurrent");
        return -1;
    }
    LOGI("Context made current");

    // Dump GL information
    LOGI("GL information");
    LOGI("\tRenderer: %s", glGetString(GL_RENDERER));
    LOGI("\tVendor: %s", glGetString(GL_VENDOR));
    LOGI("\tVersion: %s", glGetString(GL_VERSION));
    LOGI("\tShading Language: %s", glGetString(GL_SHADING_LANGUAGE_VERSION));
    LOGI("\tExtensions: %s", glGetString(GL_EXTENSIONS));

    engine->display = display;
    engine->context = context;
    engine->surface = surface;
    engine->width = egl_width;
    engine->height = egl_height;
    engine->state.angle = 0;

    // Initialize GL state.
    // glEnable(GL_CULL_FACE);
    // glDisable(GL_DEPTH_TEST);

    return 0;
}

void draw(AAssetManager* pAssetManager, int draw_limit, int frame_limit);

/**
 * Just the current frame in the display.
 */
static void engine_draw_frame(struct engine* engine) {
    if (engine->display == NULL) 
    {
        // No display.
        LOGW("No display!");
        return;
    }

    // Just fill the screen with a color.
    //glClearColor(((float)engine->state.x)/engine->width, engine->state.angle,
    //        ((float)engine->state.y)/engine->height, 1);
    LOGI("GL error is 0x%x", glGetError());
    //glClear(GL_COLOR_BUFFER_BIT);
    LOGI("GL error is 0x%x", glGetError());

    if (stop_motion)
    {
        // A tap is a few events, down + up
        if (frame_limit % 3 == 0)
        {
            draw(engine->app->activity->assetManager, 0x7FFFFFFF, frame_limit/3);
            eglSwapBuffers(engine->display, engine->surface);
        }
        draw_limit++;
        frame_limit++;

        engine->animating = 0;
    }
    else
    {
        draw(engine->app->activity->assetManager, 0x7FFFFFFF, frame_limit);
        eglSwapBuffers(engine->display, engine->surface);
        draw_limit++;
        frame_limit++;

        engine->animating = 1;
    }
}

/**
 * Tear down the EGL context currently associated with the display.
 */
static void engine_term_display(struct engine* engine) {
    if (engine->display != EGL_NO_DISPLAY) 
    {
        eglMakeCurrent(engine->display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        if (engine->context != EGL_NO_CONTEXT) 
        {
            eglDestroyContext(engine->display, engine->context);
        }
        if (engine->surface != EGL_NO_SURFACE) 
        {
            eglDestroySurface(engine->display, engine->surface);
        }
        eglTerminate(engine->display);
    }
    engine->animating = 0;
    engine->display = EGL_NO_DISPLAY;
    engine->context = EGL_NO_CONTEXT;
    engine->surface = EGL_NO_SURFACE;
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
        engine->animating = 1;
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
                    abort();
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
            engine->animating = 0;
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

void activity_load_config(JNIEnv* env, ANativeActivity* activity)
{
    LOGI("Loading activity configuration");

    // Load the configuration from the intent's extra parameters

    jobject intent = activity_get_intent(env, activity);

    egl_swap_preserve_bit = intent_get_boolean_extra(env, intent, "egl_swap_preserve_bit", egl_swap_preserve_bit);
    egl_window_bit = intent_get_boolean_extra(env, intent, "egl_window_bit", egl_window_bit);
    egl_pbuffer_bit = intent_get_boolean_extra(env, intent, "egl_pbuffer_bit", egl_pbuffer_bit);

    egl_width = intent_get_int_extra(env, intent, "egl_width", egl_width);
    egl_height = intent_get_int_extra(env, intent, "egl_height", egl_height);

    egl_red_size      = intent_get_int_extra(env, intent, "egl_red_size", egl_red_size);
    egl_blue_size     = intent_get_int_extra(env, intent, "egl_blue_size", egl_blue_size);
    egl_green_size    = intent_get_int_extra(env, intent, "egl_green_size", egl_green_size);
    egl_alpha_size    = intent_get_int_extra(env, intent, "egl_alpha_size", egl_alpha_size);
    egl_depth_size    = intent_get_int_extra(env, intent, "egl_depth_size", egl_depth_size);
    egl_stencil_size  = intent_get_int_extra(env, intent, "egl_stencil_size", egl_stencil_size);

    draw_limit        = intent_get_int_extra(env, intent, "draw_limit", draw_limit);
    frame_limit       = intent_get_int_extra(env, intent, "frame_limit", frame_limit);
    stop_motion       = intent_get_boolean_extra(env, intent, "stop_motion", stop_motion);

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

    LOGI("Runtime configuration");
    LOGI("\tdraw_limit: %d", draw_limit);
    LOGI("\tframe_limit: %d", frame_limit);
    LOGI("\tstop_motion: %d", stop_motion);
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
            // XXX Do frame statistics
            // XXX Do screenshot saving
            // XXX When done all frames, stop animating
            // XXX When done all frames, do full statistics (captured, replayed)
        }
    }
}
