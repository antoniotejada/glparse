//
// Check that functions are deinlined even with local declarations and empty lines
// in between
//

void a()
{

}

void f()
{
    GLchar local_char_ptr_0[] = "position";
    a();
    float local_float_ptr_1[] = { 0.00249999994412, 0.0, 0.0, 0.0, 0.0, -0.00165975105483, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, -1.0, 1.0, -0.0, 1.0 };
    a();
    const char local_const_char_ptr_2[64] = { 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f, 0x0, 0x0, 0x80, 0x3f };
    a();

    a();

    a();

    a();
}