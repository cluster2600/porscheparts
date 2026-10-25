/* Include the selected source so UBSan instruments its hash arithmetic. */
#include <assert.h>
#include "I2Ohash/src/util.c"

int main(void) {
    const int keys[][2] = {{60000,60000},{99999,99998},{46340,46340}};
    int values[] = {17,23,41};
    I2Ohash *table = I2Ohash_new();
    I2Ohash_init(table,100003,10,10);
    for (int i=0;i<3;++i) I2Ohash_insert(table,keys[i][0],keys[i][1],&values[i]);
    for (int i=0;i<3;++i) {
        void *found = NULL;
        assert(I2Ohash_locate(table,keys[i][0],keys[i][1],&found)==1);
        assert(found==&values[i]);
        assert(I2Ohash_remove(table,keys[i][0],keys[i][1],&found)==1);
        assert(found==&values[i]);
        assert(I2Ohash_locate(table,keys[i][0],keys[i][1],&found)==0);
    }
    I2Ohash_free(table);
    return 0;
}
