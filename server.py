#!/usr/bin/env python3
"""
Web Controller for ROS2 Car
- HTTP serves the control page
- WebSocket receives movement commands → publishes Twist to /cmd_vel
- REST /api/chat calls DeepSeek for text chat + motion control
"""

import os
import json
import time
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import CompressedImage

import subprocess

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.gen

from openai import OpenAI


# ─── Config ──────────────────────────────────────────────────────────────────

DEEPSEEK_API_KEY = "你的api"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

LINEAR_SPEED = 0.2   # m/s
ANGULAR_SPEED = 0.5  # rad/s (cmd_vel angular value)
ACTUAL_ANGULAR_SPEED = 2.94  # rad/s (measured actual rotation speed)
ACTUAL_LINEAR_SPEED = 0.235  # m/s (measured: 70cm in 3s at 0.2 cmd_vel)

SYSTEM_PROMPT = """你叫智达，是一个智能货物运输小车助手。你可以控制小车移动。

当用户给出移动指令时，你必须在回答中包含一个JSON控制命令，格式如下：
```cmd
{JSON对象}
```

支持的动作：
- forward: 前进
- backward: 后退
- left: 左转（原地左转）
- right: 右转（原地右转）
- stop: 停止
- forward_left: 左前方前进
- forward_right: 右前方前进

JSON命令格式（根据情况选一种）：

1. 用户指定时间（如"前进3秒"）：
   {"action": "动作", "duration": 秒数}

2. 用户指定距离（如"前进60cm"、"前进1米"）：
   {"action": "动作", "distance_m": 距离米数}
   注意：距离单位统一转换为米，如 60cm = 0.6，1米 = 1.0

3. 用户指定角度（如"左转90度"、"右转180度"）：
   {"action": "动作", "angle_deg": 角度数}
   注意：角度单位为度，如 90度 = 90

4. 用户没指定时间/距离/角度（如"前进"、"左转"）：
   {"action": "动作", "duration": 2}

示例：
用户：前进3秒
回答：好的，前进3秒！```cmd
{"action": "forward", "duration": 3}
```

用户：前进1米
回答：好的，前进1米！```cmd
{"action": "forward", "distance_m": 1.0}
```

用户：前进60cm
回答：好的，前进60厘米！```cmd
{"action": "forward", "distance_m": 0.6}
```

用户：左转90度
回答：好的，左转90度！```cmd
{"action": "left", "angle_deg": 90}
```

用户：右转180度
回答：好的，右转180度！```cmd
{"action": "right", "angle_deg": 180}
```

用户：左转
回答：好的，左转中！```cmd
{"action": "left", "duration": 2}
```

用户：停
回答：已停车！```cmd
{"action": "stop", "duration": 0}
```

规则：
1. 用户指定距离时，用 distance_m 字段，不要自己算 duration
2. 用户指定角度时，用 angle_deg 字段，不要自己算 duration
3. 用户指定时间时，用 duration 字段
4. 用户没指定任何量时，默认 duration=2
5. duration最大30秒
6. 如果用户说的不是移动指令，正常回答，不要输出cmd
7. 回答要简短友好
8. 收到移动指令立即生成cmd块，不要追问"""

ACTION_MAP = {
    "forward":       {"linear": LINEAR_SPEED,  "angular": 0.0},
    "backward":      {"linear": -LINEAR_SPEED, "angular": 0.0},
    "left":          {"linear": 0.0,           "angular": ANGULAR_SPEED},
    "right":         {"linear": 0.0,           "angular": -ANGULAR_SPEED},
    "forward_left":  {"linear": LINEAR_SPEED,  "angular": ANGULAR_SPEED * 0.5},
    "forward_right": {"linear": LINEAR_SPEED,  "angular": -ANGULAR_SPEED * 0.5},
    "stop":          {"linear": 0.0,           "angular": 0.0},
}


# ─── ROS2 Node ───────────────────────────────────────────────────────────────

class WebControllerNode(Node):
    def __init__(self):
        super().__init__('web_controller')
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self._stop_event = threading.Event()
        self._motion_thread = None

        # Camera image subscriber
        self._latest_frame = None
        self._frame_lock = threading.Lock()
        self.create_subscription(
            CompressedImage, '/image_jpeg', self._image_callback, 1
        )

        self.get_logger().info('WebControllerNode started, publishing to /cmd_vel')

    def _image_callback(self, msg):
        with self._frame_lock:
            self._latest_frame = bytes(msg.data)

    def get_latest_frame(self):
        with self._frame_lock:
            return self._latest_frame

    def publish_twist(self, linear_x, linear_y, angular_z):
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.linear.y = float(linear_y)
        msg.angular.z = float(angular_z)
        self.publisher.publish(msg)

    def execute_action(self, action, duration):
        """Execute a motion action (same logic as zhida_control.py)."""
        if action not in ACTION_MAP:
            self.get_logger().warn(f'Unknown action: {action}')
            return

        # Stop any previous timed motion
        self._stop_event.set()
        if self._motion_thread and self._motion_thread.is_alive():
            self._motion_thread.join(timeout=1)
        self._stop_event.clear()

        vel = ACTION_MAP[action]
        self.get_logger().info(
            f'Executing: {action} for {duration}s (linear={vel["linear"]}, angular={vel["angular"]})'
        )
        self.publish_twist(vel['linear'], 0.0, vel['angular'])

        if action != 'stop' and duration > 0:
            self._motion_thread = threading.Thread(
                target=self._timed_stop, args=(vel['linear'], vel['angular'], duration), daemon=True
            )
            self._motion_thread.start()

    def _timed_stop(self, linear, angular, duration):
        """Keep publishing velocity for duration, then stop."""
        start = time.time()
        while time.time() - start < duration:
            if self._stop_event.is_set():
                return
            self.publish_twist(linear, 0.0, angular)
            time.sleep(0.1)
        self.publish_twist(0.0, 0.0, 0.0)
        self.get_logger().info(f'Timed motion complete ({duration:.1f}s)')


# ─── Global state ────────────────────────────────────────────────────────────

ros_node = None
chat_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

# Camera process management
camera_process = None
camera_lock = threading.Lock()
camera_mode = 'stereo'  # 'stereo' or 'yolov5' or 'raw'


def kill_camera_processes():
    """Kill all camera-related processes to free resources."""
    import signal
    # Kill known camera-related processes
    kill_patterns = [
        'mipi_cam', 'hobot_codec', 'hobot_stereonet', 'stereonet_model',
        'dnn_node_example', 'websocket/websocket', 'run_stereo.sh',
        'sc132gs_raw', 'dnn_yolov5_sc132gs'
    ]
    for pattern in kill_patterns:
        os.system(f"pkill -9 -f '{pattern}' 2>/dev/null")
    # Also kill nginx from websocket package
    os.system("pkill -9 -f 'nginx.*websocket' 2>/dev/null")
    time.sleep(3)  # Wait for camera hardware resources to release

CAMERA_COMMANDS = {
    'stereo': ['bash', '/home/sunrise/run_stereo.sh'],
    'yolov5': ['bash', '-c', 'sudo systemctl stop lightdm; source /opt/tros/humble/setup.bash && source /home/sunrise/ros2_ws/install/setup.bash && ros2 launch stereo_camera dnn_yolov5_sc132gs.launch.py'],
    'raw': ['bash', '-c', 'source /opt/tros/humble/setup.bash && source /home/sunrise/ros2_ws/install/setup.bash && ros2 launch stereo_camera sc132gs_raw.launch.py'],
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_command(text):
    """Extract cmd JSON from ```cmd ... ``` block in reply (same as zhida_control.py)."""
    import re
    match = re.search(r'```cmd\s*\n?\s*(\{.*?\})\s*\n?\s*```', text, re.DOTALL)
    if match:
        try:
            cmd = json.loads(match.group(1))
            # If AI provided distance_m, calculate duration server-side
            if 'distance_m' in cmd:
                dist = float(cmd['distance_m'])
                cmd['duration'] = round(dist / ACTUAL_LINEAR_SPEED, 2)
            # If AI provided angle_deg, calculate duration server-side
            if 'angle_deg' in cmd:
                import math
                angle_rad = float(cmd['angle_deg']) * math.pi / 180.0
                cmd['duration'] = round(angle_rad / ACTUAL_ANGULAR_SPEED, 2)
            return cmd
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def clean_reply(text):
    """Remove cmd block from display text."""
    import re
    cleaned = re.sub(r'```cmd\s*\n?\s*\{.*?\}\s*\n?\s*```', '', text, flags=re.DOTALL).strip()
    return cleaned if cleaned else "已执行"


# ─── Tornado Handlers ────────────────────────────────────────────────────────

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        html_path = os.path.join(os.path.dirname(__file__), 'static', 'index.html')
        with open(html_path, 'r') as f:
            self.write(f.read())


class ControlWebSocket(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if ros_node:
            ros_node.get_logger().info('WebSocket client connected')

    def on_message(self, message):
        try:
            data = json.loads(message)
            cmd = data.get('cmd', '')
            linear_speed = data.get('linear_speed', 0.1)
            angular_speed = data.get('angular_speed', 0.1)

            move_bindings = {
                'forward':        (1,  0,  0),
                'forward_left':   (1,  0,  1),
                'forward_right':  (1,  0, -1),
                'left':           (0,  0,  1),
                'stop':           (0,  0,  0),
                'right':          (0,  0, -1),
                'backward':       (-1, 0,  0),
                'backward_left':  (-1, 0, -1),
                'backward_right': (-1, 0,  1),
            }

            if cmd in move_bindings:
                lx, ly, az = move_bindings[cmd]
                if ros_node:
                    ros_node.publish_twist(
                        lx * linear_speed,
                        0.0,
                        az * angular_speed
                    )
        except Exception as e:
            if ros_node:
                ros_node.get_logger().error(f'WebSocket error: {e}')

    def on_close(self):
        if ros_node:
            ros_node.get_logger().info('WebSocket client disconnected')
            ros_node.publish_twist(0.0, 0.0, 0.0)


class ChatHandler(tornado.web.RequestHandler):
    """REST endpoint for DeepSeek chat + motion control."""

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    async def post(self):
        global chat_history

        try:
            body = json.loads(self.request.body)
            user_msg = body.get('message', '').strip()
            if not user_msg:
                self.write(json.dumps({'reply': '请输入消息'}))
                return

            chat_history.append({"role": "user", "content": user_msg})

            # Call DeepSeek
            response = await tornado.ioloop.IOLoop.current().run_in_executor(
                None, self._call_deepseek
            )

            raw_reply = response.choices[0].message.content.strip()
            chat_history.append({"role": "assistant", "content": raw_reply})

            # Keep history manageable
            if len(chat_history) > 21:
                chat_history = chat_history[:1] + chat_history[-10:]

            # Parse and execute command (same as zhida_control.py)
            cmd = parse_command(raw_reply)
            action_info = None
            if cmd and ros_node:
                action = cmd.get('action', 'stop')
                duration = min(float(cmd.get('duration', 2)), 30)
                ros_node.execute_action(action, duration)
                vel = ACTION_MAP.get(action, {'linear': 0, 'angular': 0})
                action_info = {
                    'action': action,
                    'linear': vel['linear'],
                    'angular': vel['angular'],
                    'duration': duration
                }

            # Clean reply for display
            display_reply = clean_reply(raw_reply)

            result = {'reply': display_reply}
            if action_info:
                result['action'] = action_info

            self.write(json.dumps(result, ensure_ascii=False))

        except Exception as e:
            if ros_node:
                ros_node.get_logger().error(f'Chat error: {e}')
            self.set_status(500)
            self.write(json.dumps({'reply': f'服务错误: {e}'}, ensure_ascii=False))

    def _call_deepseek(self):
        return chat_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=chat_history,
            max_tokens=1000
        )


class CameraControlHandler(tornado.web.RequestHandler):
    """REST endpoint to start/stop camera with mode selection."""

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    async def get(self):
        """Get camera status."""
        global camera_process, camera_mode
        with camera_lock:
            running = camera_process is not None and camera_process.poll() is None
        self.write(json.dumps({'running': running, 'mode': camera_mode}))

    async def post(self):
        """Start or stop camera."""
        global camera_process, camera_mode
        try:
            body = json.loads(self.request.body)
            action = body.get('action', '')
            mode = body.get('mode', camera_mode)

            if action == 'start':
                with camera_lock:
                    # Stop existing process and clean up all camera processes
                    if camera_process and camera_process.poll() is None:
                        import signal
                        try:
                            os.killpg(os.getpgid(camera_process.pid), signal.SIGTERM)
                            camera_process.wait(timeout=3)
                        except:
                            pass
                        camera_process = None
                    kill_camera_processes()

                    camera_mode = mode
                    cmd = CAMERA_COMMANDS.get(mode, CAMERA_COMMANDS['stereo'])
                    camera_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid
                    )
                if ros_node:
                    ros_node.get_logger().info(f'Camera started in mode: {mode}')
                self.write(json.dumps({'ok': True, 'status': 'started', 'mode': mode}))

            elif action == 'stop':
                with camera_lock:
                    if camera_process and camera_process.poll() is None:
                        import signal
                        try:
                            os.killpg(os.getpgid(camera_process.pid), signal.SIGTERM)
                            camera_process.wait(timeout=3)
                        except:
                            pass
                        camera_process = None
                    kill_camera_processes()
                if ros_node:
                    ros_node.get_logger().info('Camera stopped')
                self.write(json.dumps({'ok': True, 'status': 'stopped'}))

            else:
                self.write(json.dumps({'ok': False, 'error': 'invalid action'}))

        except Exception as e:
            if ros_node:
                ros_node.get_logger().error(f'Camera control error: {e}')
            self.set_status(500)
            self.write(json.dumps({'ok': False, 'error': str(e)}))


class MjpegStreamHandler(tornado.web.RequestHandler):
    """MJPEG stream endpoint - serves camera frames as multipart JPEG."""

    async def get(self):
        self.set_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Connection', 'keep-alive')

        while True:
            if ros_node:
                frame = ros_node.get_latest_frame()
                if frame:
                    self.write(b'--frame\r\n')
                    self.write(b'Content-Type: image/jpeg\r\n\r\n')
                    self.write(frame)
                    self.write(b'\r\n')
                    try:
                        await self.flush()
                    except tornado.iostream.StreamClosedError:
                        return
            await tornado.gen.sleep(0.066)  # ~15fps


class StaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header('Cache-Control', 'no-cache')


# ─── App ─────────────────────────────────────────────────────────────────────

def make_app():
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/ws', ControlWebSocket),
        (r'/api/chat', ChatHandler),
        (r'/api/camera', CameraControlHandler),
        (r'/api/stream', MjpegStreamHandler),
        (r'/static/(.*)', StaticFileHandler, {'path': static_path}),
    ])


def ros_spin_thread():
    rclpy.spin(ros_node)


def main():
    global ros_node

    rclpy.init()
    ros_node = WebControllerNode()

    spin_thread = threading.Thread(target=ros_spin_thread, daemon=True)
    spin_thread.start()

    app = make_app()
    port = 8888
    app.listen(port)
    ros_node.get_logger().info(f'Web controller running at http://0.0.0.0:{port}')
    print(f'\n╔══════════════════════════════════════════════╗')
    print(f'║  Web Controller: http://<RDK_IP>:{port}     ║')
    print(f'║  Press Ctrl+C to stop                       ║')
    print(f'╚══════════════════════════════════════════════╝\n')

    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        pass
    finally:
        ros_node.publish_twist(0.0, 0.0, 0.0)
        ros_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
