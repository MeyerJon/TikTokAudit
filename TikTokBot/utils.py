"""
    Misc utility for the bot
"""
import time, random


def random_wait(t, sdev=0.2, min_t=None):
    """
        Waits a random amount of seconds (normal distribution according to given params)
    """
    min_t = min_t or (t/2.0)
    time.sleep(max(min_t, random.normalvariate(t, sdev)))

def emulate_keystrokes(el, text):
    """
        Emulates typing into the given element
    """
    SPC = 1.0/7.25 # Assumes ~7 keystrokes per second on average
    for c in text:
        el.send_keys(c)
        random_wait(t=SPC, sdev=0.075, min_t=SPC/3.0)