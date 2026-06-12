"""
Consistent icon vocabulary — Unicode symbols (no asset loading).
Maps to AoE2 UI concepts: ages, resources, military, UI chrome.
"""


class Icon:
    """Static icon glyphs used across Dashboard and overlay."""

    # App / navigation
    TRINKER = "⚔"
    DASHBOARD = "📜"
    LIBRARY = "📖"
    ANALYTICS = "📊"
    SETTINGS = "⚙"
    OVERLAY = "🛡"

    # Ages
    DARK = "🌑"
    FEUDAL = "🏰"
    CASTLE = "🏯"
    IMPERIAL = "👑"

    # Resources
    FOOD = "🌾"
    WOOD = "🪵"
    GOLD = "🪙"
    STONE = "🪨"
    POP = "👥"

    # Stats / status
    GAME = "⚔"
    TIMER = "⏱"
    QUALITY = "✦"
    COACH = "🛡"
    COMPARE = "⚖"
    LADDER = "🏆"
    WIN = "▲"
    LOSS = "▼"
    DRAW = "●"
    REFRESH = "↻"
    ASK = "💬"

    # Timing status
    ON_PACE = "●"
    BEHIND = "◐"
    LATE = "○"

    @staticmethod
    def result_glyph(result: str) -> str:
        r = (result or "").lower()
        if r == "win":
            return Icon.WIN
        if r == "loss":
            return Icon.LOSS
        return Icon.DRAW

    @staticmethod
    def status_glyph(status: str) -> str:
        return {
            "green": Icon.ON_PACE,
            "yellow": Icon.BEHIND,
            "red": Icon.LATE,
        }.get(status, "○")
