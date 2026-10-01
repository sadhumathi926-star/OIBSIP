# Voice Assistant - Advanced Tier

Extends the beginner assistant with looser intent parsing, general knowledge
answers, live weather, timed reminders, and custom commands.

## New features
- **Free-form intent parsing**: understands phrasing variations (e.g. "hey
  what's the time right now") instead of requiring exact keywords.
- **General knowledge**: "who is Albert Einstein" / "what is photosynthesis"
  fetches a one-sentence summary from Wikipedia's free API (no key needed).
- **Live weather**: "weather in Chennai" fetches current conditions from
  OpenWeatherMap. Requires a free API key (see Setup).
- **Timed reminders**: "remind me in 5 minutes to check the oven" speaks an
  alert after the given time, without blocking further commands.
- **Custom commands**: edit `config.json` to add new trigger phrases and
  responses without touching the code.

## Setup
```
pip install -r requirements.txt
```
To enable weather:
1. Create a free account at https://openweathermap.org/appid
2. Copy your API key into `config.json`:
   ```json
   { "openweathermap_api_key": "YOUR_KEY_HERE" }
   ```
Weather still works to give a friendly message if you skip this step.

## Usage
```
python voice_assistant_advanced.py          # voice mode
python voice_assistant_advanced.py --text   # type commands (no microphone)
```

## Privacy
- Voice audio is only sent to Google's free speech-to-text service while the
  program is actively listening; nothing is recorded to disk.
- Wikipedia and OpenWeatherMap requests send only the search term / city name
  you speak - no personal data is included.
- `config.json` is stored locally and is never uploaded anywhere by this
  program.