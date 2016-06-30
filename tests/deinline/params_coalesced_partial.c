//
// Verify that parameters with the same value are coalesced, even if the matching
// pairs in one invocation don't match one-to-one another invocation and
// there are also non-coalescing usages of the parameter between invocations
//
// In the function calls a and c below the first param_int_0 is not coalesceable
// but the third and fourth usages are, similarly with f1 and param_int_1
// Also, the parameters used on a() on f1 vs. f2 have different names, still should
// be coalesced and similarly with c().
// Additionally, function call e below is constant across occurrences, so it shouldn't
// require a formal parameter
//
void f1(param_int_0, param_int_1)
{
    a(param_int_0, param_int_1, param_int_0, param_int_0);
    b(1);
    c(param_int_0, param_int_1, param_int_0, param_int_0);
    d(3);
    e(4);
    f(5);
}

void f2(param_int_0, param_int_1, param_int_2, param_int_3)
{
    a(param_int_1, param_int_3, param_int_1, param_int_1);
    b(0);
    c(param_int_1, param_int_3, param_int_1, param_int_1);
    d(2);
    e(4);
    f(4);
}