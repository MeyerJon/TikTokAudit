from TikTokBot import setup_anon_bot, setup_puppet
from TikTokBot.bot import Bot
from selenium import webdriver
import logging, time


DRIVER_PATH = "./drivers/chromedriver"


def get_skippable_ids(fname="./to-skip.csv"):
    to_skip = set()
    with open(fname, 'r') as ifile:
        to_skip = set(ifile.read().split()[1:]) # Ignore header, read the rest
    return to_skip

def manual_setup(login=True):
    """
        Returns TTDelver bot (anon session)
        mostly for experimental/testing purposes
    """
    bot = setup_anon_bot(DRIVER_PATH)
    bot.set_credentials("hku63202@mzico.com", "TTDelver PW")
    if login: bot.login_tiktok()
    return bot

if __name__ == "__main__":

    logging.basicConfig(filename="./logs", filemode='w', format='%(asctime)s - [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

    # Read video IDs to be skipped
    to_skip = get_skippable_ids()

    #bot = setup_puppet(DRIVER_PATH, "./users/creds.json", "TTDelver")
    #bot.login_tiktok()
    bot = manual_setup(login=True)
    time.sleep(3)

    time.sleep(5)

    # Tags to collect
    tags = []
    try:
       for t in tags:
            print("Browsing tag:", t)
            bot.set_output_file(f"./data/tags/hate/{t}.csv")
            bot.browse_tag(t, n=50)
    except Exception as e:
        print("Exception occurred:")
        raise e

    # Creators to collect
    creators = []
    try:
       for c in creators:
            print("Browsing creator:", c)
            bot.set_output_file(f"./data/creators/hate/{c}.csv")
            bot.browse_creator(c, n=50)
    except Exception as e:
        print("Exception occurred:")
        raise e
