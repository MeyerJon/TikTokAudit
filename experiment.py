from code import interact
from TikTokBot import setup_anon_puppet, setup_puppet
from TikTokBot.puppets import PuppetBase
from selenium import webdriver
import logging, time


DRIVER_PATH = "./drivers/chromedriver"
CREDS_FILE = "./users/creds.json"


def get_skippable_ids(fname="./to-skip.csv"):
    to_skip = set()
    with open(fname, 'r') as ifile:
        to_skip = set(ifile.read().split()[1:]) # Ignore header, read the rest
    return to_skip

def manual_setup(login=True):
    """
        Returns TTDelver puppet (anon session)
        mostly for experimental/testing purposes
    """
    bot = setup_anon_puppet(DRIVER_PATH, profile_file="./profile_AV.json")
    bot._id = "AVANON"
    bot.set_credentials("hku63202@mzico.com", "TTDelver PW")
    if login: bot.login_tiktok()
    return bot

def collect_tags(bot, tags):
    try:
       for t in tags:
            print("Browsing tag:", t)
            bot.set_output_file(f"./data/tags/hate/{t}.csv")
            bot.browse_tag(t, n=50)
    except Exception as e:
        print("Exception occurred:")
        raise e

def collect_creators(bot, creators):
    try:
       for c in creators:
            print("Browsing creator:", c)
            bot.set_output_file(f"./data/creators/hate/{c}.csv")
            bot.browse_creator(c, n=50)
    except Exception as e:
        print("Exception occurred:")
        raise e

if __name__ == "__main__":

    logging.basicConfig(filename="./logs", filemode='w', format='%(asctime)s - [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

    #bot = manual_setup(login=True)
    #time.sleep(3)
    #bot.pre_run_routine()
    #bot.browse_fyp(interact=False)

    bot = setup_puppet(DRIVER_PATH, CREDS_FILE, "AV3", puppet_type=3, use_undetected=False)
    #time.sleep(600)
    #bot.login_tiktok()
    time.sleep(1)
    #bot.pre_run_routine(k=5, likes=True)
    time.sleep(1)
    #bot.browse_fyp(n=1, interact=True)
    bot._driver.get("http://tiktok.com")
    time.sleep(2)
    bot.browse_query(n=5, interact=True)
