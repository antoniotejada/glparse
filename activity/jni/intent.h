#ifndef INTENT_H
#define INTENT_H

#include <jni.h>
#include <stdbool.h>

bool intent_get_boolean_extra(JNIEnv* env, jobject j_intent, const char* extra_name, 
                              bool default_value);
float intent_get_float_extra(JNIEnv* env, jobject j_intent, const char* extra_name, 
                             float default_value);
int intent_get_int_extra(JNIEnv* env, jobject j_intent, const char* extra_name, 
                         int default_value);
char* intent_get_string_extra(JNIEnv* env, jobject j_intent, const char* extra_name, 
                              const char* default_value);

#endif