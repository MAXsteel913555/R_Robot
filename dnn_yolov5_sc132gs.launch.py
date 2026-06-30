# Copyright (c) 2024, D-Robotics.
# YOLOv5 detection with SC132GS camera (rotation 90°)
# Includes websocket node for web visualization on port 8000

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch_ros.actions import Node
from launch.substitutions import TextSubstitution, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python import get_package_share_directory
from ament_index_python.packages import get_package_prefix


def generate_launch_description():
    # Copy config files
    dnn_node_example_path = os.path.join(
        get_package_prefix('dnn_node_example'),
        "lib/dnn_node_example")
    cp_cmd = "cp -r " + dnn_node_example_path + "/config ."
    os.system(cp_cmd)

    config_file_launch_arg = DeclareLaunchArgument(
        "dnn_example_config_file",
        default_value=TextSubstitution(text="config/yolov5workconfig.json")
    )
    dump_render_launch_arg = DeclareLaunchArgument(
        "dnn_example_dump_render_img", default_value=TextSubstitution(text="0")
    )
    msg_pub_topic_name_launch_arg = DeclareLaunchArgument(
        "dnn_example_msg_pub_topic_name",
        default_value=TextSubstitution(text="hobot_dnn_detection")
    )

    # MIPI camera with rotation=90 for SC132GS
    mipi_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('mipi_cam'),
                'launch/mipi_cam.launch.py')),
        launch_arguments={
            'mipi_image_width': '960',
            'mipi_image_height': '544',
            'mipi_io_method': 'shared_mem',
            'mipi_frame_ts_type': 'realtime',
            'mipi_rotation': '90.0',
        }.items()
    )

    # JPEG encode
    jpeg_codec_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('hobot_codec'),
                'launch/hobot_codec_encode.launch.py')),
        launch_arguments={
            'codec_in_mode': 'shared_mem',
            'codec_out_mode': 'ros',
            'codec_sub_topic': '/hbmem_img',
            'codec_pub_topic': '/image_jpeg'
        }.items()
    )

    # Web display (port 8000) - renders detection boxes in browser
    web_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('websocket'),
                'launch/websocket.launch.py')),
        launch_arguments={
            'websocket_image_topic': '/image_jpeg',
            'websocket_image_type': 'mjpeg',
            'websocket_smart_topic': LaunchConfiguration("dnn_example_msg_pub_topic_name")
        }.items()
    )

    # DNN detection node
    dnn_node_example_node = Node(
        package='dnn_node_example',
        executable='example',
        output='screen',
        parameters=[
            {"config_file": LaunchConfiguration('dnn_example_config_file')},
            {"dump_render_img": LaunchConfiguration('dnn_example_dump_render_img')},
            {"feed_type": 1},
            {"is_shared_mem_sub": 1},
            {"msg_pub_topic_name": LaunchConfiguration("dnn_example_msg_pub_topic_name")}
        ],
        arguments=['--ros-args', '--log-level', 'warn']
    )

    # Shared memory
    shared_mem_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('hobot_shm'),
                'launch/hobot_shm.launch.py'))
    )

    return LaunchDescription([
        config_file_launch_arg,
        dump_render_launch_arg,
        msg_pub_topic_name_launch_arg,
        shared_mem_node,
        mipi_node,
        jpeg_codec_node,
        dnn_node_example_node,
        web_node,
    ])
