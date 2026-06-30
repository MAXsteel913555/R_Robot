#!/usr/bin/env python3
"""
自主导航 Launch
启动：底盘节点 + 雷达节点 + TF + nav2 导航栈
rviz2 和键盘 GUI 可通过 use_rviz / use_keyboard 参数打开
"""

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
    use_keyboard = LaunchConfiguration("use_keyboard")

    pkg_dir = get_package_share_directory("car_control")

    chassis_node = Node(
        package="car_control",
        executable="chassis_node",
        name="chassis_node",
        parameters=[{"port": chassis_port}, {"baudrate": chassis_baud}],
        output="screen",
    )

    lidar_launch = os.path.join(
        get_package_share_directory("rplidar_ros"), "launch", "rplidar_a1_launch.py"
    )
    rplidar_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(lidar_launch),
        launch_arguments={"serial_port": lidar_port, "frame_id": "laser"}.items(),
    )

    base_to_laser = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="base_to_laser",
        arguments=["0", "0", "0.1", "0", "0", "0", "base_link", "laser"],
        output="screen",
    )

    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("nav2_bringup"), "launch", "bringup_launch.py")
        ),
        launch_arguments={
            "map": "/home/sunrise/ros2_ws/src/car_control/maps/map.yaml",
            "params_file": os.path.join(pkg_dir, "config", "nav2_params.yaml"),
            "use_sim_time": "False",
            "autostart": "True",
            "use_composition": "False",
            "use_respawn": "False",
        }.items(),
    )

    rviz_node = Node(
        condition=IfCondition(use_rviz),
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", os.path.join(pkg_dir, "config", "nav_mapping.rviz")],
        output="screen",
        additional_env={"DISPLAY": ":0"},
    )

    keyboard_gui = Node(
        condition=IfCondition(use_keyboard),
        package="car_control",
        executable="keyboard_gui",
        name="keyboard_gui",
        output="screen",
        additional_env={"DISPLAY": ":0"},
    )

    return LaunchDescription([
        DeclareLaunchArgument("chassis_port", default_value="/dev/ttyS1"),
        DeclareLaunchArgument("chassis_baud", default_value="115200"),
        DeclareLaunchArgument("lidar_port", default_value="/dev/ttyUSB0"),
        DeclareLaunchArgument("use_rviz", default_value="False"),
        DeclareLaunchArgument("use_keyboard", default_value="False"),
        chassis_node,
        rplidar_node,
        base_to_laser,
        nav2_bringup,
        rviz_node,
        keyboard_gui,
    ])
