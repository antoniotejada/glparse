//
// Verify that common parameters in the call-sites are removed from the function
// parameters
//
// Function calls a, c and e below use common parameters in all call-sites, so
// shouldn't appear in the factored function parameters
// The rest of the function calls should take parameters
//
void f1()
{
    a(0);
    b(1);
    c(2);
    d(3);
    e(4);
    f(5);
}

void f2()
{
    a(0);
    b(0);
    c(2);
    d(2);
    e(4);
    f(4);
}