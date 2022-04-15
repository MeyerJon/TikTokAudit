from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, TimeoutException
from TikTokBot.utils import random_wait, emulate_keystrokes
import time, traceback, logging, json, re


# POD for video info
class VideoInfo:

    def __init__(self, vid, creator, desc, tags, duration):
        self.vid = vid
        self.creator = creator
        self.desc = desc
        self.tags = tags
        self.duration = duration
        self.likes = None
        self.comments = None
        self.sound = None

    def valid(self):
        """
            True if essential fields are not None
        """
        return (self.vid is not None) and (isinstance(self.creator, str)) and (isinstance(self.desc, str)) \
                and (isinstance(self.tags, list)) and (isinstance(self.duration, float))

    def to_csv(self):
        """
            Returns CSV columns & value
            <value_str> <columns>
        """
        cols = "v_id,creator,desc,duration,likes,comments,sound,tags"
        vals = f"{self.vid},\"{self.creator}\",\"{self.desc}\",{self.duration},{self.num_str_to_int(self.likes)},"
        vals += f"{self.num_str_to_int(self.comments)},\"{self.sound}\",\"{self.tags}\""
        return (vals, cols)

    def num_str_to_int(self, n):
        """
            Converts from shorthand number strings to integers
            e.g. "10.5K" -> 10500
        """
        if not isinstance(n, str):
            return n

        suffix = {'K': 1000, 'M': 1_000_000, 'B': 1_000_000_000}
        if n[-1] in suffix:
            # Strip suffix & multiply
            return round(float(n[:-1]) * suffix[n[-1]])
        else:
            # Number is likely already expressed in full
            return int(n)


"""
    Main bot class,
    contains all browsing functionality
"""
class Bot:

    def __init__(self, driver, output_file="./aggregate-data.csv"):
        self._driver = driver
        self._wait = WebDriverWait(self._driver, 5) # Waits for max. 5 seconds
        self._outf = output_file
        self.logger = logging.getLogger('Bot')
        self.logger.setLevel(20)

        # Prepare output file
        with open(self._outf, "w") as ofile:
            ofile.write(VideoInfo(0, "", "", [], 1).to_csv()[1] + "\n")

    ### Accessors ###
    def set_output_file(self, fname):
        """
            Sets the default output file for storing collected VideoInfo
        """
        self._outf = fname

    def set_credentials(self, email, password):
        """
            Sets credentials the bot should use for its Google account.
        """
        self.google_creds = {"email": email, "password": password}


    ### Locating elements ###
    def _el_by_xpath(self, path):
        """
            Returns the element for a given XPath, or None if element not found.
        """
        try:
            return self._driver.find_element(by=By.XPATH, value=path)
        except NoSuchElementException:
            return None
        except Exception as e:
            self.logger.error("Error while locating element by XPath.", exc_info=True)
            raise e

    def _wait_el_by_xpath(self, path, time=5):
        """
            Returns element if found after waiting some time.
        """
        elem = None
        try:
            elem = WebDriverWait(self._driver, time).until(EC.presence_of_element_located((By.XPATH, path)))
        except Exception as e:
            self.logger.error("Error while waiting for element.", exc_info=True)
        return elem

    
    ### Data collection ###
    # Assume a video is open/in focus (for locating by XPath) unless stated otherwise
    def get_video_element(self):
        """
            Returns the video player WebElement (or None if not found after max wait)
        """
        return self._wait_el_by_xpath("/html/body/div[2]/div[2]/div[3]/div[1]/div[2]/div[1]/div/video")

    def get_video_id(self):
        """
            Returns the ID (19 digits) for the currently opened TikTok video.
        """
        #['https:', '', 'www.tiktok.com', '@user', 'video', '7068338808634215686?is_copy_url=1&is_from_webapp=v1']
        return self._driver.current_url.split(sep="/")[5].split(sep='?')[0]

    def get_video_tags(self):
        """
            Returns hashtags & mentions for the opened/currently viewed TikTok video.
        """
        tags = list()
        try:
            desc_el = self._el_by_xpath("/html/body/div[2]/div[2]/div[3]/div[2]/div[2]/div[1]")
            tag_els = desc_el.find_elements(by=By.CSS_SELECTOR, value='a') # Tags are links in description
            for t_e in tag_els:
                tag_span = t_e.find_element(by=By.CSS_SELECTOR, value="strong") # Tags & mentions are encapsulated by <strong>
                tags.append(tag_span.text)
        except Exception as e:
            self.logger.info("Could not fetch tags (%s)", self._driver.current_url)
        return tags

    def get_video_sound(self):
        """
            Returns sound used in video.
        """
        try:
            sound_el = self._el_by_xpath("/html/body/div[2]/div[2]/div[3]/div[2]/div[2]/h4/a")
            return sound_el.text
        except Exception as e:
            self.logger.info("Could not locate sound element (%s)",self._driver.current_url)

    def get_video_creator(self):
        """
            Returns username of the video's creator.
        """
        try:
            return self._el_by_xpath("/html/body/div[2]/div[2]/div[3]/div[2]/div[1]/a[2]/span[1]").text
        except Exception as e:
            self.logger.warning("Could not locate creator element (%s)", self._driver.current_url)

    def get_video_description(self):
        """
            Returns video's description (can be empty).
        """
        try:
            desc_el = self._el_by_xpath("/html/body/div[2]/div[2]/div[3]/div[2]/div[2]/div[1]/span[1]")
            if desc_el is not None:
                return desc_el.text
            else:
                return ""
        except Exception as e:
            self.logger.info("Could not locate description element (%s)", self._driver.current_url)

    def get_video_duration(self):
        try:
            vid_el = self.get_video_element()
            duration = vid_el.get_property("duration")
            return duration
        except Exception as e:
            self.logger.warning("Could not fetch video duration (%s)", self._driver.current_url)


    ### Handling anomalies ###
    def close_cookie_banner(self, accept=False):
        c_b = None
        try:
            c_b = WebDriverWait(self._driver, 4).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'tiktok-cookie-banner')))
        except TimeoutException:
            return None

        if c_b is not None:
            shadowroot = c_b.get_property("shadowRoot") # The banner contains a shadowroot for some reason
            btns = shadowroot.find_elements(By.CSS_SELECTOR, "button")
            if len(btns) > 0:
                accept_ix = 0 if "accept" in btns[0].text.lower() else 1 # Banking on text match to identify correct button
                if accept:
                    btns[accept_ix].click()
                else:
                    btns[(accept_ix + 1) % 2].click()

    def pause_for_captcha(self):
        """
            Checks if Captcha has popped up, and if so, waits until it is gone
        """
        try:
            time.sleep(1)
            WebDriverWait(self._driver, 180).until(EC.invisibility_of_element_located((By.ID, 'tiktok-verify-ele')))
            time.sleep(1)
        except Exception as e:
            self.logger.error("Exception during captcha-handling.", exc_info=True)

    def unstuck_video(self):
        """
            Checks if video if paused or 'unavailable' for whatever reason,
            tries to play it or otherwise continues the run.
        """
        console_log = self._driver.get_log("browser")
        # Search for any relevant exceptions in the JS
        for l in console_log:
            # TODO: Handle run getting stuck properly
            if l['level'] == "SEVERE":
                # Temp solution? Switch to previous video and return to this one
                # This actually doesn't work since the log remains and the bot gets stuck in a loop
                # Or something, I'm not sure, it just gets stuck here
                print("Video stuck") # Manual fixing for the time being
                """
                self.prev_video()
                random_wait(0.2)
                self.next_video()
                break
                """

    def dismiss_content_warning(self):
        """
            Some videos come with a (disturbing) content warning.
            This function checks whether the 'watch anyway' button is present, and if so, clicks it.
        """
        try:
            dismiss_btn = WebDriverWait(self._driver, 2).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div[3]/div[1]/div[2]/div[5]/div/div[2]/button[2]")))
            dismiss_btn.click()
        except TimeoutException:
            pass
        except Exception as e:
            self.logger.error("Error while dismissing content warning.", exc_info=True)

    
    ### Internal behaviours ###
    def collect_open_video_info(self):
        """
        Assumes a TikTok video is being viewed and returns corresponding VideoInfo object
        """
        # Wait until video is playing
        vid_el = self._wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
        if vid_el.__sizeof__ == 0:
            time.sleep(1)

        vid = self.get_video_id()
        creator = self.get_video_creator()
        desc = self.get_video_description()
        tags = self.get_video_tags()
        duration = self.get_video_duration()

        # Temp? Like & comment counts
        likes_el = self._el_by_xpath("/html/body/div[2]/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/button[1]/strong")
        likes = likes_el.text
        comments_el = self._el_by_xpath("/html/body/div[2]/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/button[2]/strong")
        comments = comments_el.text

        vid_data = VideoInfo(vid, creator, desc, tags, duration)
        vid_data.sound = self.get_video_sound()
        vid_data.likes = likes
        vid_data.comments = comments
        return vid_data

    def prev_video(self):
        """
            Assuming a TikTok is being viewed, returns to the previous one using the arrow button
        """
        cur_id = self.get_video_id()
        while self.get_video_id() == cur_id:
            try:
                up_btn = self._wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[2]/div[3]/div[1]/button[2]")))
                up_btn.click()
                time.sleep(0.1)
            except ElementNotInteractableException:
                continue
            except Exception as e:
                self.logger.error(f"Could not continue to next video ({self._driver.current_url})", exc_info=True)
            time.sleep(0.5)

    def next_video(self):
        """
            Assuming a TikTok is being viewed, continues to next one using the arrow button
            Returns False if bot could not move to next video for some reason.
        """
        timeout_count = 0
        cur_id = self.get_video_id()
        while self.get_video_id() == cur_id:
            if timeout_count >= 3:
                # Assume there is no next video (the arrow hasn't loaded)
                return False
            try:
                down_btn = self._wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div[3]/div[1]/button[3]")))
                down_btn.click()
                time.sleep(0.1)
            except ElementNotInteractableException:
                continue
            except TimeoutException:
                # There might not be a next video, keep track of count
                timeout_count += 1
            except Exception as e:
                self.logger.error(f"Could not continue to next video ({self._driver.current_url})", exc_info=True)
                return False
            time.sleep(0.5)
        return True

    def write_vidinfo(self, vi, header=False):
        """
            Saves VideoInfo data to output file. Creates/overwrites file if header=True
        """
        mode = "w" if header else "a"
        with open(self._outf, mode) as ofile:
            row, cols = vi.to_csv()
            if header: ofile.write(cols + '\n')
            ofile.write(row + '\n')

    def check_run_paused(self):
        """
            Checks sessionStorage.botflags for 'paused' flag, waits until flag is removed
        """
        paused = True
        log_msg = False
        while paused:
            time.sleep(0.25)
            flags = self._driver.execute_script("return window.sessionStorage.botflags")
            if flags is not None:
                flags = flags.split(sep=',')
                paused = ("paused" in flags)
                if paused and not log_msg: 
                    # Just to check if the run was actually paused
                    log_msg = True
                    print("Run paused.")
                    self.logger.info("Run paused.")
            else:
                break
        if log_msg:
            print("Run unpaused.")
            self.logger.info("Run unpaused.")

    def _browse(self, base_url, first_xpath, n, **kwargs):
        """
            Starting from base_url, tries to open first video and browses n TikToks
            Writes videodata to file for each video.
        """
        # Config
        max_watch_time = kwargs.get("max_watch_time", 6)
        to_skip = kwargs.get("to_skip", None)

        # Navigate to base page
        self._driver.get(base_url)
        random_wait(1.0)

        # Close cookies banner by rejecting
        self.close_cookie_banner()
        random_wait(1.0)

        # Open first recommended video
        try:
            first_rec = self._wait_el_by_xpath(first_xpath)
            if first_rec is not None:
                first_rec.click()
            else:
                self.logger.warning("No first post located on page. Aborting run.")
                return
        except Exception as e:
            print("Could not open first TikTok. Aborting run")
            raise e
        random_wait(1.0)

        # Run
        self.logger.info(f"Beginning run ({n} videos)")
        run_ids = to_skip or set() # Video IDs encountered this run
        i = 0
        while i < n:
            try:
                self.check_run_paused()  # Check if run suspended
                self.pause_for_captcha() # Pauses run if captcha popup opened
                self.unstuck_video()
                self.dismiss_content_warning() # Dismisses any 'disturbing content' warning
                # TODO:
                # - Add check to unpause videos that got paused automatically

                # Collect statistics about this video
                random_wait(0.1)
                v_d = self.collect_open_video_info()
                random_wait(0.1)
                valid = v_d.valid()

                if not valid:
                    # Log issues with collected VideoInfo
                    s = self._driver.current_url + ": " + str(v_d.creator) + " / " + str(v_d.desc) + "\n"
                    s += str(v_d.tags) + " / " + str(v_d.duration) + "s." 
                    self.logger.info("Invalid VideoInfo: %s", s)
                    continue

                # Skip already seen videos
                if v_d.vid in run_ids:
                    #self.logger.info("Skipping video: %s", v_d.vid)
                    random_wait(0.2, 0.1, 0.1)
                else:
                    if (i+1) % 5 == 0: print(f"Watching video {i+1}/{n}")
                    i += 1
                    run_ids.add(v_d.vid)
                    self.write_vidinfo(v_d, header=(i==1))
                    # Watch a little more than half of the video
                    random_wait(min(v_d.duration*0.55, max_watch_time), sdev=0.25, min_t=(max_watch_time/1.5))

            except Exception as e:
                traceback.print_exc()
                self.logger.error("Exception during run. Aborting.", exc_info=True)
                print("Error during run. Aborting")
                break

            # Move on
            if not self.next_video():
                # Could not continue, abort the run
                self.logger.warning("Could not continue to next video, aborting run.")
                return
            random_wait(0.5, sdev=0.1, min_t=0.15)

        self.logger.info("Finished run.")

    def like_video(self, like=True):
        """
            Assuming a tiktok is being viewed, likes that tiktok.
        """
        like_btn = self._wait_el_by_xpath("/html/body/div[2]/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/button[1]")
        # Check liked status based on color of icon
        # This isn't hugely stable, of course - hopefully tiktok keeps this color code for the duration of the experiment
        svg_icon = like_btn.find_element(By.CSS_SELECTOR, "svg")
        fill_col = svg_icon.get_attribute("fill")
        rgba = re.findall(r'\d+', fill_col)
        liked = rgba[0] >= 100 # Assume that if the heart icon is red, the post has been liked
        if like != liked:
            like_btn.click()

    def follow_video(self, follow=True):
        """
            Assuming a tiktok is being viewed, follows the creator.
        """
        follow_btn = self._wait_el_by_xpath("/html/body/div[2]/div[2]/div[3]/div[2]/div[1]/button")
        # Check if creator already followed by
        following = "Following" == follow_btn.text
        if follow != following:
            follow_btn.click()

    def execute_search(self, query):
        """
            Executes a search query.
        """
        search_field = None
        try:
            search_field = WebDriverWait(self._driver, 3).until(EC.presence_of_element_located((By.NAME, 'q')))
        except TimeoutError:
            self.logger.warning("Could not execute search - searchbar not found.")
        
        if search_field is not None:
            emulate_keystrokes(search_field, query)
            random_wait(0.1)
            search_field.send_keys(Keys.RETURN)
        

    ### Routines ###

    def login_google(self):
        """
            If credentials are set, logs the bot in to Google. 
        """
        creds = None
        try:
            creds = self.google_creds
        except AttributeError as e:
            self.logger.error("Could not log in: no credentials set.")
            raise Exception("No Google credentials set.")

        # Go to Google
        self._driver.get("http://google.com")
        random_wait(0.2)

        # Accept cookies
        cookie_btn = self._wait.until(EC.presence_of_element_located((By.ID, "L2AGLb")))
        cookie_btn.click()
        random_wait(0.2)

        login_btn = self._wait_el_by_xpath("/html/body/div[1]/div[1]/div/div/div/div[2]/a")
        login_btn.click()
        random_wait(0.1)

        email_field = self._wait_el_by_xpath("/html/body/div[1]/div[1]/div[2]/div/div[2]/div/div/div[2]/div/div[1]/div/form/span/section/div/div/div[1]/div/div[1]/div/div[1]/input")
        emulate_keystrokes(email_field, creds["email"])

        nxt_btn = self._wait_el_by_xpath("/html/body/div[1]/div[1]/div[2]/div/div[2]/div/div/div[2]/div/div[2]/div/div[1]/div/div/button")
        nxt_btn.click()
        random_wait(0.1)

        pw_field = self._wait_el_by_xpath("/html/body/div[1]/div[1]/div[2]/div/div[2]/div/div/div[2]/div/div[1]/div/form/span/section/div/div/div[1]/div[1]/div/div/div/div/div[1]/div/div[1]/input")
        emulate_keystrokes(pw_field, creds["password"])

        nxt_btn = self._wait_el_by_xpath("/html/body/div[1]/div[1]/div[2]/div/div[2]/div/div/div[2]/div/div[2]/div/div[1]/div/div/button")
        nxt_btn.click()

    def login_tiktok(self):
        """
            Logs into tiktok using Google credentials.
        """
        creds = None
        try:
            creds = self.google_creds
        except AttributeError as e:
            self.logger.error("Could not log in: no credentials set.")
            raise Exception("No Google credentials set.")

        # Go to TikTok
        self._driver.get("http://tiktok.com")
        random_wait(3)

        self.close_cookie_banner()

        # Open the login popup
        login_btn = self._wait_el_by_xpath("/html/body/div[2]/div[1]/div/div[2]/button")
        login_btn.click()
        random_wait(2.0)

        # 'Continue with Google' button
        # Popup located in a different iframe
        login_frame = self._driver.switch_to.frame(self._driver.find_element(By.XPATH, '//iframe'))
        google_opt_btn = self._wait_el_by_xpath("/html/body/div[1]/div/div[1]/div/div[1]/div[2]/div[4]", time=8)
        if google_opt_btn is None:
            # Fallback in case the layout changes but the text on the button remains the same
            google_opt_btn = self._wait_el_by_xpath('//div[contains(text(), "Continue with Google")]', time=8)
        google_opt_btn.click()
        random_wait(1.0)

        # Popup window is now open
        self._driver.switch_to.window(self._driver.window_handles[-1]) # Last opened window is the Google login screen
        # Enter email
        email_field = self._wait_el_by_xpath("/html/body/div[1]/div[1]/div[2]/div/div[2]/div/div/div[2]/div/div[1]/div/form/span/section/div/div/div[1]/div/div[1]/div/div[1]/input")
        emulate_keystrokes(email_field, creds["email"])

        nxt_btn = self._wait_el_by_xpath("/html/body/div[1]/div[1]/div[2]/div/div[2]/div/div/div[2]/div/div[2]/div/div[1]/div/div/button")
        nxt_btn.click()
        random_wait(1.0)

        # Enter password
        pw_field = self._wait_el_by_xpath("/html/body/div[1]/div[1]/div[2]/div/div[2]/div/div/div[2]/div/div[1]/div/form/span/section/div/div/div[1]/div[1]/div/div/div/div/div[1]/div/div[1]/input")
        emulate_keystrokes(pw_field, creds["password"])

        nxt_btn = self._wait_el_by_xpath("/html/body/div[1]/div[1]/div[2]/div/div[2]/div/div/div[2]/div/div[2]/div/div[1]/div/div/button")
        nxt_btn.click()
        random_wait(3.0)

        # Popup windows are automatically closed, switch back to be safe
        self._driver.switch_to.window(self._driver.window_handles[0])

    def anon_run(self, n=10, to_skip=None):
        """
            Browses top n posts on the FYP/home page

            Parameters:
                n (int): Number of videos to watch
                to_skip (set<str>): Video IDs to skip
        """
        # Config
        max_watch_time = 6 # in seconds

        # Data collection
        self._browse(base_url="http://tiktok.com", first_xpath="/html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div",
                     n=n, to_skip=to_skip, max_watch_time=max_watch_time)
        
    def browse_tag(self, tag, n=10, to_skip=None):
        """
            Browses the top n videos of the given tag
        """
        # Config
        max_watch_time = 6 # in seconds
        tag_url = f"http://tiktok.com/tag/{tag}"

        # Data collection
        self._browse(base_url=tag_url, first_xpath="/html/body/div[2]/div[2]/div[2]/div/div[2]/div/div[1]/div[1]/div/div/a",
                     n=n, to_skip=to_skip, max_watch_time=max_watch_time)

    def browse_creator(self, creator, n=10, to_skip=None):
        """
            Browses n most recent videos of the given creator
        """
        # Config
        max_watch_time = 6 # in seconds
        user_url = f"http://tiktok.com/@{creator}"

        # Data collection
        self._browse(base_url=user_url, first_xpath="/html/body/div[2]/div[2]/div[2]/div/div[2]/div[2]/div/div[1]/div[1]/div/div/a",
                     n=n, to_skip=to_skip, max_watch_time=max_watch_time)
