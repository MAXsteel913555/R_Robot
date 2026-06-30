#ifndef __MOTOR_H
#define __MOTOR_H

#include "main.h"
#include "tim.h"

/* 电机编号定义 */
typedef enum {
    MOTOR_LEFT_FRONT = 0,   // 左前轮
    MOTOR_LEFT_REAR,        // 左后轮
    MOTOR_RIGHT_FRONT,      // 右前轮
    MOTOR_RIGHT_REAR        // 右后轮
} MotorID;

/* 电机方向定义 */
typedef enum {
    MOTOR_STOP = 0,
    MOTOR_FORWARD,
    MOTOR_BACKWARD
} MotorDir;

/* 电机控制结构体 */
typedef struct {
    MotorID id;
    GPIO_TypeDef* in1_port;
    uint16_t in1_pin;
    GPIO_TypeDef* in2_port;
    uint16_t in2_pin;
    TIM_HandleTypeDef* tim;
    uint32_t channel;
    int16_t speed;          // -1000 ~ 1000，正为前进，负为后退
} MotorCtrl;

/* 函数声明 */
void Motor_Init(void);
void Motor_SetSpeed(MotorID id, int16_t speed);
void Motor_Stop(MotorID id);
void Motor_StopAll(void);

/* 小车整体控制 */
void Car_Forward(int16_t speed);
void Car_Backward(int16_t speed);
void Car_TurnLeft(int16_t speed);
void Car_TurnRight(int16_t speed);
void Car_Stop(void);
void Car_Differential(int16_t linear, int16_t angular);

#endif
