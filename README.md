# R_Robot
This is a submission for the 9th National College Student Embedded Chip and System Design Competition, under the D-Robotics track.

This project addresses the industry demand for material transport in complex indoor environments by designing and implementing a cloud-edge collaborative multimodal logistics robot system based on the RDK X5 edge AI platform.

The system establishes a full-stack pipeline that integrates edge computing, multi-source sensor fusion, and cloud-based large language models, achieving an embodied intelligent control loop from semantic understanding to agile execution. The system adopts a distributed heterogeneous computing architecture, with the RDK X5 serving as the core algorithm hub, integrating LiDAR, a depth camera, and an IMU as multi-source sensors. For the lower-level controller, a custom-designed, plug-and-play STM32F1 control board was developed to meet compact space requirements, along with a simplified expansion board. Efficient collaboration between the upper and lower controllers is achieved through the ROS2 communication framework.

To address the common issue of mapping drift in traditional SLAM systems, an Extended Kalman Filter algorithm is introduced, deeply fusing omnidirectional dead reckoning with IMU data to provide a robust odometry reference. At the upper layer, SLAM_Toolbox effectively suppresses mapping ghosting, while the Navigation2 framework enables global optimal path planning and local agile obstacle avoidance.

To tackle the pain point of cumbersome on-site deployment, the team independently developed a cross-platform companion client. The software integrates dynamic IP scanning for LAN addressing and innovatively supports one-tap NFC connection, enabling a "tap-to-wake" B/S-based control experience and delivering a true "out-of-the-box" user experience.

For the remote control terminal, a multi-source visual perception time-sharing access system is built. Leveraging the 10 TOPS BPU computing power of the RDK X5, it supports one-tap agile switching between high-definition raw video, YOLOv5 real-time object detection, and depth spatial heatmaps.

Furthermore, the system integrates the DeepSeek cloud-based large language model API to construct a multimodal interaction framework. The robot supports natural language dialogue via both text and voice, realizing an embodied intelligent control loop that spans "complex temporal motion commands — LLM semantic reasoning and action decomposition — precise low-level actuation."

This repository contains the STM32F1 lower-level control programs and the relevant functional packages for ros2_ws, provided for reference only.
