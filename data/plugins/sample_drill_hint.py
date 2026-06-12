"""
Sample TRINKER plugin — suggests a drill when feudal time is very late.
Drop your own .py files in data/plugins/ or %LOCALAPPDATA%\\TRINKER\\plugins\\
"""

from src.plugins.registry import register


def on_replay_imported(**kwargs):
    profile = kwargs.get("profile")
    if profile is None:
        return None
    feudal = getattr(profile, "feudal_time_sec", None)
    if feudal and feudal > 660:
        return {"suggest_drill": "feudal_consistency", "reason": "Feudal over 11:00"}
    return None


register("replay_imported", on_replay_imported)
