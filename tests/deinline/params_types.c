// Test of the different parameter types
void a(int param_int_0, unsigned int param_int_1, float param_float_2, char param_char_3, char* param_char_ptr_4)
{

}

void b(int* param_int_ptr_0, unsigned int* param_int_ptr_1, float* param_float_ptr_2, char* param_char_ptr_3)
{

}

// Parameters
void f1(int param_int_0)
{
    a(param_int_0, param_int_1, param_float_2, param_char_3, param_char_ptr_7);
    a(param_int_0, param_int_1, param_float_2, param_char_3, param_char_ptr_7);
    a(param_int_0, param_int_1, param_float_2, param_char_3, param_char_ptr_7);
}

// Locals
void f2(int param_int_0)
{
    a(local_int_0, local_int_1, local_float_2, local_char_3, local_char_ptr_7);
    a(local_int_0, local_int_1, local_float_2, local_char_3, local_char_ptr_7);
    a(local_int_0, local_int_1, local_float_2, local_char_3, local_char_ptr_7);
}

// Globals
void f3(int param_int_0)
{
    a(global_int_0, global_int_1, global_float_2, global_char_3, global_char_ptr_7);
    a(global_int_0, global_int_1, global_float_2, global_char_3, global_char_ptr_7);
    a(global_int_0, global_int_1, global_float_2, global_char_3, global_char_ptr_7);
}

// Literals,
// strings with commas to check that parameters ignore commas inside strings
// strings with braces to check that parameters ignore braces inside strings
void f4(int param_int_0)
{
    a(0, 1, 2.0, '3', "a, b, c, d {");
    a(0, 1, 2.0, '3', "a, b, c, d {");
    a(0, 1, 2.0, '3', "a, b, c, d {");
}

// Array indexing
void f5(int param_int_0)
{
    a(param_int_ptr_4[0], param_int_ptr_5[1], param_float_ptr_6[2], param_char_ptr_7[2], param_char_ptr_ptr_8[2]);
    a(param_int_ptr_4[0], param_int_ptr_5[1], param_float_ptr_6[2], param_char_ptr_7[2], param_char_ptr_ptr_8[2]);
    a(param_int_ptr_4[0], param_int_ptr_5[1], param_float_ptr_6[2], param_char_ptr_7[2], param_char_ptr_ptr_8[2]);
}

// Pointers
void f6(int param_int_0)
{
    b(param_int_ptr_4, param_int_ptr_5, param_float_ptr_6, param_char_ptr_7);
    b(param_int_ptr_4, param_int_ptr_5, param_float_ptr_6, param_char_ptr_7);
    b(param_int_ptr_4, param_int_ptr_5, param_float_ptr_6, param_char_ptr_7);
}

// Address-of
void f7(int param_int_0)
{
    b(&param_int_0, &param_int_1, &param_float_2, &param_char_3);
    b(&param_int_0, &param_int_1, &param_float_2, &param_char_3);
    b(&param_int_0, &param_int_1, &param_float_2, &param_char_3);
}