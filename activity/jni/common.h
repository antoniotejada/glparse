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
 */
#ifndef COMMON_H
#define COMMON_H

#include <EGL/egl.h>
#include <android/log.h>
#include <android_native_app_glue.h>
#include <stdbool.h>


typedef struct {
    // Frequently used fields
    AAssetManager* pAssetManager;
    int draw_limit;
    int frame_limit;

    // Infrequently used fields
    EGLDisplay display;
    EGLSurface surface;
    EGLConfig config;
    EGLContext* contexts;
    int num_contexts;

    // OpenGL state overrides

    // Dither override (enable takes precedence over disable)
    // XXX Add other gl state overrides like max_viewport/scissor_width/height
    // (in case the trace didn't contain those calls)
    bool gl_enable_dither;
    bool gl_disable_dither;
} DrawState;

#define LOGV(...) ((void)__android_log_print(ANDROID_LOG_VERBOSE, "native-activity", __VA_ARGS__))
#define LOGD(...) ((void)__android_log_print(ANDROID_LOG_DEBUG, "native-activity", __VA_ARGS__))
#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "native-activity", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "native-activity", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "native-activity", __VA_ARGS__))
#define LOGF(...) ((void)__android_log_print(ANDROID_LOG_FATAL, "native-activity", __VA_ARGS__))

#endif