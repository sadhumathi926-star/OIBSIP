"""
Voice Assistant - Browser Version (Flask)
Run:  python app.py   -> opens http://127.0.0.1:5000 in your browser.
Use Chrome or Edge (they support the Web Speech API).
"""
import datetime
import threading
import urllib.parse
import webbrowser

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def process_command(command: str) -> dict:
    command = command.lower().strip()

    if any(w in command for w in ("exit", "quit", "stop", "bye")):
        return {"reply": "Goodbye! Have a great day.", "action": "stop"}

    if "hello" in command or command == "hi":
        return {"reply": "Hello! I am your voice assistant. How can I help you today?"}

    if "time" in command:
        return {"reply": "The current time is " + datetime.datetime.now().strftime("%I:%M %p") + "."}

    if "date" in command or "today" in command:
        return {"reply": "Today is " + datetime.datetime.now().strftime("%A, %d %B %Y") + "."}

    for trigger in ("search for", "search", "google", "look up"):
        if trigger in command:
            query = command.split(trigger, 1)[1].strip()
            if not query:
                return {"reply": "What should I search for? Say search, followed by your topic."}
            url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
            return {"reply": f"Searching the web for {query}.", "url": url}

    return {"reply": "Sorry, I can only greet, tell the time and date, or search the web."}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/command", methods=["POST"])
def command():
    text = (request.get_json(silent=True) or {}).get("text", "")
    return jsonify(process_command(text))


if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(port=5000)