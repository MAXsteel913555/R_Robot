#!/usr/bin/env python3
"""
bmi088_ros2_node.py - BMI088 via spidev (kernel CS, no GPIO conflict).
/dev/spidev1.0 = GYRO (CS0, BCM8, BOARD 24) → no dummy byte
/dev/spidev1.1 = ACC  (CS1, BCM7, BOARD 26) → 1 dummy byte
"""

import sys
import time
import math
import spidev
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

GRAVITY = 9.80665
DEG2RAD = math.pi / 180.0


class BMI088:
    def __init__(self, spi_speed=5000000):
        self.spi_acc = spidev.SpiDev()  # /dev/spidev1.1 — accel (open FIRST)
        self.spi_acc.open(1, 1)
        self.spi_acc.max_speed_hz = spi_speed
        self.spi_acc.mode = 0b11

        self.spi_gyr = spidev.SpiDev()  # /dev/spidev1.0 — gyro
        self.spi_gyr.open(1, 0)
        self.spi_gyr.max_speed_hz = spi_speed
        self.spi_gyr.mode = 0b11

        # Scales: ±6g → m/s², ±2000dps → rad/s
        self.ACC_SCALE = (6.0 * GRAVITY) / 32768.0
        self.GYR_SCALE = (2000.0 * DEG2RAD) / 32768.0

        # Zero-bias
        self.gb = [0.0, 0.0, 0.0]
        self.ab = [0.0, 0.0, 0.0]

    # ---- helpers ------------------------------------------------------
    def _gyr_write(self, reg, val):
        self.spi_gyr.xfer2([reg & 0x7F, val])

    def _acc_write(self, reg, val):
        self.spi_acc.xfer2([reg & 0x7F, val])

    def _gyr_read(self, reg, n):
        """Gyro SPI: NO dummy byte. resp[0]=status, resp[1:]=data."""
        resp = self.spi_gyr.xfer2([reg | 0x80] + [0] * n)
        return resp[1:1 + n]

    def _acc_read(self, reg, n):
        """Accel SPI: 1 dummy byte. resp[0]=status, resp[1]=dummy, resp[2:]=data."""
        resp = self.spi_acc.xfer2([reg | 0x80, 0x00] + [0] * n)
        return resp[2:2 + n]

    @staticmethod
    def _s16(data, off=0):
        val = ((data[off + 1] & 0xFF) << 8) | (data[off] & 0xFF)
        return val - 65536 if val > 32767 else val

    # ---- init ---------------------------------------------------------
    def init(self):
        # Chip IDs first (before any reset)
        aid = self._acc_read(0x00, 1)
        gid = self._gyr_read(0x00, 1)
        acc_ok = len(aid) and aid[0] == 0x1E
        gyr_ok = len(gid) and gid[0] == 0x0F
        if not acc_ok or not gyr_ok:
            print(f"[BMI088] CHIP ID: ACC=0x{aid[0]:02X} " f"(exp 0x1E)  GYR=0x{gid[0]:02X} (exp 0x0F)")
            return False

        # Soft reset
        self._acc_write(0x7E, 0xB6)
        self._gyr_write(0x14, 0xB6)
        time.sleep(0.15)

        # Accel config
        self._acc_write(0x7C, 0x00)   # power conf: disable suspend
        self._acc_write(0x7D, 0x04)   # power ctrl: enable acc
        time.sleep(0.03)
        self._acc_write(0x41, 0x01)   # range ±6g
        self._acc_write(0x40, 0xA8)   # ODR 800Hz, BW normal, OS4
        time.sleep(0.03)

        # Gyro config
        self._gyr_write(0x0F, 0x00)   # range ±2000dps
        self._gyr_write(0x10, 0x02)   # BW 116Hz (ODR 2kHz)
        time.sleep(0.03)

        return True

    def calibrate(self, n=300):
        print(f"[BMI088] Calibrating ({n} samples, keep IMU still)...")
        gsum = [0.0] * 3
        asum = [0.0] * 3
        for _ in range(n):
            ax, ay, az, gx, gy, gz = self.read_raw()
            asum[0] += ax; asum[1] += ay; asum[2] += az
            gsum[0] += gx; gsum[1] += gy; gsum[2] += gz
            time.sleep(0.005)
        self.gb = [v / n for v in gsum]
        self.ab = [v / n for v in asum]
        # Accel: remove gravity from Z
        self.ab[2] -= GRAVITY
        print(f"[BMI088] Gyro bias:  X={self.gb[0]:.5f} Y={self.gb[1]:.5f} Z={self.gb[2]:.5f} rad/s")
        print(f"[BMI088] Accel bias: X={self.ab[0]:.4f} Y={self.ab[1]:.4f} Z={self.ab[2]:.4f} m/s²")

    # ---- read ---------------------------------------------------------
    def read_raw(self):
        """Return (ax,ay,az,gx,gy,gz) raw, no bias correction."""
        ad = self._acc_read(0x12, 6)
        gd = self._gyr_read(0x02, 6)
        ax = self._s16(ad, 0) * self.ACC_SCALE
        ay = self._s16(ad, 2) * self.ACC_SCALE
        az = self._s16(ad, 4) * self.ACC_SCALE
        gx = self._s16(gd, 0) * self.GYR_SCALE
        gy = self._s16(gd, 2) * self.GYR_SCALE
        gz = self._s16(gd, 4) * self.GYR_SCALE
        return ax, ay, az, gx, gy, gz

    def read_accel(self):
        ax, ay, az, _, _, _ = self.read_raw()
        return ax - self.ab[0], ay - self.ab[1], az - self.ab[2]

    def read_gyro(self):
        _, _, _, gx, gy, gz = self.read_raw()
        return gx - self.gb[0], gy - self.gb[1], gz - self.gb[2]

    def close(self):
        self.spi_gyr.close()
        self.spi_acc.close()


class Bmi088DriverNode(Node):
    def __init__(self):
        super().__init__('bmi088_driver_node')
        self.declare_parameter('topic', '/imu_data')
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('calibrate', True)
        self.declare_parameter('calibrate_samples', 300)

        topic = self.get_parameter('topic').value
        self.frame_id = self.get_parameter('frame_id').value
        do_cal = self.get_parameter('calibrate').value
        cal_n = self.get_parameter('calibrate_samples').value

        self.pub = self.create_publisher(Imu, topic, 10)

        self.imu = BMI088()
        if not self.imu.init():
            self.get_logger().error("BMI088 init failed")
            sys.exit(1)

        if do_cal:
            self.get_logger().info("Starting zero-bias calibration (KEEP IMU STILL)...")
            self.imu.calibrate(cal_n)
            self.get_logger().info("Calibration done")

        self.get_logger().info(f"BMI088 publishing to {topic} at 100Hz")
        self.create_timer(0.01, self._cb)

    def _cb(self):
        try:
            ax, ay, az = self.imu.read_accel()
            gx, gy, gz = self.imu.read_gyro()
            m = Imu()
            m.header.stamp = self.get_clock().now().to_msg()
            m.header.frame_id = self.frame_id
            m.linear_acceleration.x = ax
            m.linear_acceleration.y = ay
            m.linear_acceleration.z = az
            m.angular_velocity.x = gx
            m.angular_velocity.y = gy
            m.angular_velocity.z = gz
            m.orientation_covariance[0] = -1.0
            self.pub.publish(m)
        except Exception as e:
            self.get_logger().error(f"Read error: {e}")

    def destroy_node(self):
        self.imu.close()
        super().destroy_node()


def main():
    rclpy.init()
    n = Bmi088DriverNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
