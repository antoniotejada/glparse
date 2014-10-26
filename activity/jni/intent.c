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
 * @see http://developer.android.com/reference/android/content/Intent.html
 * @see http://journals.ecs.soton.ac.uk/java/tutorial/native1.1/implementing/method.html
 * @see http://docs.oracle.com/javase/1.5.0/docs/guide/jni/spec/design.html#wp16696
 * @see http://docs.oracle.com/javase/1.5.0/docs/guide/jni/spec/types.html
 * @see http://docs.oracle.com/javase/1.5.0/docs/guide/jni/spec/functions.html#wp16656
 * @see http://mflerackers.wordpress.com/2013/08/25/using-the-ndk-and-jni-to-build-android-applications/
 *
 * Get method signatures via
 * javap.exe -s -classpath c:\adt-bundle-windows-x86_64-20140321\sdk\platforms\android-19\android.jar android.content.Intent
 */
#include <string.h>

#include "common.h"
#include "intent.h"

float intent_get_float_extra(JNIEnv* env, jobject j_intent, const char* extra_name, float default_value)
{
    jclass icl = (*env)->GetObjectClass(env, j_intent);
    jmethodID gseid = (*env)->GetMethodID(env, icl, "getFloatExtra", "(Ljava/lang/String;F)F");
    jstring j_extra_name = (*env)->NewStringUTF(env, extra_name);

    jfloat result = (*env)->CallFloatMethod(env, j_intent, gseid, j_extra_name, default_value);

    (*env)->DeleteLocalRef(env, j_extra_name);

    return result;
}

int intent_get_int_extra(JNIEnv* env, jobject j_intent, const char* extra_name, int default_value)
{
    jclass icl = (*env)->GetObjectClass(env, j_intent);
    jmethodID gseid = (*env)->GetMethodID(env, icl, "getIntExtra", "(Ljava/lang/String;I)I");
    jstring j_extra_name = (*env)->NewStringUTF(env, extra_name);

    jint result = (*env)->CallIntMethod(env, j_intent, gseid, j_extra_name, default_value);

    (*env)->DeleteLocalRef(env, j_extra_name);

    return result;
}

bool intent_get_boolean_extra(JNIEnv* env, jobject j_intent, const char* extra_name, bool default_value)
{
    LOGV("get_boolean_extra for *env %p intent %p extra_name %s", *env, j_intent, extra_name);

    jclass icl = (*env)->GetObjectClass(env, j_intent);
    jmethodID gseid = (*env)->GetMethodID(env, icl, "getBooleanExtra", "(Ljava/lang/String;Z)Z");
    jstring j_extra_name = (*env)->NewStringUTF(env, extra_name);

    jboolean result = (*env)->CallIntMethod(env, j_intent, gseid, j_extra_name, default_value);

    (*env)->DeleteLocalRef(env, j_extra_name);

    return (result != JNI_FALSE);
}

/**
 * @return Zero-terminated UTF string or NULL in case of error.
 * Caller is responsible of freeing the result string
 */
char* intent_get_string_extra(JNIEnv* env, jobject j_intent, const char* extra_name, const char* default_value)
{
    // Resolve class and method
    jclass icl = (*env)->GetObjectClass(env, j_intent);
    jmethodID gseid = (*env)->GetMethodID(env, icl, "getStringExtra", "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;");

    // Marshal parameters
    jstring j_default_value = (*env)->NewStringUTF(env, default_value);
    jstring j_extra_name = (*env)->NewStringUTF(env, extra_name);

    // Call method
    jstring j_result = (*env)->CallObjectMethod(env, j_intent, gseid, j_extra_name, default_value);

    // Free marshalled parameters
    (*env)->DeleteLocalRef(env, j_extra_name);
    (*env)->DeleteLocalRef(env, j_default_value);

    // Unmarshall result
    const char* j_utf_result = (*env)->GetStringUTFChars(env, j_result, NULL);
    char* result = strdup(j_utf_result);
    (*env)->ReleaseStringUTFChars(env, j_result, j_utf_result);
    
    return result;
}
