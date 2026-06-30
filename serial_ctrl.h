#ifndef __SERIAL_CTRL_H
#define __SERIAL_CTRL_H

#include "main.h"
#include "usart.h"

/* 串口接收缓冲区大小 */
#define RX_BUF_SIZE 64

/* 命令解析函数 */
void SerialCtrl_Init(void);
void SerialCtrl_ProcessByte(uint8_t byte);

#endif
