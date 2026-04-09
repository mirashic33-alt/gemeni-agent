"""
time_sense.py — time-of-day awareness.
Used to inject date/time context into the agent's system prompt.
"""

from datetime import datetime


def get_time_of_day(hour: int | None = None) -> str:
    """Returns the period of day based on the current hour."""
    if hour is None:
        hour = datetime.now().hour

    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 23:
        return "evening"
    else:
        return "night"


_GREETINGS = {
    "morning":   "Good morning",
    "afternoon": "Good afternoon",
    "evening":   "Good evening",
    "night":     "Good night",
}

def get_greeting() -> str:
    """Returns a greeting based on the current time of day."""
    return _GREETINGS[get_time_of_day()]


def get_datetime_context() -> str:
    """Returns the current date and time string for the system prompt."""
    now = datetime.now()
    weekdays = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday",
        3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday",
    }
    weekday = weekdays[now.weekday()]
    return now.strftime(f"%d.%m.%Y, {weekday}, %H:%M")


if __name__ == "__main__":
    print("=== time_sense test ===")
    print(f"Time of day : {get_time_of_day()}")
    print(f"Greeting    : {get_greeting()}")
    print()
    print("--- Prompt context ---")
    print(get_datetime_context())
