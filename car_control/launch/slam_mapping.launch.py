#!/usr/bin/env python3
"""RDK X5 + RPLidar A1M8 + chassis_node one-click laser mapping."""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    chassis_port = LaunchConfiguration("chassis_port")
    chassis_baud = LaunchConfiguration("chassis_baud")
    lidar_port = LaunchConfiguration("lidar_port")
    use_rviz = LaunchConfiguration("use_rviz")

    car_pkg = get_package_share_directory("car_control")
    lidar_launch = os.path.join(get_package_share_directory("rplidar_ros"), "launch", "rplidar_a1_launch.py")
    slam_params = os.path.join(car_pkg, "config", "slam_toolbox_mapping.yaml")
    rviz_config = os.path.join(car_pkg, "config", "slam_mapping.rviz")

    return LaunchDescription([
        DeclareLaunchArgument("chassis_port", default_value="/dev/ttyS1"),
        DeclareLaunchArgument("chassis_baud", default_value="115200"),
        DeclareLaunchArgument("lidar_port", default_value="/dev/ttyUSB0"),
        DeclareLaunchArgument("use_rviz", default_value="false"),

        # Chassis control
        Node(
            package="car_control",
            executable="chassis_node",
            name="chassis_node",
            parameters=[{"port": chassis_port, "baudrate": chassis_baud}],
            output="screen",
        ),

        # RPLidar A1
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(lidar_launch),
            launch_arguments={
                "serial_port": lidar_port,
                "frame_id": "laser",
            }.items(),
        ),

        # Static TF: base_link -> laser
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="base_to_laser",
            arguments=["0", "0", "0.2", "0", "0", "0", "base_link", "laser"],
            output="screen",
        ),

        # SLAM Toolbox
        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            parameters=[slam_params],
            output="screen",
        ),

        # RViz2 (optional)
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            arguments=["-d", rviz_config],
            output="screen",
            additional_env={"DISPLAY": ":0"},
            condition=IfCondition(use_rviz),
        ),
    ])
