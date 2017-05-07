// Test for the following pointer aliasing bug:
// Multiple calls to
//   openAsset(param_AAssetManager_ptr_0, "filename", &local_AAsset_ptr_0)
//   getAssetBuffer(local_AAsset_ptr_0);
// are deinlined as
//   openAsset(param_AAssetManager_ptr_0, param_char_ptr_1, param_AAsset_ptr_ptr_2);
//   getAssetBuffer(param_AAsset_ptr_3);
// Note how getAssetBuffer calls using a temporary variable that is no
// longer updated by the call to openAsset
// This is currently fixed in different ways (coalescing to a global,
// coalescing to pointer dereference, explicit memcpy) depending on whether
// it's pure aliasing or mixed aliasing/non-aliasing in the call sites

// First form of aliasing, address-of and pointer
// Check for several aliasing occurrence support
void a(AAssetManager* param_AAssetManager_ptr_0)
{
    AAsset* local_AAsset_ptr_0 = 0;

    openAsset(param_AAssetManager_ptr_0, "filename", &local_AAsset_ptr_0);
    getAssetBuffer(local_AAsset_ptr_0);
    getAssetBuffer(local_AAsset_ptr_0);
    openAsset(param_AAssetManager_ptr_0, "filename1", &local_AAsset_ptr_0);
    getAssetBuffer(local_AAsset_ptr_0);
    openAsset(param_AAssetManager_ptr_0, "filename2", &local_AAsset_ptr_0);
    getAssetBuffer(local_AAsset_ptr_0);
}

// Second form of aliasing, pointer and indexing
// Check for several aliasing occurrence support
void b(AAssetManager* param_AAssetManager_ptr_0)
{
    AAsset* local_AAsset_ptr_ptr_1 = 0;

    openAsset(param_AAssetManager_ptr_0, "filename", local_AAsset_ptr_ptr_1);
    getAssetBuffer(local_AAsset_ptr_ptr_1[0]);
    getAssetBuffer(local_AAsset_ptr_ptr_1[1]);
    openAsset(param_AAssetManager_ptr_0, "filename1", local_AAsset_ptr_ptr_1);
    getAssetBuffer(local_AAsset_ptr_ptr_1[2]);
    openAsset(param_AAssetManager_ptr_0, "filename2", local_AAsset_ptr_ptr_1);
    getAssetBuffer(local_AAsset_ptr_ptr_1[2]);
}


// Mixed aliasing and non-aliasing
void c(AAssetManager* param_AAssetManager_ptr_0)
{
    AAsset* local_AAsset_ptr_0 = 0;
    AAsset* local_AAsset_ptr_1 = 0;
    openAsset(param_AAssetManager_ptr_0, "filename0", &local_AAsset_ptr_0);
    getAssetBuffer(local_AAsset_ptr_0);
    openAsset(param_AAssetManager_ptr_0, "filename1", &local_AAsset_ptr_0);
    getAssetBuffer(local_AAsset_ptr_1);
    openAsset(param_AAssetManager_ptr_0, "filename2", &local_AAsset_ptr_0);
    getAssetBuffer(0);
}

// Aliasing originating in different instructions
void d_1()
{
    GLuint local_GLuint_0;
    GLuint local_GLuint_1;

    glGenTextures(1, &local_GLuint_0);
    glGenTextures(1, &local_GLuint_1);
    glBindTexture(GL_TEXTURE_2D, local_GLuint_0);
}
void d_2()
{
    GLuint local_GLuint_0;
    GLuint local_GLuint_1;

    glGenTextures(1, &local_GLuint_0);
    glGenTextures(1, &local_GLuint_1);
    glBindTexture(GL_TEXTURE_2D, local_GLuint_1);
}

// Aliasing affecting different instructions
void e_1()
{
    GLuint local_GLuint_0;

    glGenTextures1(1, &local_GLuint_0);
    glBindTexture1(GL_TEXTURE_2D, 0);
    glBindTexture1(GL_TEXTURE_2D, local_GLuint_0);
}

void e_2()
{
    GLuint local_GLuint_0;

    glGenTextures1(1, &local_GLuint_0);
    glBindTexture1(GL_TEXTURE_2D, local_GLuint_0);
    glBindTexture1(GL_TEXTURE_2D, 0);
}

// Aliasing with global variables, parameters should be coalesced into the
// global variables and aliasing avoided
void g_1()
{
    glGenTextures2(1, &global_GLuint_0);
    glBindTexture2(GL_TEXTURE_2D, global_GLuint_0);
    glBindTexture2(GL_TEXTURE_2D, global_GLuint_0);
}

void g_2()
{
    glGenTextures2(1, &global_GLuint_0);
    glBindTexture2(GL_TEXTURE_2D, global_GLuint_0);
    glBindTexture2(GL_TEXTURE_2D, global_GLuint_0);
}

// Non-mixed aliasing with multiple aliased instructions
void i_1()
{
    GLuint local_GLuint_3 = 0;

    glGenTextures3(1, &local_GLuint_3);
    glBindTexture3(GL_TEXTURE_2D, local_GLuint_3);
    glBindTexture3(GL_TEXTURE_2D, local_GLuint_3);
    glTexImage3(0);
}

void i_2()
{
    GLuint local_GLuint_3 = 0;

    glGenTextures3(1, &local_GLuint_3);
    glBindTexture3(GL_TEXTURE_2D, local_GLuint_3);
    glBindTexture3(GL_TEXTURE_2D, local_GLuint_3);
    glTexImage3(1);
}

// Mixed aliasing with multiple aliased instructions, one coalesced into pointer
void j_1()
{
    GLuint local_GLuint_4 = 0;

    glGenTextures4(1, &local_GLuint_4);
    glBindTexture4(GL_TEXTURE_2D, local_GLuint_4);
    glBindTexture4(GL_TEXTURE_2D, local_GLuint_4);
    glTexImage4(0);
}

void j_2()
{
    GLuint local_GLuint_4 = 0;

    glGenTextures4(1, &local_GLuint_4);
    glBindTexture4(GL_TEXTURE_2D, local_GLuint_4);
    glBindTexture4(GL_TEXTURE_2D, 0);
    glTexImage4(1);
}

// Mixed aliasing with single aliasing instruction and multiple aliased instructions,
// none coalesced into pointer
void k_1()
{
    GLuint local_GLuint_5 = 0;

    glGenTextures5(1, &local_GLuint_5);
    glBindTexture5(GL_TEXTURE_2D, local_GLuint_5);
    glBindTexture5(GL_TEXTURE_2D, 0);
    glBindTexture5(GL_TEXTURE_2D, local_GLuint_5);
    glBindTexture5(GL_TEXTURE_2D, 0);
    glTexImage5(0);
}

void k_2()
{
    GLuint local_GLuint_5 = 0;

    glGenTextures5(1, &local_GLuint_5);
    glBindTexture5(GL_TEXTURE_2D, 0);
    glBindTexture5(GL_TEXTURE_2D, local_GLuint_5);
    glBindTexture5(GL_TEXTURE_2D, 0);
    glBindTexture5(GL_TEXTURE_2D, local_GLuint_5);
    glTexImage5(1);
}

void f(AAssetManager* param_AAssetManager_ptr_0)
{
    a(param_AAssetManager_ptr_0);
    a(param_AAssetManager_ptr_0);
    a(param_AAssetManager_ptr_0);
    a(param_AAssetManager_ptr_0);
    a(param_AAssetManager_ptr_0);
    a(param_AAssetManager_ptr_0);
    b(param_AAssetManager_ptr_0);
    b(param_AAssetManager_ptr_0);
    b(param_AAssetManager_ptr_0);
    b(param_AAssetManager_ptr_0);
    b(param_AAssetManager_ptr_0);
    b(param_AAssetManager_ptr_0);
    c(param_AAssetManager_ptr_0);
    c(param_AAssetManager_ptr_0);
    c(param_AAssetManager_ptr_0);
    c(param_AAssetManager_ptr_0);
    c(param_AAssetManager_ptr_0);
    c(param_AAssetManager_ptr_0);
    d_1();
    d_2();
    e_1();
    e_2();
    g_1();
    g_2();
    i_1();
    i_2();
}