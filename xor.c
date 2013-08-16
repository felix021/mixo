#ifdef __WIN32
#define DLLEXPORT __declspec(dllexport)
#else
#define DLLEXPORT
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

unsigned char *table = NULL;

DLLEXPORT int set_xor_table(const unsigned char *str, int len)
{
    int i;
    table = (unsigned char *)malloc(len);
    if (table == NULL)
        return 1;
    memcpy(table, str, len);
    return 0;
}

DLLEXPORT int xor(unsigned char *buf, int len, int pos)
{
    int i;
    for (i = 0; i < len; i++, pos++)
        buf[i] ^= table[pos];
    return 0;
}
