"""
    Specific puppet implementations.
"""
import random, time, json
from TikTokBot.bot import Bot
from TikTokBot.utils import random_wait


"""
    Base/Shared puppet behaviours
"""
class PuppetBase(Bot):
    
    def __init__(self, driver, puppet_id, profile_file=None, output_file=None):
        output_file = output_file or f"./{puppet_id}_out.csv"
        super().__init__(driver, output_file)
        self._id = puppet_id # This is always assumed to be either AVn or HSn (where n is an integer)

        # Behavior-related parameters
        self.relevance_like = 0
        self.relevance_follow = 0
        self.watch_duration = 0.2 # Fraction of TikTok duration

        # Interest data
        profile_file = profile_file or f"./profile_{puppet_id[:2]}.json"
        self._profile = self._read_profile(profile_file)
        if self._profile is None:
            self.logger.error(f"Could not read profile from {profile_file}")
            raise Exception("Aborting puppet setup: could not read profile.") 

        self.relevant_tags = self._profile['tags']
        self.relevant_creators = set(self._profile['creators'])
        self.relevant_sounds = set(self._profile['sounds'])

        # Log creation of puppet
        self.logger.info("Created puppet %s", self._id)
        

    # Config
    def _read_profile(self, profile_file):
        profile = None
        with open(profile_file, 'r') as f:
            try:
                profile = json.load(f)
            except json.JSONDecodeError as e:
                self.logger.exception("Invalid JSON profile.", stack_info=True)
            except Exception as e:
                self.logger.exception("Error while loading profile.", stack_info=True)
        return profile

    def set_like_thresh(self, thresh):
        """
            Sets the minimum required relevance for this puppet to like a video.
        """
        self.relevance_like = thresh
    
    def set_follow_thresh(self, thresh):
        """
            Sets the minimum required relevance for this puppet to follow a creator.
        """
        self.relevance_follow = thresh

    def _vid_relevance(self, vidinfo):
        r = sum([self.relevant_tags.get(t, 0) for t in vidinfo.tags])  # Score of tags
        r += (int(vidinfo.creator in self.relevant_creators) * 10)     # Flagged creators count for 10
        if vidinfo.sound is not None:
            r += int(vidinfo.sound in self.relevant_sounds)            # Flagged sounds count too
        return r

    def video_relevant(self, vidinfo):
        """
            For a given VideoInfo object, returns true
            if the video is considered relevant enough for the puppet to like.
        """ 
        return self._vid_relevance(vidinfo) >= self.relevance_like

    def creator_relevant(self, creator):
        """
            For a given creator, returns true
            if the given creator is considered relevant enough for the puppet to follow.
        """
        return self._vid_relevance(vidinfo) >= self.relevance_follow


    # Behaviors
    def pre_run_routine(self, k=3, likes=True):
        """
            Watches and likes a number of videos from a predefined set.
        """
        fname = f"./prime_{self._id[:2]}.csv"
        urls = list()
        with open(fname, 'r') as f:
            urls = f.readlines()
        
        picks = random.sample(urls, k=k)
        watchtime = 0.2 # Fraction of total time

        for p in picks:

            self._driver.get(p)
            # Check if video available
            error_msg = self._wait_el_by_xpath("/html/body/div[2]/div[2]/div[2]/div[1]/div/p[1]", verbose=False)
            if error_msg is not None:
                if "unavailable" in error_msg.text.lower():
                    # Append another pick to try instead & continue
                    picks.append(random.choice(urls))
                    continue

            # Watch the video for the required time, then move on
            vid_dur = None
            while vid_dur is None:
                vid_dur = self.get_video_duration()
            time.sleep(vid_dur * watchtime)

            if likes:
                self.like_video(like=True)

            random_wait(1) # Random wait before moving on

    def browse_fyp(self, n=50, interact=True):
        """
            Browses the FYP and collects data. 
            
            Parameters:
                - interact (bool): Puppet can like/follow (based on profile) if true
        """
        # Navigate to base page
        self._driver.get("http://tiktok.com/foryou")
        random_wait(1.0)

        # Close cookies banner by rejecting
        self.close_cookie_banner()
        random_wait(1.0)

        # Open first recommended video
        first_xpath = "/html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div"
        try:
            first_rec = self._wait_el_by_xpath(first_xpath)
            if first_rec is not None:
                first_rec.click()
            else:
                self.logger.warning("No first post located on page. Aborting run.")
                return
        except Exception as e:
            print("Could not open first recommended TikTok. Aborting run")
            raise e
        random_wait(1.0)

        # Run
        self.logger.info(f"Beginning run ({n} videos)")
        if not interact: self.logger.info("Interaction disabled.")
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

                i += 1
                self.write_vidinfo(v_d, header=(i==1))

                # Watch video for required duration
                req_duration = v_d.duration * self.watch_duration
                random_wait(req_duration, sdev=0.25, min_t=req_duration*0.9)

                # Potentially like the video/follow the creator
                if interact:
                    if self.video_relevant(v_d):
                        self.like_video()
                    if self.creator_relevant(v_d.creator):
                        self.follow_video()

                #print("Tags:", v_d.tags)
                #print("Relevance:", self._vid_relevance(v_d))

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



"""
    Passive puppet:
        - Only browses FYP
        - Doesn't watch posts more than once per run
        - Occassionally likes posts
"""
class PuppetPassive(PuppetBase):
    
    def __init__(self, driver, puppet_id, profile_file=None, output_file=None):
        super().__init__(driver, puppet_id, profile_file, output_file)
        
        # Passive params
        self.watch_duration = 1
        self.relevance_like = 2
        self.relevance_follow = 3


"""
    Casual puppet:
        - Only browses FYP
        - Watches relevant content twice (per run)
        - Likes sufficiently relevant posts, occassionally follows relevant creators
"""
class PuppetCasual(PuppetBase):
    pass


"""
    Active puppet:
        - Executes extra search queries before browsing FYP
        - Watches relevant content twice or more if very relevant/short
        - Likes all relevant posts, follows relevant creators   
"""
class PuppetActive(PuppetBase):
    pass