# SC132GS dual camera raw image output to /image_jpeg
# For web_controller MJPEG stream integration (no websocket/8000 port needed)

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python import get_package_share_directory


def generate_launch_description():

    # MIPI dual camera (SC132GS with calibration + rotation 90)
    mipi_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('mipi_cam'),
                'launch/mipi_cam_dual_channel.launch.py')),
        launch_arguments={
            'mipi_image_width': '1280',
            'mipi_image_height': '1088',
            'mipi_image_framerate': '10.0',
            'mipi_frame_ts_type': 'realtime',
            'mipi_rotation': '90.0',
            'mipi_cal_rotation': '0.0',
            'mipi_gdc_enable': 'True',
            'mipi_lpwm_enable': 'True',
            'mipi_stream_mode': '1',
            'device_mode': 'dual',
            'dual_combine': '2',
            'mipi_channel': '2',
            'mipi_channel2': '0',
            'mipi_io_method': 'ros',
        }.items()
    )

    # Encode to JPEG, publish to /image_jpeg for web_controller
    jpeg_codec_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('hobot_codec'),
                'launch/hobot_codec_encode.launch.py')),
        launch_arguments={
            'codec_in_mode': 'ros',
            'codec_out_mode': 'ros',
            'codec_in_format': 'nv12',
            'codec_sub_topic': '/image_combine_raw',
            'codec_pub_topic': '/image_jpeg',
            'codec_jpg_quality': '85.0',
        }.items()
    )

    # Shared memory
    shared_mem_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('hobot_shm'),
                'launch/hobot_shm.launch.py'))
    )

    return LaunchDescription([
        shared_mem_node,
        mipi_node,
        jpeg_codec_node,
    ])
