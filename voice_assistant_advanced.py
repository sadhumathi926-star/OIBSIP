#!/usr/bin/env python3
"""
Voice Assistant (Advanced Tier) - Expanded Version

Features:
- Voice mode and --text testing mode
- Greetings and casual conversation
- Time and date
- Weather using OpenWeatherMap
- General knowledge using Wikipedia
- Built-in answers for common questions
- Natural-language maths
- Reminders in seconds or minutes
- Web search
- Jokes
- Flexible matching for common spelling mistakes
- Custom commands from config.json
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
import random

import pyttsx3
import requests


CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config.json"
)


# ============================================================
# CONFIG
# ============================================================

def load_config() -> dict:
    default = {
        "openweathermap_api_key": "",
        "custom_commands": {
            "who created you": (
                "I was built by Sadhana as part of the Oasis Infobyte "
                "Python internship."
            ),
            "thank you": "You're welcome!",
            "thanks": "You're welcome!"
        }
    }

    if not os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)
        except OSError:
            pass
        return default

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            if "openweathermap_api_key" in data:
                default["openweathermap_api_key"] = data[
                    "openweathermap_api_key"
                ]

            if isinstance(data.get("custom_commands"), dict):
                default["custom_commands"].update(
                    data["custom_commands"]
                )

        return default

    except (json.JSONDecodeError, OSError):
        return default


CONFIG = load_config()


# ============================================================
# TEXT TO SPEECH
# ============================================================

def init_engine():
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 170)
        return engine
    except Exception:
        return None


def speak(engine, text: str):
    print(f"Assistant: {text}")

    if engine is not None:
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass


# ============================================================
# INPUT
# ============================================================

def listen_voice(recognizer, sr_module):
    with sr_module.Microphone() as source:
        print("\nListening... (speak now)")

        try:
            audio = recognizer.listen(
                source,
                timeout=6,
                phrase_time_limit=10
            )
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
    try:
        text = input("\nYou (type command): ").strip().lower()
        return text if text else None
    except (EOFError, KeyboardInterrupt):
        return "bye"


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:
    text = text.lower().strip()

    # Common voice/text typos.
    replacements = {
        "afetr": "after",
        "befor": "before",
        "mins": "minutes",
        "min": "minute",
        "sec": "seconds",
        "secs": "seconds",
        "rminder": "reminder",
        "reminde": "remind",
        "remaind": "remind",
        "tata": "tata",
        "nagai": "nagai",
        "naga": "nagai",
        "gud": "good",
        "wht": "what",
        "whos": "who is",
        "whats": "what is",
        "thnks": "thanks",
        "tnx": "thanks"
    }

    for old, new in replacements.items():
        text = re.sub(r"\b" + re.escape(old) + r"\b", new, text)

    text = re.sub(r"\s+", " ", text)
    return text


def clean_topic(topic: str) -> str:
    topic = topic.strip()
    topic = re.sub(r"[?.!,]+$", "", topic).strip()
    return topic


# ============================================================
# COMMON BUILT-IN KNOWLEDGE
# ============================================================

BUILT_IN_ANSWERS = {
    "father of drama":
        "Thespis is traditionally known as the father of drama and is considered one of the earliest known actors in ancient Greek theatre.",

    "father of computers":
        "Charles Babbage is widely known as the father of computers because of his design for the Analytical Engine.",

    "father of the computer":
        "Charles Babbage is widely known as the father of computers because of his design for the Analytical Engine.",

    "father of computer":
        "Charles Babbage is widely known as the father of computers because of his design for the Analytical Engine.",

    "inventor of telephone":
        "Alexander Graham Bell is commonly credited with inventing the telephone.",

    "who invented telephone":
        "Alexander Graham Bell is commonly credited with inventing the telephone.",

    "what is artificial intelligence":
        "Artificial intelligence is the field of creating computer systems that can perform tasks that normally require human intelligence.",

    "what is ai":
        "AI stands for artificial intelligence. It enables computer systems to perform tasks that normally require human intelligence.",

    "what is machine learning":
        "Machine learning is a branch of artificial intelligence in which computers learn patterns from data and use them to make predictions or decisions.",

    "what is python":
        "Python is a high-level, general-purpose programming language known for its simple syntax and wide use in web development, data science, automation, and artificial intelligence.",

    "what is internet":
        "The Internet is a global network of interconnected computer networks that communicate using standard protocols.",

    "what is the internet":
        "The Internet is a global network of interconnected computer networks that communicate using standard protocols.",

    "what is a black hole":
        "A black hole is a region of space where gravity is so strong that nothing, including light, can escape from it.",

    "what is black hole":
        "A black hole is a region of space where gravity is so strong that nothing, including light, can escape from it.",

    "what is photosynthesis":
        "Photosynthesis is the process by which green plants use sunlight, water, and carbon dioxide to produce food and release oxygen.",

    "capital of india":
        "The capital of India is New Delhi.",

    "largest ocean":
        "The Pacific Ocean is the largest ocean on Earth.",

    "highest mountain":
        "Mount Everest is the highest mountain above sea level.",

    "what is gravity":
        "Gravity is the force of attraction between objects that have mass.",

    "what is earth":
        "Earth is the third planet from the Sun and the only astronomical object currently known to support life.",

    "what is the earth":
        "Earth is the third planet from the Sun and the only astronomical object currently known to support life.",

    "what is solar system":
        "The Solar System consists of the Sun and the objects that orbit it, including planets, moons, asteroids, and comets.",

    "what is an operating system":
        "An operating system is system software that manages computer hardware and provides services for applications.",

    "what is operating system":
        "An operating system is system software that manages computer hardware and provides services for applications.",

    "what is flask":
        "Flask is a lightweight Python web framework commonly used to build web applications and APIs.",

    "what is api":
        "API stands for Application Programming Interface. It allows different software systems to communicate with each other.",

    "what is database":
        "A database is an organized collection of data that can be stored, managed, and retrieved electronically.",

    "what is cloud computing":
        "Cloud computing is the delivery of computing resources such as servers, storage, and software over the Internet.",

    "what is blockchain":
        "Blockchain is a distributed digital ledger technology that records transactions in linked blocks.",

    "what is cybersecurity":
        "Cybersecurity is the practice of protecting computers, networks, applications, and data from unauthorized access and attacks."
}


def get_builtin_answer(command: str):
    command = clean_topic(command)

    # Exact built-in match.
    if command in BUILT_IN_ANSWERS:
        return BUILT_IN_ANSWERS[command]

    # Natural variations.
    compact = re.sub(r"[^a-z0-9 ]", "", command)
    compact = re.sub(r"\s+", " ", compact).strip()

    if compact in BUILT_IN_ANSWERS:
        return BUILT_IN_ANSWERS[compact]

    # Specific questions with different wording.
    if (
        "father of drama" in command
        or "who is the father of drama" in command
        or "who was the father of drama" in command
    ):
        return BUILT_IN_ANSWERS["father of drama"]

    if (
        "father of computer" in command
        or "father of computers" in command
    ):
        return BUILT_IN_ANSWERS["father of computers"]

    if (
        "who invented the telephone" in command
        or "who invented telephone" in command
    ):
        return BUILT_IN_ANSWERS["inventor of telephone"]

    if "capital of india" in command:
        return BUILT_IN_ANSWERS["capital of india"]

    if "largest ocean" in command:
        return BUILT_IN_ANSWERS["largest ocean"]

    if "highest mountain" in command:
        return BUILT_IN_ANSWERS["highest mountain"]

    return None


# ============================================================
# GENERAL KNOWLEDGE - WIKIPEDIA
# ============================================================

def answer_general_knowledge(topic: str) -> str:
    topic = clean_topic(topic)

    if not topic:
        return "Who or what would you like to know about?"

    builtin = get_builtin_answer(topic)
    if builtin:
        return builtin

    try:
        url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(topic)
        )

        response = requests.get(
            url,
            timeout=6,
            headers={"User-Agent": "voice-assistant/2.0"}
        )

        if response.status_code == 200:
            data = response.json()
            extract = data.get("extract", "")

            if extract:
                sentences = re.split(r"(?<=[.!?])\s+", extract)

                if sentences:
                    answer = sentences[0].strip()

                    if not answer.endswith((".", "!", "?")):
                        answer += "."

                    return answer

        return f"I could not find information about {topic}."

    except requests.RequestException:
        return (
            "I could not reach the knowledge service. "
            "Please check your internet connection."
        )


# ============================================================
# WEATHER
# ============================================================

def get_weather(city: str) -> str:
    city = city.strip()

    if not city:
        return "Which city's weather would you like?"

    api_key = CONFIG.get("openweathermap_api_key", "")

    if not api_key:
        return (
            "Weather is not set up yet. Add a free OpenWeatherMap "
            "API key to config.json to enable it."
        )

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"

        params = {
            "q": city,
            "appid": api_key,
            "units": "metric"
        }

        response = requests.get(
            url,
            params=params,
            timeout=6
        )

        try:
            data = response.json()
        except ValueError:
            return "I received an invalid response from the weather service."

        if response.status_code != 200:
            message = data.get("message", "")
            return f"I could not find weather for {city}. {message}".strip()

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]

        return (
            f"It is currently {temp} degrees Celsius with {desc} "
            f"in {city.title()}, humidity {humidity} percent."
        )

    except requests.RequestException:
        return (
            "I could not reach the weather service. "
            "Please check your internet connection."
        )

    except (KeyError, IndexError, TypeError):
        return f"I got an unexpected response looking up weather for {city}."


# ============================================================
# MATH
# ============================================================

WORD_OPERATORS = {
    "plus": "+",
    "add": "+",
    "added to": "+",
    "minus": "-",
    "subtract": "-",
    "subtracted from": "-",
    "times": "*",
    "multiplied by": "*",
    "multiply": "*",
    "divided by": "/",
    "divide by": "/",
    "over": "/",
    "x": "*"
}

SAFE_EXPR = re.compile(r"^[\d\s\.\+\-\*/\(\)%]+$")


def solve_math(expression: str) -> str:
    original = expression.strip()
    expr = clean_topic(expression).lower()

    # Percentage phrase.
    percent_match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*(?:percent|%)\s+of\s+(\d+(?:\.\d+)?)",
        expr
    )

    if percent_match:
        percentage = float(percent_match.group(1))
        number = float(percent_match.group(2))
        result = (percentage / 100) * number

        if result.is_integer():
            result = int(result)

        return f"{original} is {result}."

    for word in sorted(WORD_OPERATORS, key=len, reverse=True):
        expr = expr.replace(word, WORD_OPERATORS[word])

    expr = expr.strip()

    if not expr or not SAFE_EXPR.match(expr):
        return (
            "I didn't catch a valid maths expression. "
            "Try something like, what is 5 plus 3."
        )

    try:
        result = eval(
            expr,
            {"__builtins__": {}},
            {}
        )

        if isinstance(result, float) and result.is_integer():
            result = int(result)

        return f"{original} is {result}."

    except ZeroDivisionError:
        return "I can't divide by zero."

    except Exception:
        return (
            "I didn't catch a valid maths expression. "
            "Try something like, what is 5 plus 3."
        )


# ============================================================
# REMINDERS
# ============================================================

def schedule_reminder(engine, seconds: float, task: str):
    def alert():
        message = (
            f"Reminder: {task}"
            if task
            else "Reminder: time is up!"
        )
        speak(engine, message)

    timer = threading.Timer(seconds, alert)
    timer.daemon = True
    timer.start()


def parse_reminder(command: str):
    """
    Supports:
    remind me after 5 seconds
    remind me in 5 seconds
    remind me after 1 minute
    remind me in 2 minutes to drink water
    set a reminder for the next 1 minute
    set a reminder for 30 seconds to study
    """

    text = normalize_text(command)

    # Pattern 1:
    # remind me after/in 5 seconds/minutes to ...
    pattern1 = re.search(
        r"\bremind\s+me\s+(?:after|in)\s+"
        r"(\d+(?:\.\d+)?)\s*"
        r"(seconds?|minutes?|hours?)"
        r"(?:\s+(?:to|for)\s+(.+))?$",
        text
    )

    if pattern1:
        amount = float(pattern1.group(1))
        unit = pattern1.group(2)
        task = (pattern1.group(3) or "").strip()

        return amount, unit, task

    # Pattern 2:
    # set a reminder for the next 1 minute
    pattern2 = re.search(
        r"\bset\s+(?:a\s+)?reminder\s+"
        r"(?:for\s+)?(?:the\s+)?next\s+"
        r"(\d+(?:\.\d+)?)\s*"
        r"(seconds?|minutes?|hours?)"
        r"(?:\s+(?:to|for)\s+(.+))?$",
        text
    )

    if pattern2:
        amount = float(pattern2.group(1))
        unit = pattern2.group(2)
        task = (pattern2.group(3) or "").strip()

        return amount, unit, task

    # Pattern 3:
    # set a reminder in 5 minutes
    pattern3 = re.search(
        r"\bset\s+(?:a\s+)?reminder\s+"
        r"(?:after|in)\s+"
        r"(\d+(?:\.\d+)?)\s*"
        r"(seconds?|minutes?|hours?)"
        r"(?:\s+(?:to|for)\s+(.+))?$",
        text
    )

    if pattern3:
        amount = float(pattern3.group(1))
        unit = pattern3.group(2)
        task = (pattern3.group(3) or "").strip()

        return amount, unit, task

    return None


def reminder_to_seconds(amount: float, unit: str):
    unit = unit.lower()

    if unit.startswith("second"):
        return amount

    if unit.startswith("minute"):
        return amount * 60

    if unit.startswith("hour"):
        return amount * 60 * 60

    return None


# ============================================================
# JOKES
# ============================================================

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my computer I needed a break, and it said no problem, it will go to sleep too.",
    "Why did the developer go broke? Because they used up all their cache.",
    "Why was the computer cold? Because it left its Windows open.",
    "Why do Python programmers wear glasses? Because they cannot C.",
    "What do computers eat for a snack? Microchips."
]


# ============================================================
# INTENT HELPERS
# ============================================================

def is_greeting(command):
    patterns = [
        r"\bhi\b",
        r"\bhello\b",
        r"\bhey\b",
        r"\bhiya\b",
        r"\bhey there\b",
        r"\bgood morning\b",
        r"\bgood afternoon\b",
        r"\bgood evening\b"
    ]

    return any(re.search(pattern, command) for pattern in patterns)


def is_goodbye(command):
    return bool(
        re.search(
            r"\b(bye|goodbye|good bye|tata|see you|see ya|"
            r"exit|quit|stop|close)\b",
            command
        )
    )


def is_thanks(command):
    return bool(
        re.search(
            r"\b(thank you|thanks|thankyou|many thanks)\b",
            command
        )
    )


def is_how_are_you(command):
    return bool(
        re.search(
            r"\bhow\s+(?:are|r)\s+you\b",
            command
        )
    )


def is_nice_to_meet(command):
    return bool(
        re.search(
            r"\bnice\s+to\s+meet\s+you\b",
            command
        )
    )


def is_welcome_response(command):
    return bool(
        re.search(
            r"\b(you are welcome|you're welcome|welcome)\b",
            command
        )
    )


def is_identity_question(command):
    return bool(
        re.search(
            r"\b(who are you|what are you|what is your name|"
            r"what's your name|tell me your name)\b",
            command
        )
    )


def is_capability_question(command):
    return bool(
        re.search(
            r"\bwhat can you do\b|\bwhat do you do\b|"
            r"\bhow can you help me\b",
            command
        )
    )


def is_time_question(command):
    return bool(
        re.search(
            r"\b(what(?:'s| is)? the time|"
            r"tell me the time|"
            r"current time|"
            r"time right now|"
            r"what time is it|"
            r"what time is it now)\b",
            command
        )
    )


def is_date_question(command):
    return bool(
        re.search(
            r"\b(what(?:'s| is)? today's date|"
            r"what is the date|"
            r"today's date|"
            r"current date|"
            r"what day is today|"
            r"what day is it|"
            r"tell me today's date)\b",
            command
        )
    )


def extract_weather_city(command):
    text = command.strip()

    patterns = [
        r"(?:weather|temperature)\s+(?:in|at|for|of|about)\s+(.+)",
        r"(?:what(?:'s| is)\s+)?(?:the\s+)?weather\s+(?:in|at|for|about)\s+(.+)",
        r"(?:tell me|give me|show me)\s+(?:today's\s+)?weather\s+(?:in|at|for|about)\s+(.+)",
        r"(?:how hot|how cold)\s+is\s+(?:it\s+)?(?:in|at)\s+(.+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            city = clean_topic(match.group(1))
            return city

    if re.search(r"\bweather\b", text):
        return ""

    return None


def extract_search_query(command):
    patterns = [
        r"\bsearch\s+(?:for\s+)?(.+)",
        r"\bgoogle\s+(.+)",
        r"\blook\s+up\s+(.+)",
        r"\bsearch\s+the\s+web\s+(?:for\s+)?(.+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return clean_topic(match.group(1))

    return None


def extract_knowledge_topic(command):
    patterns = [
        r"^(?:who\s+is|who\s+was)\s+(.+)$",
        r"^(?:what\s+is|what\s+are|what\s+was|what\s+were)\s+(.+)$",
        r"^(?:tell\s+me\s+about|tell\s+about)\s+(.+)$",
        r"^(?:explain)\s+(.+)$",
        r"^(?:define)\s+(.+)$",
        r"^(?:give\s+me\s+information\s+about)\s+(.+)$",
        r"^(?:can\s+you\s+tell\s+me\s+about)\s+(.+)$"
    ]

    for pattern in patterns:
        match = re.search(pattern, command)

        if match:
            return clean_topic(match.group(1))

    # Common direct questions.
    direct_topics = [
        "father of drama",
        "father of computers",
        "father of computer",
        "largest ocean",
        "highest mountain",
        "capital of india"
    ]

    for topic in direct_topics:
        if topic in command:
            return topic

    return None


def extract_math_expression(command):
    # Must contain a number and a maths operation.
    if not re.search(r"\d", command):
        return None

    math_words = (
        "plus", "minus", "times", "multiplied",
        "divided", "divide", "over", "calculate",
        "solve", "add", "subtract", "percent"
    )

    has_operator = (
        any(word in command for word in math_words)
        or bool(re.search(r"\d\s*[\+\-\*/xX%]\s*\d", command))
    )

    if not has_operator:
        return None

    expression = command

    expression = re.sub(
        r"^(what(?:'s| is)?|calculate|solve)\s+",
        "",
        expression
    )

    expression = re.sub(
        r"^(can you\s+)?(please\s+)?calculate\s+",
        "",
        expression
    )

    return expression.strip()


# ============================================================
# COMMAND HANDLER
# ============================================================

def handle_command(command: str, engine, state: dict) -> bool:
    command = normalize_text(command)

    if not command:
        speak(engine, "Please say or type a command.")
        return True

    # --------------------------------------------------------
    # Custom commands
    # --------------------------------------------------------
    custom_commands = CONFIG.get("custom_commands", {})

    if isinstance(custom_commands, dict):
        for phrase, response in custom_commands.items():
            phrase_normalized = normalize_text(str(phrase))

            if phrase_normalized in command:
                speak(engine, str(response))
                return True

    # --------------------------------------------------------
    # Goodbye
    # --------------------------------------------------------
    if is_goodbye(command):
        speak(engine, "Goodbye! Have a great day.")
        return False

    # --------------------------------------------------------
    # Reminder
    # --------------------------------------------------------
    reminder_data = parse_reminder(command)

    if reminder_data:
        amount, unit, task = reminder_data
        seconds = reminder_to_seconds(amount, unit)

        if seconds is not None and seconds >= 0:
            schedule_reminder(engine, seconds, task)

            if unit.startswith("second"):
                unit_text = "second" if amount == 1 else "seconds"
            elif unit.startswith("minute"):
                unit_text = "minute" if amount == 1 else "minutes"
            else:
                unit_text = "hour" if amount == 1 else "hours"

            response = (
                f"Okay, I will remind you in {amount:g} {unit_text}"
            )

            if task:
                response += f" to {task}."

            else:
                response += "."

            speak(engine, response)
            return True

    # --------------------------------------------------------
    # Weather
    # --------------------------------------------------------
    weather_city = extract_weather_city(command)

    if weather_city is not None:
        if not weather_city:
            state["waiting_for_weather_city"] = True
            speak(engine, "Which city's weather would you like?")
        else:
            state["waiting_for_weather_city"] = False
            speak(engine, get_weather(weather_city))

        return True

    # Weather follow-up:
    # User first says "weather", then says "nagai"
    if state.get("waiting_for_weather_city"):
        state["waiting_for_weather_city"] = False
        speak(engine, get_weather(command))
        return True

    # --------------------------------------------------------
    # Thanks / welcome / conversation
    # --------------------------------------------------------
    if is_thanks(command):
        speak(engine, "You're very welcome! I'm happy to help.")
        return True

    if is_welcome_response(command):
        speak(engine, "Thank you!")
        return True

    if is_nice_to_meet(command):
        speak(
            engine,
            "Nice to meet you too! I'm happy to help you."
        )
        return True

    if is_how_are_you(command):
        speak(
            engine,
            "I'm doing great, thanks for asking! How can I help you?"
        )
        return True

    if is_identity_question(command):
        speak(
            engine,
            "I'm your Python voice assistant, built for the Oasis Infobyte internship."
        )
        return True

    if is_capability_question(command):
        speak(
            engine,
            "I can tell you the time and date, check weather, answer "
            "general knowledge questions, solve maths, set reminders, "
            "tell jokes, and search the web."
        )
        return True

    # --------------------------------------------------------
    # Time
    # --------------------------------------------------------
    if is_time_question(command):
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        speak(engine, f"The current time is {current_time}.")
        return True

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------
    if is_date_question(command):
        current_date = datetime.datetime.now().strftime(
            "%A, %d %B %Y"
        )
        speak(engine, f"Today is {current_date}.")
        return True

    # --------------------------------------------------------
    # Joke
    # --------------------------------------------------------
    if re.search(r"\b(joke|make me laugh|tell me something funny)\b", command):
        speak(engine, random.choice(JOKES))
        return True

    # --------------------------------------------------------
    # Web search
    # --------------------------------------------------------
    search_query = extract_search_query(command)

    if search_query:
        speak(engine, f"Searching the web for {search_query}.")
        url = (
            "https://www.google.com/search?q="
            + urllib.parse.quote_plus(search_query)
        )

        try:
            webbrowser.open(url)
        except Exception:
            pass

        return True

    # --------------------------------------------------------
    # Maths
    # --------------------------------------------------------
    math_expression = extract_math_expression(command)

    if math_expression:
        speak(engine, solve_math(math_expression))
        return True

    # --------------------------------------------------------
    # General knowledge
    # --------------------------------------------------------
    knowledge_topic = extract_knowledge_topic(command)

    if knowledge_topic:
        speak(engine, answer_general_knowledge(knowledge_topic))
        return True

    # --------------------------------------------------------
    # Greeting
    # --------------------------------------------------------
    if is_greeting(command):
        speak(
            engine,
            "Hello! I am your voice assistant. How can I help you today?"
        )
        return True

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------
    speak(
        engine,
        "Sorry, I didn't understand that. You can ask me about "
        "the time, date, weather, general knowledge, maths, reminders, "
        "jokes, or ask me to search the web."
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Advanced Voice Assistant"
    )

    parser.add_argument(
        "--text",
        action="store_true",
        help="Type commands instead of using the microphone"
    )

    args = parser.parse_args()

    engine = init_engine()

    state = {
        "waiting_for_weather_city": False
    }

    recognizer = None
    sr_module = None

    # --------------------------------------------------------
    # Voice mode setup
    # --------------------------------------------------------
    if not args.text:
        try:
            import speech_recognition as sr_module
            recognizer = sr_module.Recognizer()

        except ImportError:
            print(
                "speech_recognition is not installed. "
                "Run: pip install SpeechRecognition"
            )
            return

        try:
            with sr_module.Microphone() as source:
                print(
                    "Calibrating microphone... "
                    "please stay quiet for 2 seconds."
                )
                recognizer.adjust_for_ambient_noise(
                    source,
                    duration=2
                )

        except OSError:
            print(
                "Could not access the microphone. "
                "Please check your microphone and try again."
            )
            return

    # --------------------------------------------------------
    # Startup
    # --------------------------------------------------------
    speak(
        engine,
        "Advanced voice assistant started. Ask me the time, "
        "date, weather, general knowledge questions, maths questions, "
        "set a reminder, tell a joke, or search the web."
    )

    running = True

    while running:
        try:
            command = (
                listen_text()
                if args.text
                else listen_voice(recognizer, sr_module)
            )

        except OSError:
            speak(
                engine,
                "I could not access the microphone. "
                "Please check your microphone and try again."
            )
            break

        if command is None:
            speak(
                engine,
                "Sorry, I did not catch that. Could you please repeat?"
            )
            continue

        if command == "REQUEST_ERROR":
            speak(
                engine,
                "I could not reach the speech service. "
                "Please check your internet connection."
            )
            continue

        running = handle_command(
            command,
            engine,
            state
        )


if __name__ == "__main__":
    main()
