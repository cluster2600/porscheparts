#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>

typedef int CUresult;
typedef int CUdevice;
typedef void *CUcontext;
typedef uint64_t CUdeviceptr;

int main(void) {
    void *library = dlopen("libcuda.so.1", RTLD_NOW | RTLD_LOCAL);
    if (library == NULL) {
        fputs("cuda_driver_library_missing\n", stderr);
        return 2;
    }
#define LOAD(name) typeof(name) *p_##name = (typeof(name) *)dlsym(library, #name)
    CUresult cuInit(unsigned int);
    CUresult cuDeviceGetCount(int *);
    CUresult cuDeviceGet(CUdevice *, int);
    CUresult cuCtxCreate_v2(CUcontext *, unsigned int, CUdevice);
    CUresult cuCtxDestroy_v2(CUcontext);
    CUresult cuMemAlloc_v2(CUdeviceptr *, size_t);
    CUresult cuMemFree_v2(CUdeviceptr);
    LOAD(cuInit); LOAD(cuDeviceGetCount); LOAD(cuDeviceGet);
    LOAD(cuCtxCreate_v2); LOAD(cuCtxDestroy_v2); LOAD(cuMemAlloc_v2); LOAD(cuMemFree_v2);
    if (!p_cuInit || !p_cuDeviceGetCount || !p_cuDeviceGet || !p_cuCtxCreate_v2 ||
        !p_cuCtxDestroy_v2 || !p_cuMemAlloc_v2 || !p_cuMemFree_v2) {
        fputs("cuda_driver_symbol_missing\n", stderr);
        return 3;
    }
    int count = 0;
    CUdevice device = 0;
    CUcontext context = NULL;
    CUdeviceptr pointer = 0;
    if (p_cuInit(0) != 0 || p_cuDeviceGetCount(&count) != 0 || count < 1 ||
        p_cuDeviceGet(&device, 0) != 0 || p_cuCtxCreate_v2(&context, 0, device) != 0 ||
        p_cuMemAlloc_v2(&pointer, 4096) != 0 || pointer == 0 ||
        p_cuMemFree_v2(pointer) != 0 || p_cuCtxDestroy_v2(context) != 0) {
        fputs("cuda_driver_allocation_failed\n", stderr);
        return 4;
    }
    printf("cuda_driver_allocation_passed devices=%d bytes=4096\n", count);
    dlclose(library);
    return 0;
}
