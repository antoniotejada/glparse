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
    GLubyte pixels[] = { 0, 0, 0, 0,  1, 1, 1, 1,  2, 2, 2, 2,  3, 3, 3, 3,  4, 4, 4, 4,  5, 5, 5, 5,  6, 6, 6, 6,  7, 7, 7, 7,  8, 8, 8, 8,  9, 9, 9, 9,  10, 10, 10, 10,  11, 11, 11, 11,  12, 12, 12, 12,  13, 13, 13, 13,  14, 14, 14, 14,  15, 15, 15, 15,  16, 16, 16, 16,  17, 17, 17, 17,  18, 18, 18, 18,  19, 19, 19, 19,  20, 20, 20, 20,  21, 21, 21, 21,  22, 22, 22, 22,  23, 23, 23, 23,  24, 24, 24, 24,  25, 25, 25, 25,  26, 26, 26, 26,  27, 27, 27, 27,  28, 28, 28, 28,  29, 29, 29, 29,  30, 30, 30, 30,  31, 31, 31, 31,  32, 32, 32, 32,  33, 33, 33, 33,  34, 34, 34, 34,  35, 35, 35, 35,  36, 36, 36, 36,  37, 37, 37, 37,  38, 38, 38, 38,  39, 39, 39, 39,  40, 40, 40, 40,  41, 41, 41, 41,  42, 42, 42, 42,  43, 43, 43, 43,  44, 44, 44, 44,  45, 45, 45, 45,  46, 46, 46, 46,  47, 47, 47, 47,  48, 48, 48, 48,  49, 49, 49, 49,  50, 50, 50, 50,  51, 51, 51, 51,  52, 52, 52, 52,  53, 53, 53, 53,  54, 54, 54, 54,  55, 55, 55, 55,  56, 56, 56, 56,  57, 57, 57, 57,  58, 58, 58, 58,  59, 59, 59, 59,  60, 60, 60, 60,  61, 61, 61, 61,  62, 62, 62, 62,  63, 63, 63, 63,  64, 64, 64, 64,  65, 65, 65, 65,  66, 66, 66, 66,  67, 67, 67, 67,  68, 68, 68, 68,  69, 69, 69, 69,  70, 70, 70, 70,  71, 71, 71, 71,  72, 72, 72, 72,  73, 73, 73, 73,  74, 74, 74, 74,  75, 75, 75, 75,  76, 76, 76, 76,  77, 77, 77, 77,  78, 78, 78, 78,  79, 79, 79, 79,  80, 80, 80, 80,  81, 81, 81, 81,  82, 82, 82, 82,  83, 83, 83, 83,  84, 84, 84, 84,  85, 85, 85, 85,  86, 86, 86, 86,  87, 87, 87, 87,  88, 88, 88, 88,  89, 89, 89, 89,  90, 90, 90, 90,  91, 91, 91, 91,  92, 92, 92, 92,  93, 93, 93, 93,  94, 94, 94, 94,  95, 95, 95, 95,  96, 96, 96, 96,  97, 97, 97, 97,  98, 98, 98, 98,  99, 99, 99, 99,  100, 100, 100, 100,  101, 101, 101, 101,  102, 102, 102, 102,  103, 103, 103, 103,  104, 104, 104, 104,  105, 105, 105, 105,  106, 106, 106, 106,  107, 107, 107, 107,  108, 108, 108, 108,  109, 109, 109, 109,  110, 110, 110, 110,  111, 111, 111, 111,  112, 112, 112, 112,  113, 113, 113, 113,  114, 114, 114, 114,  115, 115, 115, 115,  116, 116, 116, 116,  117, 117, 117, 117,  118, 118, 118, 118,  119, 119, 119, 119,  120, 120, 120, 120,  121, 121, 121, 121,  122, 122, 122, 122,  123, 123, 123, 123,  124, 124, 124, 124,  125, 125, 125, 125,  126, 126, 126, 126,  127, 127, 127, 127,  128, 128, 128, 128,  129, 129, 129, 129,  130, 130, 130, 130,  131, 131, 131, 131,  132, 132, 132, 132,  133, 133, 133, 133,  134, 134, 134, 134,  135, 135, 135, 135,  136, 136, 136, 136,  137, 137, 137, 137,  138, 138, 138, 138,  139, 139, 139, 139,  140, 140, 140, 140,  141, 141, 141, 141,  142, 142, 142, 142,  143, 143, 143, 143,  144, 144, 144, 144,  145, 145, 145, 145,  146, 146, 146, 146,  147, 147, 147, 147,  148, 148, 148, 148,  149, 149, 149, 149,  150, 150, 150, 150,  151, 151, 151, 151,  152, 152, 152, 152,  153, 153, 153, 153,  154, 154, 154, 154,  155, 155, 155, 155,  156, 156, 156, 156,  157, 157, 157, 157,  158, 158, 158, 158,  159, 159, 159, 159,  160, 160, 160, 160,  161, 161, 161, 161,  162, 162, 162, 162,  163, 163, 163, 163,  164, 164, 164, 164,  165, 165, 165, 165,  166, 166, 166, 166,  167, 167, 167, 167,  168, 168, 168, 168,  169, 169, 169, 169,  170, 170, 170, 170,  171, 171, 171, 171,  172, 172, 172, 172,  173, 173, 173, 173,  174, 174, 174, 174,  175, 175, 175, 175,  176, 176, 176, 176,  177, 177, 177, 177,  178, 178, 178, 178,  179, 179, 179, 179,  180, 180, 180, 180,  181, 181, 181, 181,  182, 182, 182, 182,  183, 183, 183, 183,  184, 184, 184, 184,  185, 185, 185, 185,  186, 186, 186, 186,  187, 187, 187, 187,  188, 188, 188, 188,  189, 189, 189, 189,  190, 190, 190, 190,  191, 191, 191, 191,  192, 192, 192, 192,  193, 193, 193, 193,  194, 194, 194, 194,  195, 195, 195, 195,  196, 196, 196, 196,  197, 197, 197, 197,  198, 198, 198, 198,  199, 199, 199, 199,  200, 200, 200, 200,  201, 201, 201, 201,  202, 202, 202, 202,  203, 203, 203, 203,  204, 204, 204, 204,  205, 205, 205, 205,  206, 206, 206, 206,  207, 207, 207, 207,  208, 208, 208, 208,  209, 209, 209, 209,  210, 210, 210, 210,  211, 211, 211, 211,  212, 212, 212, 212,  213, 213, 213, 213,  214, 214, 214, 214,  215, 215, 215, 215,  216, 216, 216, 216,  217, 217, 217, 217,  218, 218, 218, 218,  219, 219, 219, 219,  220, 220, 220, 220,  221, 221, 221, 221,  222, 222, 222, 222,  223, 223, 223, 223,  224, 224, 224, 224,  225, 225, 225, 225,  226, 226, 226, 226,  227, 227, 227, 227,  228, 228, 228, 228,  229, 229, 229, 229,  230, 230, 230, 230,  231, 231, 231, 231,  232, 232, 232, 232,  233, 233, 233, 233,  234, 234, 234, 234,  235, 235, 235, 235,  236, 236, 236, 236,  237, 237, 237, 237,  238, 238, 238, 238,  239, 239, 239, 239,  240, 240, 240, 240,  241, 241, 241, 241,  242, 242, 242, 242,  243, 243, 243, 243,  244, 244, 244, 244,  245, 245, 245, 245,  246, 246, 246, 246,  247, 247, 247, 247,  248, 248, 248, 248,  249, 249, 249, 249,  250, 250, 250, 250,  251, 251, 251, 251,  252, 252, 252, 252,  253, 253, 253, 253,  254, 254, 254, 254,  255, 255, 255, 255 };

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 16, 16, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels);

    glIsTexture(texture_id);

    exitOnGLError("creating first texture");

    // create again to check that asset file coalescing works
    glGenTextures(1, &texture_id);
    glBindTexture(GL_TEXTURE_2D, texture_id);

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 16, 16, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels);

    glIsTexture(texture_id);

    exitOnGLError("creating second texture");

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
        GLfloat unif[3] = {1.0f, 2.0f, 3.0f };
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

    exitOnGLError("creating color texture");

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
