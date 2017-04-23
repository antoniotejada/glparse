// Test for the following pointer aliasing bug:
// Multiple calls to
//   openAsset(param_AAssetManager_ptr_0, "filename", &local_AAsset_ptr_0)
//   getAssetBuffer(local_AAsset_ptr_0);
// are deinlined as
//   openAsset(param_AAssetManager_ptr_0, param_char_ptr_1, param_AAsset_ptr_ptr_2);
//   getAssetBuffer(param_AAsset_ptr_3);
// Note how getAssetBuffer calls using a temporary variable that is no
// longer updated by the call to openAsset
// This is currently fixed by coalescing the variable usage into a pointer
// dereference
// Note that there's no support for deinlining aliased and non-aliased occurrences
// and will throw an exception

void a(AAssetManager* param_AAssetManager_ptr_0)
{
    AAsset* local_AAsset_ptr_0 = NULL;

    // First form of aliasing, address-of and pointer
    openAsset(param_AAssetManager_ptr_0, "filename", &local_AAsset_ptr_0);
    getAssetBuffer(local_AAsset_ptr_0);
    // Check for several aliasing occurrence support
    getAssetBuffer(local_AAsset_ptr_0);
    openAsset(param_AAssetManager_ptr_0, "filename1", &local_AAsset_ptr_0);
    getAssetBuffer(local_AAsset_ptr_0);
    openAsset(param_AAssetManager_ptr_0, "filename2", &local_AAsset_ptr_0);
    getAssetBuffer(local_AAsset_ptr_0);

    // Uncommenting this should fire an exception, mix of aliased and non-aliased
    // occurrences is not supported
    // AAsset* local_AAsset_ptr_1 = NULL;
    // openAsset(param_AAssetManager_ptr_0, "filename2", &local_AAsset_ptr_0);
    // getAssetBuffer(local_AAsset_ptr_1);
}

void b(AAssetManager* param_AAssetManager_ptr_0)
{
    AAsset* local_AAsset_ptr_ptr_1 = NULL;

    // Second form of aliasing, pointer and indexing
    openAsset(param_AAssetManager_ptr_0, "filename2", local_AAsset_ptr_ptr_1);
    getAssetBuffer(local_AAsset_ptr_ptr_1[1]);
    // Check for several aliasing occurrence support
    getAssetBuffer(local_AAsset_ptr_ptr_1[1]);
    openAsset(param_AAssetManager_ptr_0, "filename2", local_AAsset_ptr_ptr_1);
    getAssetBuffer(local_AAsset_ptr_ptr_1[1]);
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
}