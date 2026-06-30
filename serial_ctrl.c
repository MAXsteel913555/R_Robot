#include "serial_ctrl.h"
#include "motor.h"
#include "encoder.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

static uint8_t rx_buf[RX_BUF_SIZE];
static uint8_t rx_index = 0;

void SerialCtrl_Init(void)
{
    memset(rx_buf, 0, RX_BUF_SIZE);
    rx_index = 0;

    /* 开启串口3中断接收 */
    HAL_UART_Receive_IT(&huart3, &rx_buf[rx_index], 1);
}

/**
 * @brief 处理接收到的单个字节
 * @param byte 接收到的字节
 *
 * 命令格式（以 \n 结尾）：
 *   F:500          前进，速度500
 *   B:500          后退，速度500
 *   L:500          左转，速度500
 *   R:500          右转，速度500
 *   S              停止
 *   D:300,100      差速控制（线速度300，角速度100）
 *   E              查询编码器
 */
void SerialCtrl_ProcessByte(uint8_t byte)
{
    if (byte == '\n') {
        // 收到完整一帧，解析
        rx_buf[rx_index] = '\0';
        char *cmd = (char*)rx_buf;

        if (cmd[0] == 'F' && cmd[1] == ':') {
            // 前进 F:500
            int speed = atoi(&cmd[2]);
            if (speed < 0) speed = 0;
            Car_Forward((int16_t)speed);
            printf("OK FWD %d\r\n", speed);
        }
        else if (cmd[0] == 'B' && cmd[1] == ':') {
            // 后退 B:500
            int speed = atoi(&cmd[2]);
            if (speed < 0) speed = 0;
            Car_Backward((int16_t)speed);
            printf("OK BWD %d\r\n", speed);
        }
        else if (cmd[0] == 'L' && cmd[1] == ':') {
            // 左转 L:500
            int speed = atoi(&cmd[2]);
            if (speed < 0) speed = 0;
            Car_TurnLeft((int16_t)speed);
            printf("OK LEFT %d\r\n", speed);
        }
        else if (cmd[0] == 'R' && cmd[1] == ':') {
            // 右转 R:500
            int speed = atoi(&cmd[2]);
            if (speed < 0) speed = 0;
            Car_TurnRight((int16_t)speed);
            printf("OK RIGHT %d\r\n", speed);
        }
        else if (cmd[0] == 'S') {
            // 停止
            Car_Stop();
            printf("OK STOP\r\n");
        }
        else if (cmd[0] == 'D' && cmd[1] == ':') {
            // 差速控制 D:linear,angular
            char *comma = strchr(&cmd[2], ',');
            if (comma != NULL) {
                *comma = '\0';
                int linear = atoi(&cmd[2]);
                int angular = atoi(comma + 1);
                Car_Differential((int16_t)linear, (int16_t)angular);
                printf("OK DIFF L:%d A:%d\r\n", linear, angular);
            }
        }
        else if (cmd[0] == 'E') {
            // 查询编码器
            int32_t left = Encoder_GetLeftFront();
            int32_t right = Encoder_GetRightFront();
            printf("ENC L:%ld R:%ld\r\n", left, right);
        }
        else {
            printf("ERR UNKNOWN CMD\r\n");
        }

        // 清空缓冲区，准备接收下一条
        memset(rx_buf, 0, RX_BUF_SIZE);
        rx_index = 0;
    }
    else {
        // 未收到换行，继续接收
        rx_index++;
        if (rx_index >= RX_BUF_SIZE) {
            rx_index = 0;  // 防止溢出，丢弃
        }
    }

    // 继续接收下一个字节
    HAL_UART_Receive_IT(&huart3, &rx_buf[rx_index], 1);
}

/**
 * @brief 串口中断回调（在stm32f1xx_it.c中调用或直接在HAL回调中处理）
 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART3) {
        SerialCtrl_ProcessByte(rx_buf[rx_index]);
    }
}
