#pragma once
#include <stdint.h>
uint32_t sceKernelLoadStartModule(const char*,uint64_t,const void*,uint32_t,void*,void*);
int32_t sceKernelDlsym(int,const char*,void**);
