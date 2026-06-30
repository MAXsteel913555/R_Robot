#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
import math
from .stm32car import STM32Car


class ChassisNode(Node):
    def __init__(self):
        super().__init__('chassis_node')

        self.declare_parameter('port', '/dev/ttyS1')
        self.declare_parameter('baudrate', 115200)
        port = self.get_parameter('port').value
        baudrate = self.get_parameter('baudrate').value
        self.stm32 = STM32Car(port=port, baudrate=baudrate)

        self.cmd_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_callback, 10
        )
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        self.encoder_resolution = 1000
        self.wheel_diameter = 0.07
        self.wheel_base = 0.19
        self.pulse_per_meter = self.encoder_resolution / (math.pi * self.wheel_diameter)

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_left = 0
        self.last_right = 0
        self.first_reading = True

        self.timer = self.create_timer(0.05, self.timer_callback)
        self.get_logger().info('ChassisNode Ready')

    def cmd_callback(self, msg):
        linear = msg.linear.x * 1000
        angular = msg.angular.z * 1000
        self.stm32.differential(int(linear), int(angular))

    def timer_callback(self):
        reply = self.stm32.get_encoder()
        if reply is None:
            return
        if not reply.startswith("ENC"):
            return

        try:
            parts = reply.split()
            if len(parts) < 3:
                return
            left_str = parts[1].split(':')[1]
            right_str = parts[2].split(':')[1]
            left_count = int(left_str)
            right_count = int(right_str)
        except Exception:
            return

        if self.first_reading:
            self.last_left = left_count
            self.last_right = right_count
            self.first_reading = False
            return

        delta_left = left_count - self.last_left
        delta_right = right_count - self.last_right
        self.last_left = left_count
        self.last_right = right_count

        d_left = delta_left / self.pulse_per_meter
        d_right = delta_right / self.pulse_per_meter

        d = (d_left + d_right) / 2.0
        d_theta = (d_right - d_left) / self.wheel_base

        self.x += d * math.cos(self.theta + d_theta / 2.0)
        self.y += d * math.sin(self.theta + d_theta / 2.0)
        self.theta += d_theta

        now = self.get_clock().now().to_msg()

        t = TransformStamped()
        t.header.stamp = now
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation.z = math.sin(self.theta / 2.0)
        t.transform.rotation.w = math.cos(self.theta / 2.0)
        self.tf_broadcaster.sendTransform(t)

        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = math.sin(self.theta / 2.0)
        odom.pose.pose.orientation.w = math.cos(self.theta / 2.0)
        dt = 0.05
        odom.twist.twist.linear.x = d / dt
        odom.twist.twist.angular.z = d_theta / dt
        self.odom_pub.publish(odom)

    def destroy_node(self):
        self.stm32.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ChassisNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
