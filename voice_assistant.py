#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDK X5 voice assistant - ZhiDa
ASR: Vosk | LLM: DeepSeek | TTS: Edge TTS
"""

import os
import sys
import json
import time
import subprocess
import asyncio
import numpy as np
from vosk import Model, KaldiRecognizer
from openai import OpenAI
import edge_tts
import sounddevice as sd

# ========== Configuration ==========
DEEPSEEK_API_KEY = "你的api"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

VOSK_MODEL_PATH = "/home/sunrise/ros2_ws/src/voice_assistant/model"
TTS_VOICE = "zh-CN-XiaoxiaoNeural"

SAMPLE_RATE = 16000
CHANNELS = 1

SYSTEM_PROMPT = "你叫智达，是一个智能货物运输小车助手。你的职责是协助完成货物运输任务。请用简短口语化的中文回答问题。"


# ========== ASR ==========
class ASR:
    def __init__(self, model_path):
        print("[ASR] Loading model...")
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        print("[ASR] Ready")

    def record_and_recognize(self):
        print("\n Press Enter to start recording...")
        input()
        print(" Recording... (Press Enter to stop)")
        audio_data = []
        recording = True

        def callback(indata, frames, time_info, status):
            if recording:
                audio_data.append(indata.copy())

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS,
            dtype='int16', blocksize=4000, callback=callback)
        stream.start()
        input()
        recording = False
        stream.stop()
        stream.close()

        if not audio_data:
            return ""

        audio = np.concatenate(audio_data, axis=0)
        print(" Recognizing...")
        self.recognizer.AcceptWaveform(audio.tobytes())
        result = json.loads(self.recognizer.FinalResult())
        text = result.get("text", "").strip()

        if text:
            print(f" You: {text}")
        else:
            print(" No speech detected")

        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        return text


# ========== LLM ==========
class LLM:
    def __init__(self):
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        print("[LLM] DeepSeek Ready")

    def chat(self, user_text):
        self.history.append({"role": "user", "content": user_text})
        print(" Thinking...")
        try:
            response = self.client.chat.completions.create(
                model=DEEPSEEK_MODEL, messages=self.history,
                max_tokens=500, temperature=0.7)
            reply = response.choices[0].message.content.strip()
            self.history.append({"role": "assistant", "content": reply})
            if len(self.history) > 20:
                self.history = self.history[:1] + self.history[-10:]
            print(f" ZhiDa: {reply}")
            return reply
        except Exception as e:
            print(f" API Error: {e}")
            return "Sorry, please try again later."


# ========== TTS ==========
class TTS:
    def __init__(self, voice=TTS_VOICE):
        self.voice = voice
        print(f"[TTS] Edge TTS Ready ({voice})")

    def speak(self, text):
        if not text:
            return
        print(" Synthesizing...")
        tmp_file = "/tmp/tts_output.mp3"
        asyncio.run(self._generate(text, tmp_file))
        print(" Playing...")
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_file],
            capture_output=True)
        try:
            os.remove(tmp_file)
        except:
            pass

    async def _generate(self, text, output_file):
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_file)


# ========== Main ==========
def main():
    print("=" * 50)
    print("  ZhiDa - Smart Transport Assistant")
    print("  ASR: Vosk | LLM: DeepSeek | TTS: Edge TTS")
    print("=" * 50)

    asr = ASR(VOSK_MODEL_PATH)
    llm = LLM()
    tts = TTS()

    print("\n Ready!")
    print("   Press Enter -> Speak -> Press Enter -> Wait")
    print("   Say 'quit' or type 'q' to exit\n")

    while True:
        try:
            text = asr.record_and_recognize()
            if not text:
                continue
            if text in ('quit', 'exit'):
                tts.speak("Goodbye!")
                break
            reply = llm.chat(text)
            tts.speak(reply)
        except KeyboardInterrupt:
            print("\nBye!")
            break
        except Exception as e:
            print(f" Error: {e}")
            continue


if __name__ == "__main__":
    main()
