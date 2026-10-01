#!/usr/bin/env python3
"""
Voice Assistant (Advanced Tier)
--------------------------------
Builds on the beginner assistant with:
  1. Looser intent parsing (regex-based, not exact keyword matching) so
     free-form sentences like "hey what's the time right now" still work.
  2. General knowledge answers via Wikipedia's free summary API (no key needed).
  3. Live weather via OpenWeatherMap (needs a free API key - see config.json).
  4. Timed reminders ("remind me in 5 minutes to check the oven").
  5. Custom commands loaded from config.json - add new phrase/response pairs
     without touching the code.
  6. All beginner features kept: greeting, time, date, web search, TTS,
     "please repeat" on unclear speech.

Usage:
    python voice_assistant_advanced.py           # voice mode
    python voice_assistant_advanced.py --text     # type commands (testing)

Setup:
    pip install -r requirements.txt
    (optional) put your free OpenWeatherMap key in config.json to enable weather
"""

import argparse
import datetime
import json
import os
import re
import threading
import time
import urllib.parse
import webbrowser

import pyttsx3
import requests

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


# ---------------------------------------------------------------------------
# Config (weather API key + custom commands) - editable without touching code
# ---------------------------------------------------------------------------
def load_config() -> dict:
    default = {
        "openweathermap_api_key": "",
        "custom_commands": {
            "who created you": "I was built by Sadhana as part of the Oasis Infobyte Python internship.",
            "thank you": "You're welcome!"
        }
    }
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
        return default
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        default.update(data)
        return default
    except (json.JSONDecodeError, OSError):
        return default


CONFIG = load_config()


# ---------------------------------------------------------------------------
# Text-to-speech
# ---------------------------------------------------------------------------
def init_engine():
    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
    return engine


def speak(engine, text: str):
    print(f"Assistant: {text}")
    engine.say(text)
    engine.runAndWait()


# ---------------------------------------------------------------------------
# Voice / text input
# ---------------------------------------------------------------------------
def listen_voice(recognizer, sr_module):
    with sr_module.Microphone() as source:
        print("\nListening... (speak now)")
        try:
            audio = recognizer.listen(source, timeout=6, phrase_time_limit=10)
        except sr_module.WaitTimeoutError:
            return None
    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text.lower()
    except sr_module.UnknownValueError:
        return None
    except sr_module.RequestError:
        return "REQUEST_ERROR"


def listen_text():
    text = input("\nYou (type command): ").strip().lower()
    return text if text else None


# ---------------------------------------------------------------------------
# Feature: Wikipedia general knowledge (no API key needed)
# ---------------------------------------------------------------------------
def answer_general_knowledge(topic: str) -> str:
    topic = topic.strip()
    if not topic:
        return "Who or what would you like to know about?"
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(topic)
        resp = requests.get(url, timeout=6, headers={"User-Agent": "voice-assistant/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            extract = data.get("extract", "")
            if extract:
                # keep the spoken answer short
                first_sentence = extract.split(". ")[0]
                return first_sentence if first_sentence.endswith(".") else first_sentence + "."
        return f"I could not find information about {topic}."
    except requests.RequestException:
        return "I could not reach the knowledge service. Please check your internet connection."


# ---------------------------------------------------------------------------
# Feature: Weather (OpenWeatherMap - needs a free API key in config.json)
# ---------------------------------------------------------------------------
def get_weather(city: str) -> str:
    city = city.strip()
    if not city:
        return "Which city's weather would you like?"
    api_key = CONFIG.get("openweathermap_api_key", "")
    if not api_key:
        return "Weather is not set up yet. Add a free OpenWeatherMap API key to config.json to enable it."
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": api_key, "units": "metric"}
        resp = requests.get(url, params=params, timeout=6)
        data = resp.json()
        if resp.status_code != 200:
            return f"I could not find weather for {city}. {data.get('message', '')}".strip()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        return f"It is currently {temp} degrees Celsius with {desc} in {city.title()}, humidity {humidity} percent."
    except requests.RequestException:
        return "I could not reach the weather service. Please check your internet connection."
    except (KeyError, IndexError):
        return f"I got an unexpected response looking up weather for {city}."


# ---------------------------------------------------------------------------
# Feature: Timed reminders (runs in a background thread, does not block input)
# ---------------------------------------------------------------------------
def schedule_reminder(engine, minutes: float, task: str):
    def alert():
        speak(engine, f"Reminder: {task}" if task else "Reminder: time is up!")

    threading.Timer(minutes * 60, alert).start()


# ---------------------------------------------------------------------------
# Intent parsing - regex-based "loose" matching instead of exact keywords,
# so word order and extra filler words don't break recognition.
# ---------------------------------------------------------------------------
PATTERNS = {
    "greeting": re.compile(r"\b(hello|hi|hey)\b"),
    "how_are_you": re.compile(r"how are you"),
    "your_name": re.compile(r"what('?s| is) your name"),
    "time": re.compile(r"\b(time)\b"),
    "date": re.compile(r"\b(date|today'?s date|what day)\b"),
    "search": re.compile(r"(?:search(?: for)?|google|look up)\s+(.+)"),
    "weather": re.compile(r"weather(?: in| for)?\s*(.*)"),
    "knowledge": re.compile(r"(?:who is|who was|what is|what are|tell me about)\s+(.+)"),
    "reminder": re.compile(r"remind me in\s+(\d+)\s*(?:minutes?|mins?)\s*(?:to\s+(.+))?"),
    "joke": re.compile(r"\bjoke\b"),
    "exit": re.compile(r"\b(exit|quit|stop|bye|goodbye)\b"),
}

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my computer I needed a break, and it said no problem, it will go to sleep too.",
    "Why did the developer go broke? Because they used up all their cache.",
]


def handle_command(command: str, engine, state: dict) -> bool:
    """Returns False when the assistant should exit."""
    command = command.strip()

    # Custom commands from config.json take priority (exact phrase match)
    for phrase, response in CONFIG.get("custom_commands", {}).items():
        if phrase in command:
            speak(engine, response)
            return True

    if PATTERNS["exit"].search(command):
        speak(engine, "Goodbye! Have a great day.")
        return False

    if PATTERNS["reminder"].search(command):
        m = PATTERNS["reminder"].search(command)
        minutes = float(m.group(1))
        task = (m.group(2) or "").strip()
        schedule_reminder(engine, minutes, task)
        speak(engine, f"Okay, I will remind you in {minutes:g} minutes" + (f" to {task}." if task else "."))
        return True

    if PATTERNS["weather"].search(command) and "weather" in command:
        m = PATTERNS["weather"].search(command)
        speak(engine, get_weather(m.group(1)))
        return True

    if PATTERNS["search"].search(command):
        m = PATTERNS["search"].search(command)
        query = m.group(1).strip()
        speak(engine, f"Searching the web for {query}.")
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(query))
        return True

    if PATTERNS["joke"].search(command):
        import random
        speak(engine, random.choice(JOKES))
        return True

    if PATTERNS["your_name"].search(command):
        speak(engine, "I'm your Python voice assistant, built for the Oasis Infobyte internship.")
        return True

    if PATTERNS["how_are_you"].search(command):
        speak(engine, "I'm doing great, thanks for asking! How can I help you?")
        return True

    if PATTERNS["time"].search(command):
        speak(engine, "The current time is " + datetime.datetime.now().strftime("%I:%M %p") + ".")
        return True

    if PATTERNS["date"].search(command):
        speak(engine, "Today is " + datetime.datetime.now().strftime("%A, %d %B %Y") + ".")
        return True

    if PATTERNS["greeting"].search(command):
        speak(engine, "Hello! I am your voice assistant. How can I help you today?")
        return True

    if PATTERNS["knowledge"].search(command):
        m = PATTERNS["knowledge"].search(command)
        speak(engine, answer_general_knowledge(m.group(1)))
        return True

    speak(engine, "Sorry, I didn't understand that. You can ask me the time, date, weather, "
                  "general knowledge questions, set a reminder, or search the web.")
    return True


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Advanced Voice Assistant")
    parser.add_argument("--text", action="store_true", help="Type commands instead of using the microphone")
    args = parser.parse_args()

    engine = init_engine()
    state = {}

    recognizer = None
    sr_module = None
    if not args.text:
        try:
            import speech_recognition as sr_module  # noqa: F811
            recognizer = sr_module.Recognizer()
        except ImportError:
            print("speech_recognition is not installed. Run: pip install SpeechRecognition")
            return
        try:
            with sr_module.Microphone() as source:
                print("Calibrating microphone... please stay quiet for 2 seconds.")
                recognizer.adjust_for_ambient_noise(source, duration=2)
        except OSError:
            print("Could not access the microphone. Please check your microphone and try again.")
            return

    speak(engine, "Advanced voice assistant started. Ask me the time, date, weather, general "
                  "knowledge questions, set a reminder, or search the web.")

    running = True
    while running:
        try:
            command = listen_text() if args.text else listen_voice(recognizer, sr_module)
        except OSError:
            speak(engine, "I could not access the microphone. Please check your microphone and try again.")
            break

        if command is None:
            speak(engine, "Sorry, I did not catch that. Could you please repeat?")
            continue
        if command == "REQUEST_ERROR":
            speak(engine, "I could not reach the speech service. Please check your internet connection.")
            continue

        running = handle_command(command, engine, state)


if __name__ == "__main__":
    main()
