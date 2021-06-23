"""This script can be used to notify you when a slot comes available at your favorite gym.
Update the settings in config.py.
"""
import sys
from datetime import datetime
from datetime import timedelta
import logging
import time
from typing import Dict
from typing import List

from dateutil.tz import gettz

from models import QueueItem
from models import Slot
from telegram_bot import TelegramBot
from toplogger import TopLogger
try:
    import config
except ImportError:
    # this should only be used by Github verifier
    import config_sample as config


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)


def init_notification(telegram: TelegramBot, queue: List[QueueItem]):
    message = ""
    for item in queue:
        str_format = '%A %d %B %H:%M'
        message += f"Searching for available slots in {item.gym.name} for " \
                   f"{item.period.start.strftime(str_format)} - {item.period.end.strftime(str_format)}\n"
    logger.info(f'init message:\n\t{message}')

    if not config.DEBUG:
        telegram.updater.bot.send_message(chat_id=config.CHAT_ID, text=message)


def exit_notification(telegram: TelegramBot):
    message = "Shutting down."
    logger.info(f'exit message:\n\t{message}')
    if not config.DEBUG:
        telegram.updater.bot.send_message(chat_id=config.CHAT_ID, text=message)


def notify(telegram: TelegramBot, item: QueueItem, slots: List[Slot]):
    """
    Send Telegram notification for available slots.
    """
    if not slots:
        return

    message = f"Slot(s) available at {item.gym.name} on {slots[0].date.strftime('%A %d %B')}"
    for slot in slots:
        message += f"\n -> {slot.start_at.strftime('%H:%M')} - {slot.end_at.strftime('%H:%M')}: {slot.spots_available} spot(s)"

    logger.info(f'Notify message:\n\t{message}')
    if not config.DEBUG:
        telegram.updater.bot.send_message(chat_id=config.CHAT_ID, text=message)


def check(top_logger: TopLogger, telegram: TelegramBot, queue: List[QueueItem]) -> int:
    """
    Check for available slot(s) based on given items in queue.
    """
    now = datetime.now(gettz())
    # register last_run for command /status message
    telegram.set_last_run(now)

    available = 0
    for item in queue:
        if not item.handled:
            top_logger.gym = item.gym
            available_slots = top_logger.available_slots(item.period)
            if available_slots:
                notify(telegram, item, available_slots)
                item.set_handled(True)
                available += len(available_slots)
    return available


def repeat(top_logger: TopLogger, telegram: TelegramBot, queue: List[QueueItem], interval: int):
    """
    Run check each INTERVAL seconds.
    """
    logger.info(f'  --  START: check for {len(queue)} slots')
    available = check(top_logger, telegram, queue)
    logger.info(f'  --  FINISH: found {available} new slots')

    interval = max(1, interval)
    time.sleep(interval)
    repeat(top_logger, telegram, queue, interval)


def main():
    """
    Start Top Logger notifier.

    Make sure you've set all necessary settings in config.py
    """
    top_logger = TopLogger()
    queue = config.QUEUE
    # setup telegram
    telegram_bot = TelegramBot(config.TOKEN)
    telegram_bot.set_queue(queue)

    # start schedule
    init_notification(telegram_bot, queue)
    try:
        repeat(top_logger, telegram_bot, queue, config.INTERVAL)
    except KeyboardInterrupt:
        exit_notification(telegram_bot)
        sys.exit(0)


if __name__ == '__main__':
    main()
