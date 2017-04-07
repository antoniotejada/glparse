int egl_width  = 800;
int egl_height = 1205;
static const GLsizei max_viewport_width  = 800;
static const GLsizei max_viewport_height = 1205;
static const GLsizei max_scissor_width  = 800;
static const GLsizei max_scissor_height = 1205;

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

    glClearColor(1.0, 1.0, 1.0, 0.0);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    // Create a vertex buffer
    int vertex_buffer_id;
    glGenBuffers(1, &vertex_buffer_id);
    glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer_id);
    const char vertices[64] = { 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f };
    glBufferData(GL_ARRAY_BUFFER, 64, vertices, GL_STATIC_DRAW);
    glIsBuffer(vertex_buffer_id);

    // Create a texture
    GLuint texture_id;
    glGenTextures(1, &texture_id);
    glBindTexture(GL_TEXTURE_2D, texture_id);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 1024, 74, GL_ALPHA, GL_UNSIGNED_BYTE, NULL);
    glIsTexture(texture_id);

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
    for (i = 0; i < 2; ++i)
    {
        // Create a program
        GLint shader_program_id;
        shader_program_id = glCreateProgram();
        glAttachShader(shader_program_id, vertex_shader_id);
        glAttachShader(shader_program_id, fragment_shader_id);
        glLinkProgram(shader_program_id);
        glGetProgramiv(shader_program_id, GL_LINK_STATUS, &success);
        if (!success) {
            glGetProgramInfoLog(shader_program_id, sizeof(info_log), NULL, info_log);
            LOGE("ERROR::SHADER::PROGRAM::LINKING_FAILED\n%s\n", info_log);
        }

        glUseProgram(shader_program_id);

        // Get attribute location
        GLuint attr_location = glGetAttribLocation(shader_program_id, "position");
        GLchar attr_name[20];
        GLenum attr_type;
        GLint attr_size;
        GLsizei attr_length;
        glGetActiveAttrib(shader_program_id, attr_location, sizeof(attr_name), &attr_length, &attr_size, &attr_type, attr_name);

        // Get uniform location
        GLint unif_location = glGetUniformLocation(shader_program_id, "origin");
        GLfloat unif[3];
        glUniform3fv(attr_location, 1, unif);
    }

    // Renderbuffers
    GLuint renderbuffer_id;
    glGenRenderbuffers(1, &renderbuffer_id);
    glBindRenderbuffer(GL_RENDERBUFFER, renderbuffer_id);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_RGBA4, 1024, 768);

    // Framebuffers
    GLuint framebuffer_id;
    glGenFramebuffers(1, &framebuffer_id);
    glBindFramebuffer(GL_FRAMEBUFFER, framebuffer_id);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER,
        renderbuffer_id);

    // Render to texture path
    /*
    glBindTexture(GL_TEXTURE_2D, 0);
    glBindFramebuffer(GL_FRAMEBUFFER, framebuffer_id);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                    GL_TEXTURE_2D, colour_texture, 0);

    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                    GL_TEXTURE_2D, depth_texture, 0);*/

}
