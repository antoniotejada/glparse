#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>

#include <android/log.h>

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "native-activity", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "native-activity", __VA_ARGS__))

#ifndef GL_RED
// GLES2 headers don't have this one, but GLES3 do
#define GL_RED 0x1903
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
