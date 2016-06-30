//
// Verify that parameters with the same value are coalesced
//
// In the function calls a and c below param_int_0 is used twice, but when refactored
// into a new function, it should be coalesced and only appear once in that
// new function's formal parameters
// Additionally, function call e below is constant across occurrences, so it shouldn't
// require a formal parameter
//
void f1(param_int_0, param_int_1)
{
    a(param_int_0, param_int_1, param_int_0);
    b(1);
    c(param_int_0, param_int_1, param_int_0);
    d(3);
    e(4);
    f(5);
}

void f2(param_int_0, param_int_1)
{
    a(param_int_0, param_int_1, param_int_0);
    b(0);
    c(param_int_0, param_int_1, param_int_0);
    d(2);
    e(4);
    f(4);
}