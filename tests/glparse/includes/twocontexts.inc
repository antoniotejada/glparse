int egl_width  = 800;
int egl_height = 1205;
static const GLsizei max_viewport_width  = 800;
static const GLsizei max_viewport_height = 1205;
static const GLsizei max_scissor_width  = 800;
static const GLsizei max_scissor_height = 1205;

void draw(DrawState* param_DrawState_ptr_0)
{
    // WAR: There's a bug in the trace recorder with eglMakeCurrent inside the
    //      same swapbuffers where the trace recorder ignores everything in
    //      between eglMakeCurrents (fails to to flush the trace?)
    //      The OpenGL code is correct since it appears in the screen, but
    //      the trace fails to capture it.
    //      The workaround is to have a swapbuffers between eglMakeCurrent
    //      (probably eglSwapBuffers causes a flush of the trace?). Note glFinish
    //      doesn't fix the issue.

    static GLuint tex1;
    static GLuint tex2;
    static EGLContext ctx1;
    static EGLContext ctx2;
    switch (param_DrawState_ptr_0->frame_limit)
    {
        case 0:
            ctx1 = eglOverriddenCreateContext(param_DrawState_ptr_0);
            eglOverriddenMakeCurrent(param_DrawState_ptr_0, ctx1);

            glEnable(GL_SCISSOR_TEST);
            glScissor(0,0,200,200);
            glClearColor(1.0, 1.0, 1.0, 0.0);
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
            glGenTextures(1, &tex1);
            glBindTexture(GL_TEXTURE_2D, tex1);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 64, 64, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);
        break;
        case 1:
            // Create a second context with the same configuration as the first and sharing
            // WAR: Note that there's no point in testing non-sharing contexts since
            //     the ES trace doesn't contain information on whether the context is
            //     shared or not
            ctx2 = eglOverriddenCreateContext(param_DrawState_ptr_0);
            eglOverriddenMakeCurrent(param_DrawState_ptr_0, ctx2);

            glEnable(GL_SCISSOR_TEST);
            glScissor(200,200,200,200);
            glClearColor(1.0, 0.0, 1.0, 0.0);
            glClear(GL_COLOR_BUFFER_BIT);
            // Textures created in 1 should work on 2
            glBindTexture(GL_TEXTURE_2D, tex1);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 64, 64, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);

            glGenTextures(1, &tex2);
            glBindTexture(GL_TEXTURE_2D, tex2);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 64, 64, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);
        break;
        case 2:
            eglOverriddenMakeCurrent(param_DrawState_ptr_0, ctx1);

            glEnable(GL_SCISSOR_TEST);
            glScissor(400,400,200,200);
            glClearColor(0.0, 1.0, 1.0, 0.0);
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

            // Textures created in 2 should work on 1
            glBindTexture(GL_TEXTURE_2D, tex1);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 64, 64, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);
        break;
        default:
            LOGI("Reached frame %d end of replay, exiting", param_DrawState_ptr_0->frame_limit);
            exit(EXIT_SUCCESS);
        break;
    }

    // XXX Missing testing other resources, in particular per-program resources
    //     (uniforms, attribs),
}