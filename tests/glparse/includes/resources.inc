int egl_width  = 800;
int egl_height = 1205;
static const GLsizei max_viewport_width  = 800;
static const GLsizei max_viewport_height = 1205;
static const GLsizei max_scissor_width  = 800;
static const GLsizei max_scissor_height = 1205;


void exitOnGLError(const char* action)
{
    GLenum error = glGetError();

    if (error != GL_NO_ERROR)
    {
        LOGE("GL error 0x%x when %s", error, action);
        exit(EXIT_FAILURE);
    }
}

void draw(DrawState* param_DrawState_ptr_0)
{
    static const GLchar* vertex_shader_source =
        "#version 100\n"
        "attribute vec3 position;\n"
        "uniform vec3 origin;\n"
        "void main() {\n"
        "   gl_Position = vec4(position + origin, 1.0);\n"
        "}\n";
    static const GLchar* fragment_shader_source =
        "#version 100\n"
        "void main() {\n"
        "   gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);\n"
        "}\n";

    if (param_DrawState_ptr_0->frame_limit > 0)
    {
        LOGI("Reached frame %d end of replay, exiting", param_DrawState_ptr_0->frame_limit);
        exit(EXIT_SUCCESS);
    }

    EGLContext context = eglOverriddenCreateContext(param_DrawState_ptr_0);
    eglOverriddenMakeCurrent(param_DrawState_ptr_0, context);
    GLenum error;

    glClearColor(1.0, 1.0, 1.0, 0.0);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    // Create a vertex buffer
    int vertex_buffer_id;
    glGenBuffers(1, &vertex_buffer_id);
    glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer_id);
    const char vertices[64] = { 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f };
    glBufferData(GL_ARRAY_BUFFER, 64, vertices, GL_STATIC_DRAW);
    glIsBuffer(vertex_buffer_id);

    exitOnGLError("creating vertex buffer");

    // Create a texture
    GLuint texture_id;
    glGenTextures(1, &texture_id);
    glBindTexture(GL_TEXTURE_2D, texture_id);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 64, 64, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
    glIsTexture(texture_id);

    exitOnGLError("creating texture");

    // Create a vertex shader
    GLint vertex_shader_id;
    GLint success;
    GLchar info_log[100];
    vertex_shader_id = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vertex_shader_id, 1, &vertex_shader_source, NULL);
    glCompileShader(vertex_shader_id);
    glGetShaderiv(vertex_shader_id, GL_COMPILE_STATUS, &success);
    if (!success)
    {
        glGetShaderInfoLog(vertex_shader_id, sizeof(info_log), NULL, info_log);
        LOGE("ERROR::SHADER::VERTEX::COMPILATION_FAILED\n%s\n", info_log);
        exit(EXIT_FAILURE);
    }

    // Create a fragment shader
    GLint fragment_shader_id;
    fragment_shader_id = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fragment_shader_id, 1, &fragment_shader_source, NULL);
    glCompileShader(fragment_shader_id);
    glGetShaderiv(fragment_shader_id, GL_COMPILE_STATUS, &success);
    if (!success)
    {
        glGetShaderInfoLog(fragment_shader_id, sizeof(info_log), NULL, info_log);
        LOGE("ERROR::SHADER::FRAGMENT::COMPILATION_FAILED\n%s\n", info_log);
        exit(EXIT_FAILURE);
    }

    // Check uniform/attrib program eviction by creating two programs
    int i;
    GLuint shader_program_ids[2];
    for (i = 0; i < 2; ++i)
    {
        // Create a program
        GLuint shader_program_id = glCreateProgram();
        shader_program_ids[i] = shader_program_id;
        glAttachShader(shader_program_id, vertex_shader_id);
        glAttachShader(shader_program_id, fragment_shader_id);
        glLinkProgram(shader_program_id);
        glGetProgramiv(shader_program_id, GL_LINK_STATUS, &success);
        if (!success) {
            glGetProgramInfoLog(shader_program_id, sizeof(info_log), NULL, info_log);
            LOGE("ERROR::SHADER::PROGRAM::LINKING_FAILED\n%s\n", info_log);
        }

        exitOnGLError("creating a program");

        glUseProgram(shader_program_id);

        // Get attribute location
        GLuint attr_location = glGetAttribLocation(shader_program_id, "position");
        GLchar attr_name[20];
        GLenum attr_type;
        GLint attr_size;
        GLsizei attr_length;
        glGetActiveAttrib(shader_program_id, attr_location, sizeof(attr_name), &attr_length, &attr_size, &attr_type, attr_name);

        exitOnGLError("getting attribute location");

        // Get uniform location
        GLint unif_location = glGetUniformLocation(shader_program_id, "origin");
        GLfloat unif[3];
        glUniform3fv(attr_location, 1, unif);

        exitOnGLError("getting uniform location");

        // Get attached shaders
        GLuint attached_shaders[2];
        glGetAttachedShaders(shader_program_id, 2, NULL, attached_shaders);

        exitOnGLError("getting attached shaders");
    }

    // Renderbuffers
    GLuint renderbuffer_id;
    glGenRenderbuffers(1, &renderbuffer_id);
    glBindRenderbuffer(GL_RENDERBUFFER, renderbuffer_id);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_RGBA4, 1024, 768);

    exitOnGLError("creating renderbuffers");

    // Texture Render to texture path
    GLuint colortexture_id;
    glGenTextures(1, &colortexture_id);
    glBindTexture(GL_TEXTURE_2D, colortexture_id);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1024, 768, 0, GL_RGBA, GL_UNSIGNED_BYTE,
        NULL);

    exitOnGLError("creating depth texture");

    // Framebuffers
    GLuint framebuffer_ids[2];
    glGenFramebuffers(2, framebuffer_ids);
    glBindFramebuffer(GL_FRAMEBUFFER, framebuffer_ids[0]);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER,
        renderbuffer_id);

    glBindFramebuffer(GL_FRAMEBUFFER, framebuffer_ids[1]);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D,
        colortexture_id, 0);

    exitOnGLError("creating framebuffers");

    // Check program deletion & shader detach
    for (i = 0; i < (sizeof(shader_program_ids)/sizeof(shader_program_ids[0])); ++i)
    {
        GLuint shader_program_id = shader_program_ids[i];
        glDetachShader(shader_program_id, vertex_shader_id);
        glDetachShader(shader_program_id, fragment_shader_id);

        exitOnGLError("detaching shaders");

        glDeleteProgram(shader_program_id);

        exitOnGLError("deleting programs");
    }

    // Shader deletion
    glDeleteShader(vertex_shader_id);
    glDeleteShader(fragment_shader_id);

    exitOnGLError("deleting shaders");

    // Check buffer deletion
    GLuint buffers[] = { vertex_buffer_id };
    glDeleteBuffers(sizeof(buffers)/ sizeof(buffers[0]), buffers);

    exitOnGLError("deleting buffers");

    // Check framebuffer deletion
    GLuint framebuffers[] = { framebuffer_ids[0], framebuffer_ids[1] };
    glDeleteFramebuffers(sizeof(framebuffers)/sizeof(framebuffers[0]), framebuffers);

    exitOnGLError("deleting framebuffers");

    // Check renderbuffer deletion
    GLuint renderbuffers[] = { renderbuffer_id };
    glDeleteRenderbuffers(sizeof(renderbuffers)/sizeof(renderbuffers[0]), renderbuffers);

    exitOnGLError("deleting renderbuffers");

    // Check texture deletion
    GLuint textures[] = { texture_id, colortexture_id  };
    glDeleteTextures(sizeof(textures)/sizeof(textures[0]), textures);

    exitOnGLError("deleting textures");

}
