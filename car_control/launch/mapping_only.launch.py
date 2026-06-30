#!/usr/bin/env python3
"""
Laser SLAM mapping only.
Prerequisites: chassis_node and teleop_twist_keyboard started separately.
Usage:
  ros2 launch car_control mapping_only.launch.py
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    lidar_port = LaunchConfiguration("lidar_port")

    car_pkg = get_package_share_directory("car_control")
    lidar_launch = os.path.join(
        get_package_share_directory("rplidar_ros"), "launch", "rplidar_a1_launch.py")
    slam_params = os.path.join(car_pkg, "config", "slam_toolbox_mapping.yaml")

    return LaunchDescription([
        DeclareLaunchArgument("lidar_port", default_value="/dev/ttyUSB0"),

        # RPLidar A1
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(lidar_launch),
            launch_arguments={
                "serial_port": lidar_port,
                "frame_id": "laser",
            }.items(),
        ),

        # Static TF: base_link -> laser (20cm above)
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="base_to_laser",
            arguments=["0", "0", "0.2", "0", "0", "0", "base_link", "laser"],
            output="screen",
        ),

        # SLAM Toolbox (async mapping)
        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            parameters=[slam_params],
            output="screen",
        ),
    ])
