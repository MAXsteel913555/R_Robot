#ifndef __ENCODER_H
#define __ENCODER_H

#include "main.h"
#include "tim.h"

void Encoder_Init(void);
int32_t Encoder_GetLeftFront(void);
int32_t Encoder_GetRightFront(void);
void Encoder_ResetAll(void);

#endif
