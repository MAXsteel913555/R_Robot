#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZhiDa - DeepSeek text chat
"""

from openai import OpenAI

DEEPSEEK_API_KEY = "你的api"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
history = [{"role": "system", "content": "你叫智达，是一个智能货物运输小车助手。你的职责是协助完成货物运输任务。请用简洁友好的中文回答问题。"}]

print("=" * 40)
print("  智达 - 智能货物运输助手")
print("  输入 q 退出")
print("=" * 40)

while True:
    try:
        user = input("\n你: ")
    except (KeyboardInterrupt, EOFError):
        break
    if user.strip().lower() in ('q', 'quit', 'exit'):
        break
    if not user.strip():
        continue

    history.append({"role": "user", "content": user})
    try:
        r = client.chat.completions.create(model=DEEPSEEK_MODEL, messages=history, max_tokens=1000)
        reply = r.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": reply})
        if len(history) > 20:
            history = history[:1] + history[-10:]
        print(f"\n智达: {reply}")
    except Exception as e:
        print(f"\n错误: {e}")
