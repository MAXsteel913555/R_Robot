<img width="4096" height="2122" alt="RC" src="https://github.com/user-attachments/assets/2a4f94e8-66c6-44d8-8e5b-e40667d56776" />
<img width="2280" height="1520" alt="地瓜机器人" src="https://github.com/user-attachments/assets/d6363f96-f393-4437-af3e-f278f226aca5" />
<img width="572" height="937" alt="rdkx5海报" src="https://github.com/user-attachments/assets/b69552c8-a71d-4d98-855f-b63944f11f5a" />

这是参加第9届全国大学生嵌入式芯片与系统设计竞赛地瓜机器人赛道的参赛作品。

本作品针对复杂室内场景下物资转运的行业需求，设计并实现了一款基于RDK X5边缘AI平台的端云协同多模态物流机器人系统。

系统打通了边缘计算、多源传感器融合与云端大语言模型的全栈链路。实现了从语义理解到敏捷执行的具身智能控制闭环。系统采用分布式异构计算架构，以RDK X5作为核心算法母体，集成激光雷达、深度相机与IMU多源传感器，下位机则针对紧凑空间需求，自主设计了一款简易插拔式STM32F1控制板，此外还有一块简易的拓展板。上下位机通过ROS2通信框架实现高效协同。
<img width="2470" height="1210" alt="爆炸图结构" src="https://github.com/user-attachments/assets/ba3d4808-d1a8-43dc-94e7-e243370b7644" />

针对传统建图易飞图的痛点，系统引入扩展卡尔曼滤波算法，将全向航位推算与IMU数据深度融合，提供鲁棒的里程计基准，上层通过SLAM_Toolbox有效抑制建图重影，结合Navigation2框架实现全局最优路径规划与局部敏捷避障。
<img width="1640" height="1220" alt="image" src="https://github.com/user-attachments/assets/d79e929d-34ed-4241-8e20-888404fa052d" />

针对现场部署繁琐的痛点，团队自主开发了跨平台配套客户端，软件集成局域网IP动态扫描寻址，并创新支持NFC一键连接。实现“触碰即唤醒”的B/S端控制体验。打通了“开箱即用”的用户体验。
<img width="1642" height="1234" alt="image" src="https://github.com/user-attachments/assets/64e2126d-8098-4829-9571-5cd0522f304c" />

在远程控制端，系统构建多源视觉感知分时调阅系统，依托RDK X5的10TOPS BPU算力，支持高清原始画面、YOLOv5实时目标检测及深度空间热力图的一键敏捷切换。
<img width="1642" height="1234" alt="image" src="https://github.com/user-attachments/assets/ae20a912-bbd9-4fd1-a163-2d90e8313450" />

此外，系统还集成了DeepSeek云端大语言模型API，构建了多模态交互体系，机器人支持文字与语音的自然语言对话，实现了“复杂时序运动指令—大模型语义推理与动作解耦—底层精准驱动”的具身智能控制闭环。
<img width="3556" height="2000" alt="deepseek云端" src="https://github.com/user-attachments/assets/5a481831-0d89-47b6-9985-01981d9df140" />

本仓库存放了是下位机STM32F1的控制程序和ros2_ws的相关功能包，仅供参考。
