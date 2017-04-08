//
// Check the supported code flow:
// - conditionals
// - switch statements
// - function calls
//


void a()
{

}

void f()
{
    GLboolean local_GLboolean_0 = GL_FALSE;
    a();
    if (local_GLboolean_0) a();
    if (local_GLboolean_0) {
        a();
        a();
        a();
    }
    if (!TRUE) {
        a();
        a();
        a();
    }
    int local_int_0 = 1;
    switch (local_int_0) {
        case 1:
            a();
            a();
            a();
        break;
        case 2:
            a();
            a();
        break;
        case 3:

        break;
        default:
    }
    a();
    a();
    a();
    a();
    a();
}