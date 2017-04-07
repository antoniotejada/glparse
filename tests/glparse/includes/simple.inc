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

    glClearColor(1.0, 1.0, 1.0, 0.0);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    int vertex_buffer_id;
    glGenBuffers(1, &vertex_buffer_id);
    glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer_id);
    const char vertices[64] = { 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f };
    glBufferData(GL_ARRAY_BUFFER, 64, vertices, GL_STATIC_DRAW);
    glDisable(GL_SCISSOR_TEST);
    glActiveTexture(GL_TEXTURE0);
    glGenBuffers(1, &vertex_buffer_id);
    glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer_id);
    glBufferData(GL_ARRAY_BUFFER, 131072, 0, GL_DYNAMIC_DRAW);
    int max_combined_texture_image_units;
    glGetIntegerv(GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS, &max_combined_texture_image_units);
    int max_texture_size;
    glGetIntegerv(GL_MAX_TEXTURE_SIZE, &max_texture_size);
    int texture_id;
    glGenTextures(1, &texture_id);
    glBindTexture(GL_TEXTURE_2D, texture_id);
    glEnableVertexAttribArray(0);
    glDisable(GL_BLEND);
    glViewport(0,0,max_viewport_width, max_viewport_height);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 1024, 74, GL_ALPHA, GL_UNSIGNED_BYTE, NULL);
}
