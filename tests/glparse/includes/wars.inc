int egl_width  = 800;
int egl_height = 1205;
static const GLsizei max_viewport_width  = 800;
static const GLsizei max_viewport_height = 1205;
static const GLsizei max_scissor_width  = 800;
static const GLsizei max_scissor_height = 1205;

void draw(DrawState* param_DrawState_ptr_0)
{
    if (param_DrawState_ptr_0->frame_limit > 0)
    {
        LOGI("Reached frame %d end of replay, exiting", param_DrawState_ptr_0->frame_limit);
        exit(EXIT_SUCCESS);
    }

    EGLContext context = eglOverriddenCreateContext(param_DrawState_ptr_0);
    eglOverriddenMakeCurrent(param_DrawState_ptr_0, context);

    // Sonicdash traces use several desktop GL calls
    glHint(GL_FRAGMENT_SHADER_DERIVATIVE_HINT, GL_DONT_CARE);
    // glGetProgram/ShaderInfoLog in some Android version stores integers instead
    // of pointers, glparse should swap them properly
    GLuint program = 0;
    GLuint shader = 0;
    GLsizei bufsize;
    GLsizei length;
    GLchar info;
    glGetProgramInfoLog(program, 0, &length, &info);
    glGetShaderInfoLog(shader, 0, &length, &info);

    // gltrace stores integers instead of pointers, make sure they are fixed up
    GLint range;
    GLint precision;
    glGetShaderPrecisionFormat(GL_FRAGMENT_SHADER, GL_HIGH_INT, &range, &precision);
}
