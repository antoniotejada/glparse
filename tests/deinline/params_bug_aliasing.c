// Test for the following unfixed pointer aliasing bug:
// Multiple calls to
//   openAsset(param_AAssetManager_ptr_0, "filename", &local_AAsset_ptr_0)
//   getAssetBuffer(local_AAsset_ptr_0);
// are deinlined as
//   openAsset(param_AAssetManager_ptr_0, param_char_ptr_1, param_AAsset_ptr_ptr_2);
//   getAssetBuffer(param_AAsset_ptr_3);
// Note how getAssetBuffer calls using a temporary variable that is no
// longer updated by the call to openAsset
// This is currently fixed in the generator by unifying those calls
// into a single openAndGetAssetBuffer
// A better fix would be to do parameter coalescing in an aliasing-aware way

void a(AAssetManager* param_AAssetManager_ptr_0)
{
    AAsset* local_AAsset_ptr_0 = NULL;

    openAsset(param_AAssetManager_ptr_0, "filename", &local_AAsset_ptr_0)
    getAssetBuffer(local_AAsset_ptr_0);
    openAsset(param_AAssetManager_ptr_0, "filename1", &local_AAsset_ptr_0)
    getAssetBuffer(local_AAsset_ptr_0);
    openAsset(param_AAssetManager_ptr_0, "filename2", &local_AAsset_ptr_0)
    getAssetBuffer(local_AAsset_ptr_0);
}

void f(AAssetManager* param_AAssetManager_ptr_0)
{
    a(param_AAssetManager_ptr_0);
    a(param_AAssetManager_ptr_0);
    a(param_AAssetManager_ptr_0);
    a(param_AAssetManager_ptr_0);
    a(param_AAssetManager_ptr_0);
    a(param_AAssetManager_ptr_0);
}