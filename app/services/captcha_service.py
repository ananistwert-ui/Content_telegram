from __future__ import annotations

import random

from app.models.bot import BotConfig


class CaptchaService:
    """Pure logic for building/validating the emoji captcha.

    Wrong answers never lock the user out (per spec: unlimited retries);
    the handler layer just re-shows the same captcha with attempts++.
    """

    @staticmethod
    def shuffled_options(config: BotConfig) -> list[str]:
        options = list(config.captcha_emojis)
        random.shuffle(options)
        return options

    @staticmethod
    def is_correct(config: BotConfig, chosen_emoji: str) -> bool:
        return chosen_emoji == config.captcha_correct_emoji
