#include "motor.h"
#include <stdlib.h>

/* 全局电机对象数组 */
static MotorCtrl motors[4];

void Motor_Init(void)
{
    /* 左前轮 - PA6(IN1), PA7(IN2), TIM2 CH1 */
    motors[MOTOR_LEFT_FRONT].id = MOTOR_LEFT_FRONT;
    motors[MOTOR_LEFT_FRONT].in1_port = GPIOA;
    motors[MOTOR_LEFT_FRONT].in1_pin = GPIO_PIN_6;

    motors[MOTOR_LEFT_FRONT].in2_port = GPIOA;
    motors[MOTOR_LEFT_FRONT].in2_pin = GPIO_PIN_7;

    motors[MOTOR_LEFT_FRONT].tim = &htim2;
    motors[MOTOR_LEFT_FRONT].channel = TIM_CHANNEL_1;
    motors[MOTOR_LEFT_FRONT].speed = 0;

    /* 左后轮 - PB0(IN1), PB1(IN2), TIM2 CH2 */
    motors[MOTOR_LEFT_REAR].id = MOTOR_LEFT_REAR;
    motors[MOTOR_LEFT_REAR].in1_port = GPIOB;
    motors[MOTOR_LEFT_REAR].in1_pin = GPIO_PIN_0;

    motors[MOTOR_LEFT_REAR].in2_port = GPIOB;
    motors[MOTOR_LEFT_REAR].in2_pin = GPIO_PIN_1;

    motors[MOTOR_LEFT_REAR].tim = &htim2;
    motors[MOTOR_LEFT_REAR].channel = TIM_CHANNEL_2;
    motors[MOTOR_LEFT_REAR].speed = 0;

    /* 右前轮 - PA4(IN1), PA5(IN2), TIM1 CH1 */
    motors[MOTOR_RIGHT_FRONT].id = MOTOR_RIGHT_FRONT;
    motors[MOTOR_RIGHT_FRONT].in1_port = GPIOA;
    motors[MOTOR_RIGHT_FRONT].in1_pin = GPIO_PIN_4;

    motors[MOTOR_RIGHT_FRONT].in2_port = GPIOA;
    motors[MOTOR_RIGHT_FRONT].in2_pin = GPIO_PIN_5;

    motors[MOTOR_RIGHT_FRONT].tim = &htim1;
    motors[MOTOR_RIGHT_FRONT].channel = TIM_CHANNEL_2;
    motors[MOTOR_RIGHT_FRONT].speed = 0;

    /* 右后轮 - PA2(IN1), PA3(IN2), TIM2 CH2 */
    motors[MOTOR_RIGHT_REAR].id = MOTOR_RIGHT_REAR;
    motors[MOTOR_RIGHT_REAR].in1_port = GPIOA;
    motors[MOTOR_RIGHT_REAR].in1_pin = GPIO_PIN_2;
    motors[MOTOR_RIGHT_REAR].in2_port = GPIOA;
    motors[MOTOR_RIGHT_REAR].in2_pin = GPIO_PIN_3;
    motors[MOTOR_RIGHT_REAR].tim = &htim1;
    motors[MOTOR_RIGHT_REAR].channel = TIM_CHANNEL_1;
    motors[MOTOR_RIGHT_REAR].speed = 0;

    /* 启动PWM输出 */
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1);HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_2);HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);

    /* 初始化为停止状态 */
    Motor_StopAll();
}

/**
 * @brief 设置单个电机速度
 * @param id 电机编号
 * @param speed 速度值，范围 -1000~1000
 *        正数：前进（IN1=1, IN2=0）
 *        负数：后退（IN1=0, IN2=1）
 *        0：停止（IN1=0, IN2=0）
 */
void Motor_SetSpeed(MotorID id, int16_t speed)
{
    if (id > MOTOR_RIGHT_REAR) return;

    MotorCtrl* motor = &motors[id];

    // 限幅
    if (speed > 1000) speed = 1000;
    if (speed < -1000) speed = -1000;

    motor->speed = speed;

    if (speed > 0) {
        // 前进
        HAL_GPIO_WritePin(motor->in1_port, motor->in1_pin, GPIO_PIN_SET);
        HAL_GPIO_WritePin(motor->in2_port, motor->in2_pin, GPIO_PIN_RESET);
        __HAL_TIM_SET_COMPARE(motor->tim, motor->channel, speed);
    }
    else if (speed < 0) {
        // 后退
        HAL_GPIO_WritePin(motor->in1_port, motor->in1_pin, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(motor->in2_port, motor->in2_pin, GPIO_PIN_SET);
        __HAL_TIM_SET_COMPARE(motor->tim, motor->channel, -speed);
    }
    else {
        // 停止
        HAL_GPIO_WritePin(motor->in1_port, motor->in1_pin, GPIO_PIN_SET);
        HAL_GPIO_WritePin(motor->in2_port, motor->in2_pin, GPIO_PIN_SET);
        __HAL_TIM_SET_COMPARE(motor->tim, motor->channel, 0);
    }
}

void Motor_Stop(MotorID id)
{
    Motor_SetSpeed(id, 0);
}

void Motor_StopAll(void)
{
    for (int i = 0; i < 4; i++) {
        Motor_Stop((MotorID)i);
    }
}

/* ========== 小车整体控制 ========== */

void Car_Forward(int16_t speed)
{
    Motor_SetSpeed(MOTOR_LEFT_FRONT, speed);Motor_SetSpeed(MOTOR_RIGHT_FRONT, speed);
    Motor_SetSpeed(MOTOR_LEFT_REAR, -speed);Motor_SetSpeed(MOTOR_RIGHT_REAR, -speed);
}

void Car_Backward(int16_t speed)
{
    Motor_SetSpeed(MOTOR_LEFT_FRONT, -speed);Motor_SetSpeed(MOTOR_RIGHT_FRONT, -speed);
    Motor_SetSpeed(MOTOR_LEFT_REAR,   speed);Motor_SetSpeed(MOTOR_RIGHT_REAR,   speed);
}

void Car_TurnLeft(int16_t speed)
{
    // 左转：左侧轮反转，右侧轮正转（原地差速转向）
    Motor_SetSpeed(MOTOR_LEFT_FRONT, -speed);Motor_SetSpeed(MOTOR_RIGHT_FRONT, speed);
    Motor_SetSpeed(MOTOR_LEFT_REAR,   speed);Motor_SetSpeed(MOTOR_RIGHT_REAR,  -speed);
}

void Car_TurnRight(int16_t speed)
{
    // 右转：左侧轮正转，右侧轮反转
    Motor_SetSpeed(MOTOR_LEFT_FRONT, speed);Motor_SetSpeed(MOTOR_RIGHT_FRONT,-speed);
    Motor_SetSpeed(MOTOR_LEFT_REAR, -speed);Motor_SetSpeed(MOTOR_RIGHT_REAR,  speed);
}

void Car_Stop(void)
{
    Motor_StopAll();
}

/**
 * @brief 差速控制（接收RDK X5发来的线速度和角速度）
 * @param linear 线速度，范围 -1000~1000
 * @param angular 角速度，范围 -1000~1000
 *
 * 简化差速模型：
 *   left_speed  = linear - angular
 *   right_speed = linear + angular
 */
void Car_Differential(int16_t linear, int16_t angular)
{
    int16_t left_speed = linear - angular;
    int16_t right_speed = linear + angular;

    // 限幅
    if (left_speed > 1000) left_speed = 1000;
    if (left_speed < -1000) left_speed = -1000;
    if (right_speed > 1000) right_speed = 1000;
    if (right_speed < -1000) right_speed = -1000;

    Motor_SetSpeed(MOTOR_LEFT_FRONT, left_speed);Motor_SetSpeed(MOTOR_RIGHT_FRONT, right_speed);
    Motor_SetSpeed(MOTOR_LEFT_REAR, -left_speed);Motor_SetSpeed(MOTOR_RIGHT_REAR, -right_speed);


}
