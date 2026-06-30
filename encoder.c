#include "encoder.h"

void Encoder_Init(void)
{
    /* 启动TIM3编码器模式（左前轮） */
    HAL_TIM_Encoder_Start(&htim3, TIM_CHANNEL_ALL);

    /* 启动TIM4编码器模式（右前轮） */
    HAL_TIM_Encoder_Start(&htim4, TIM_CHANNEL_ALL);
}

/**
 * @brief 获取左前轮编码器计数值
 * @return 当前计数值（有符号，正转增加，反转减少）
 */
int32_t Encoder_GetLeftFront(void)
{
    // 实际读 TIM4（右前轮的线接在了这里）
    uint32_t cnt = __HAL_TIM_GET_COUNTER(&htim4);
    int32_t val;
    if (cnt > 32767)
        val = (int32_t)(cnt - 65536);
    else
        val = (int32_t)cnt;
    return val;
}

int32_t Encoder_GetRightFront(void)
{
    // 实际读 TIM3（左前轮的线接在了这里）
    uint32_t cnt = __HAL_TIM_GET_COUNTER(&htim3);
    int32_t val;
    if (cnt > 32767)
        val = (int32_t)(cnt - 65536);
    else
        val = (int32_t)cnt;
    return -val;
}

/**
 * @brief 重置所有编码器计数
 */
void Encoder_ResetAll(void)
{
    __HAL_TIM_SET_COUNTER(&htim3, 0);
    __HAL_TIM_SET_COUNTER(&htim4, 0);
}
