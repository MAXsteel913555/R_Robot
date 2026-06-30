#!/usr/bin/env python3
"""
stm32car.py - STM32 文本协议通信接口

STM32 命令格式（以 \\n 结尾）：
  F:500   前进
  B:500   后退
  L:500   左转
  R:500   右转
  S       停止
  D:300,100  差速(线速度,角速度)
  E       查询编码器

STM32 返回格式：
  ENC L:123 R:456\\r\\n
"""

import serial
import threading
import time


class STM32Interface:
    """STM32串口通信接口 - 文本协议，线程安全"""

    def __init__(self, port='/dev/ttyS1', baudrate=115200):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.05
        )
        time.sleep(0.5)

        self._write_lock = threading.Lock()

        # 里程计数据（线程安全）
        self._odom_lock = threading.Lock()
        self._left_enc = 0
        self._right_enc = 0
        self._odom_updated = False

        self._running = True

        # 接收线程
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()

        print(f'[STM32Interface] Connected to {port}')

    def _send(self, cmd: str):
        """发送一条文本命令"""
        with self._write_lock:
            if self.ser.is_open:
                self.ser.write((cmd + '\n').encode('ascii'))

    def send_velocity(self, left_speed, right_speed):
        """发送差速指令（转成 D:linear,angular 格式）"""
        left_speed = max(-1000, min(1000, int(left_speed)))
        right_speed = max(-1000, min(1000, int(right_speed)))
        linear = (left_speed + right_speed) // 2
        angular = (right_speed - left_speed) // 2
        self._send(f'D:{linear},{angular}')

    def query_encoder(self):
        """发送编码器查询命令"""
        self._send('E')

    def stop(self):
        """发送停止命令"""
        self._send('S')

    def get_odom(self):
        """获取最新里程计数据"""
        with self._odom_lock:
            return (
                self._left_enc,
                self._right_enc,
                0,
                0,
                self._odom_updated
            )

    def clear_odom_flag(self):
        """清除更新标志"""
        with self._odom_lock:
            self._odom_updated = False

    def _rx_loop(self):
        """接收线程 - 持续读取串口并解析文本行"""
        line_buf = ''
        while self._running:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting).decode('ascii', errors='ignore')
                    line_buf += data
                    while '\n' in line_buf:
                        line, line_buf = line_buf.split('\n', 1)
                        line = line.strip()
                        if line:
                            self._process_line(line)
                else:
                    time.sleep(0.005)
            except Exception as e:
                if self._running:
                    print(f'[STM32Interface] RX error: {e}')
                break

    def _process_line(self, line: str):
        """处理一行返回数据"""
        if line.startswith('ENC'):
            try:
                parts = line.split()
                if len(parts) >= 3:
                    left = int(parts[1].split(':')[1])
                    right = int(parts[2].split(':')[1])
                    with self._odom_lock:
                        self._left_enc = left
                        self._right_enc = right
                        self._odom_updated = True
            except (ValueError, IndexError):
                pass

    def close(self):
        """关闭连接"""
        self._running = False
        time.sleep(0.2)
        self.stop()
        time.sleep(0.1)
        if self.ser.is_open:
            self.ser.close()
        print('[STM32Interface] Closed')


class STM32Car(STM32Interface):
    """兼容层 - 供 chassis_node 直接调用"""

    def __init__(self, port='/dev/ttyS1', baudrate=115200):
        super().__init__(port=port, baudrate=baudrate)

    def get_encoder(self):
        """返回 chassis_node 期望的字符串格式，或 None"""
        self.query_encoder()
        time.sleep(0.02)
        left, right, _, _, updated = self.get_odom()
        if not updated:
            return None
        self.clear_odom_flag()
        return f"ENC L:{left} R:{right}"

    def differential(self, linear, angular):
        """
        linear: mm/s, angular: milli-rad/s
        直接转发给 STM32 的 D:linear,angular 命令
        """
        self._send(f'D:{int(linear)},{int(angular)}')
