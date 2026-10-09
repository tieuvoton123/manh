#pragma once
#include <stdint.h>
typedef int32_t OrbisBgftTaskId;
struct OrbisBgftInitParams{void* heap;size_t heapSize;};
enum OrbisBgftTaskOpt{ORBIS_BGFT_TASK_OPT_DISABLE_CDN_QUERY_PARAM=0x10000};
struct OrbisBgftDownloadParam{int32_t userId,entitlementType;const char* id;const char* contentUrl;const char* contentExUrl;const char* contentName;const char* iconPath;const char* skuId;OrbisBgftTaskOpt option;const char* playgoScenarioId;const char* releaseDate;const char* packageType;const char* packageSubType;uint32_t packageSize;};
struct OrbisBgftDownloadParamEx{OrbisBgftDownloadParam params;uint32_t slot;};
struct OrbisBgftTaskProgress{uint32_t bits;int32_t errorResult;uint32_t length,transferred,lengthTotal,transferredTotal,numIndex,numTotal,restSec,restSecTotal;int32_t preparingPercent,localCopyPercent;};
int32_t sceBgftServiceIntInit(OrbisBgftInitParams*);
int32_t sceBgftServiceIntDownloadRegisterTaskByStorageEx(OrbisBgftDownloadParamEx*,OrbisBgftTaskId*);
int32_t sceBgftServiceDownloadStartTask(OrbisBgftTaskId);
int32_t sceBgftServiceDownloadGetProgress(OrbisBgftTaskId,OrbisBgftTaskProgress*);
