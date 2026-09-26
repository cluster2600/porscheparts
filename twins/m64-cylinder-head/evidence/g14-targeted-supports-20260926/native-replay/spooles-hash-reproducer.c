/* Private witness using the actual SPOOLES hash API, not an FE solve. */
#include "I2Ohash/I2Ohash.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    static const int keys[][2] = {
        {46339,46339}, {46340,46340}, {46339,46340}, {46340,46339},
        {0,0}, {0,1}, {1,0}, {49775,49775}, {49776,49776}
    };
    int payload[sizeof(keys)/sizeof(keys[0])];
    const int n = (int)(sizeof(keys)/sizeof(keys[0]));
    I2Ohash *table;
    void *found = NULL;
    int i;
    assert(INT_MAX == 2147483647);
    assert(((long long)46341*46341)%49777 == 8947);
    assert(argc == 2);
    table = I2Ohash_new();
    I2Ohash_init(table,49777,32,32);
    if (strcmp(argv[1],"insert") == 0) {
        I2Ohash_insert(table,46340,46340,&payload[0]);
    } else if (strcmp(argv[1],"locate") == 0) {
        (void)I2Ohash_locate(table,46340,46340,&found);
    } else if (strcmp(argv[1],"remove") == 0) {
        (void)I2Ohash_remove(table,46340,46340,&found);
    } else if (strcmp(argv[1],"all") == 0) {
        for (i=0;i<n;i++) {
            payload[i] = 100+i;
            I2Ohash_insert(table,keys[i][0],keys[i][1],&payload[i]);
        }
        assert(table->nitem == n);
        for (i=0;i<n;i++) {
            found = NULL;
            assert(I2Ohash_locate(table,keys[i][0],keys[i][1],&found) == 1);
            assert(found == &payload[i]);
            assert(*(int *)found == 100+i);
        }
        assert(I2Ohash_locate(table,17,31,&found) == 0);
        for (i=n-1;i>=0;i--) {
            found = NULL;
            assert(I2Ohash_remove(table,keys[i][0],keys[i][1],&found) == 1);
            assert(found == &payload[i]);
            assert(I2Ohash_locate(table,keys[i][0],keys[i][1],&found) == 0);
            assert(I2Ohash_remove(table,keys[i][0],keys[i][1],&found) == 0);
        }
        assert(table->nitem == 0);
        /* Equal-key insertion preserves the original first-match behaviour. */
        I2Ohash_insert(table,46340,46340,&payload[0]);
        I2Ohash_insert(table,46340,46340,&payload[1]);
        assert(I2Ohash_remove(table,46340,46340,&found) == 1);
        assert(found == &payload[1]);
        assert(I2Ohash_remove(table,46340,46340,&found) == 1);
        assert(found == &payload[0]);
        assert(table->nitem == 0);
    } else {
        return 2;
    }
    I2Ohash_free(table);
    puts("hash witness passed");
    return 0;
}
