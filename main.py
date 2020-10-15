"""
This script can be used to notify you when a slot comes available at your favorite gym.

Update the following settings in main.py:
- USER      - TopLogger username (email)
- PASSWORD  - TopLogger password
- GYMS      - The id of the gyms you want to check
- QUEUE     - List if gyms and periods to look at
"""
import time
from datetime import datetime
from datetime import timedelta

try:
    import config
except ImportError:
    import config_sample as config

from models import QueueItem
from telegram import Telegram
from toplogger import TopLogger


def notify(slots):
    """
    Send Telegram notification for available slots
    """

    if len(slots) == 0:
        return

    message = f"Slot(s) available at: {slots[0].date.strftime('%A %d %B')}"
    for slot in slots:
        #  TODO: would be nice to have a link to slot in message
        message += f"\n -> {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}"
    if config.DEBUG:
        print(f"DEBUG: message\n\t{message}")
    else:
        Telegram(config.TOKEN, config.CHAT_ID).send_message(message)


def check(top_logger: TopLogger, item: QueueItem):
    """
    Check for available slot(s) based on given item
    """
    available = 0
    if not item.handled:
        top_logger.gym = item.gym
        available_slots = top_logger.available_slots(item.period)
        available = len(available_slots)
        if available_slots:
            notify(available_slots)
            item.handled = True

    return available


def repeat(top_logger):
    """
    Run check each INTERVAL seconds.
    """
    now = datetime.now()
    available_slots = 0
    print(f"{now}  --  START: check for {len(config.QUEUE)} slots")
    for item in config.QUEUE:
        # TODO: find out if the 10 days check is DB only
        if item.period.start <= (now + timedelta(10)):
            available_slots += check(top_logger, item)
    # TODO: add proper logging
    print(f"{now}  --  FINISH: found {available_slots} slots")
    time.sleep(config.INTERVAL)
    repeat(top_logger)


if __name__ == '__main__':
    repeat(TopLogger(config.USER, config.PASSWORD))
