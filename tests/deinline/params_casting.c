//
// Verify that parameters are casted properly to prevent compiler warnings.
//
// In the function calls a and c below param_int_0 is used twice, but when refactored
// into a new function, it should be coalesced and only appear once in that
// new function's formal parameters
// Additionally, function call e below is constant across occurrences, so it shouldn't
// require a formal parameter
//

void f1(int param_int_0)
{
    GLubyte* local_GLubyte_ptr_0;
    a(0x0);
    a(0x500);
    a(10000);
    a(local_GLubyte_ptr_0);
}

void f2(int param_int_0)
{
    GLubyte* local_GLubyte_ptr_0;
    a(local_GLubyte_ptr_0);
    a(0x0);
    a(local_GLubyte_ptr_0);
    a(0x500);
    a(10000);
}