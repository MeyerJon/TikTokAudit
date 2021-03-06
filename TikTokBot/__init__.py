from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc
from TikTokBot.bot import Bot
from TikTokBot.puppets import PuppetPassive, PuppetCasual, PuppetActive, PuppetBase
import json, datetime, sys

PUPPET_TYPES = [PuppetBase, PuppetPassive, PuppetCasual, PuppetActive]

### Private functionality ###

def _default_outputfile(data_dir, puppet_id):
    """
        Returns the default filename for a given puppet's output.
    """
    return f"{data_dir}/{puppet_id}_{datetime.date.today()}_out.csv"


### Public functionality ###

def get_chrome_options(user_dir="./users/default", incognito=False):
    """
        Returns Options object which can be used to configure the driver.
    """
    options = Options()
    #options.add_argument(
    #    "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36")

    # Avoiding detection
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Preferences for browser
    """
    prefs = {
        'credentials_enable_service': False
    }
    options.add_experimental_option("prefs", prefs)
    """

    # Regular arguments
    if incognito: options.add_argument("--incognito")
    # options.add_argument("--profile-directory=Default")
    options.add_argument(f"--user-data-dir={user_dir}")
    options.add_argument("--mute-audio")

    return options

def setup_anon_puppet(driver_path, **kwargs):
    """
        Opens an anonymous browser instance and returns a configured bot.
    """

    data_dir = kwargs.get("data_dir", "./data")
    outf = kwargs.get("output_file", f"{data_dir}/anon.csv")
    profile_f = kwargs.get("profile_file", f"profile_anon.json")

    # Get session options
    driver_service = Service(driver_path)
    options = get_chrome_options(user_dir="./users/default", incognito=True)

    # Open driver
    driver = webdriver.Chrome(service=driver_service, options=options)

    # Make bot & set output file
    puppet = PuppetBase(driver, "ANON", profile_file=profile_f, output_file=outf)
    puppet.set_output_file(outf)
    return puppet

def setup_puppet(driver_path, creds_file, puppet_id, **kwargs):
    """
        Opens a browser instance corresponding to a user, returns a configured bot.
    """

    # Read credentials
    cred_info = None
    with open(creds_file, "r") as cfile:
        creds = json.load(cfile)
        try:
            cred_info = creds[puppet_id]
        except KeyError as e:
            logging.error(f"No credentials for puppet id '{puppet_id}'")
            raise Exception("Could not start session.")

    if cred_info is None:
        logging.warning("No credentials found. Aborting setup.")
        raise Exception("Could not start session.")

    # Set params
    data_dir = kwargs.get("data_dir", "./data")
    outf = kwargs.get("output_file", _default_outputfile(data_dir, puppet_id))

    user_dir_parent = kwargs.get("user_dir", "./users")
    user_dir = f"{user_dir_parent}/{puppet_id}"

    # Open driver
    driver = None
    use_undetected_chromedriver = kwargs.get("use_undetected", True)
    if use_undetected_chromedriver:
        ucoptions = uc.ChromeOptions()
        ucoptions.add_argument(f"--user-data-dir={user_dir}")
        ucoptions.add_argument("--mute-audio")
        if sys.platform == "linux":
            # Fix so the program uses Chrome instead of Chromium if both are installed
            ucoptions.binary_location = "/usr/bin/google-chrome"
        driver = uc.Chrome(options=ucoptions, version_main=102)
    else:
        driver_service = Service(driver_path)
        options = get_chrome_options(user_dir=user_dir, incognito=False)
        driver = webdriver.Chrome(service=driver_service, options=options)

    # Make bot & configure
    puppet_type = kwargs.get("puppet_type", 0) # 0 = Base, 1 = Passive, 2 = Casual, 3 = Active
    puppet_type = PUPPET_TYPES[puppet_type]
    puppet = puppet_type(driver, puppet_id, output_file=outf)
    puppet.set_data_dir(data_dir)
    puppet.set_credentials(cred_info["email"], cred_info["password"], platform=cred_info["platform"])

    return puppet
