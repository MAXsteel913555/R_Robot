#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZhiDa - Smart Transport Assistant with Car Control
DeepSeek understands your intent -> publishes /cmd_vel to move the car
"""

import json
import time
import threading
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from openai import OpenAI

# ========== Configuration ==========
DEEPSEEK_API_KEY = "你的api"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

LINEAR_SPEED = 0.2   # m/s
ANGULAR_SPEED = 0.5  # rad/s

SYSTEM_PROMPT = """你叫智达，是一个智能货物运输小车助手。你可以控制小车移动。

当用户给出移动指令时，你必须在回答中包含一个JSON控制命令，格式如下：
```cmd
{"action": "动作", "duration": 秒数}
```

支持的动作：
- forward: 前进
- backward: 后退
- left: 左转
- right: 右转
- stop: 停止
- forward_left: 左前方前进
- forward_right: 右前方前进

示例：
用户：前进3秒
回答：好的，小车前进3秒！```cmd
{"action": "forward", "duration": 3}
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
1. 如果用户没指定时间，默认2秒
2. duration最大10秒，保证安全
3. 如果用户说的不是移动指令（比如聊天、提问），正常回答，不要输出cmd
4. 回答要简短友好
"""

ACTION_MAP = {
    "forward":       {"linear": LINEAR_SPEED,  "angular": 0.0},
    "backward":      {"linear": -LINEAR_SPEED, "angular": 0.0},
    "left":          {"linear": 0.0,           "angular": ANGULAR_SPEED},
    "right":         {"linear": 0.0,           "angular": -ANGULAR_SPEED},
    "forward_left":  {"linear": LINEAR_SPEED,  "angular": ANGULAR_SPEED * 0.5},
    "forward_right": {"linear": LINEAR_SPEED,  "angular": -ANGULAR_SPEED * 0.5},
    "stop":          {"linear": 0.0,           "angular": 0.0},
}


class ZhidaNode(Node):
    def __init__(self):
        super().__init__('zhida_control')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.get_logger().info('ZhiDa control node ready')

    def send_cmd(self, linear, angular):
        twist = Twist()
        twist.linear.x = float(linear)
        twist.angular.z = float(angular)
        self.pub.publish(twist)

    def execute_action(self, action, duration):
        if action not in ACTION_MAP:
            print(f"  Unknown action: {action}")
            return

        vel = ACTION_MAP[action]
        print(f"  Executing: {action} for {duration}s (linear={vel['linear']}, angular={vel['angular']})")

        self.send_cmd(vel['linear'], vel['angular'])

        if action != "stop" and duration > 0:
            time.sleep(duration)
            self.send_cmd(0.0, 0.0)
            print(f"  Done, stopped.")


def parse_command(reply):
    """Extract cmd JSON from reply text."""
    import re
    match = re.search(r'```cmd\s*\n?\s*(\{.*?\})\s*\n?\s*```', reply, re.DOTALL)
    if match:
        try:
            cmd = json.loads(match.group(1))
            return cmd
        except json.JSONDecodeError:
            pass
    return None


def clean_reply(reply):
    """Remove cmd block from display text."""
    import re
    return re.sub(r'```cmd\s*\n?\s*\{.*?\}\s*\n?\s*```', '', reply, flags=re.DOTALL).strip()


def main():
    rclpy.init()
    node = ZhidaNode()

    # Spin ROS2 in background
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("=" * 50)
    print("  ZhiDa - Smart Transport Control")
    print("  Text commands to control the car")
    print("  Examples: forward, left turn, stop, go back")
    print("  Type 'q' to quit")
    print("=" * 50)

    while True:
        try:
            user = input("\nYou: ")
        except (KeyboardInterrupt, EOFError):
            break
        if user.strip().lower() in ('q', 'quit', 'exit'):
            break
        if not user.strip():
            continue

        history.append({"role": "user", "content": user})

        try:
            r = client.chat.completions.create(
                model=DEEPSEEK_MODEL, messages=history,
                max_tokens=500, temperature=0.3)
            reply = r.choices[0].message.content.strip()
            history.append({"role": "assistant", "content": reply})

            if len(history) > 20:
                history = history[:1] + history[-10:]

            # Parse and execute command
            cmd = parse_command(reply)
            display = clean_reply(reply)
            print(f"\nZhiDa: {display}")

            if cmd:
                action = cmd.get("action", "stop")
                duration = min(cmd.get("duration", 2), 10)
                node.execute_action(action, duration)

        except Exception as e:
            print(f"\nError: {e}")

    # Stop car before exit
    node.send_cmd(0.0, 0.0)
    node.destroy_node()
    rclpy.shutdown()
    print("Bye!")


if __name__ == "__main__":
    main()
