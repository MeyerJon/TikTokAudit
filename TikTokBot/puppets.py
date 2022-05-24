"""
    Specific puppet implementations.
"""
import random, time
from TikTokBot.bot import Bot
from TikTokBot.utils import random_wait


"""
    Base/Shared puppet behaviours
"""
class PuppetBase(Bot):
    
    def __init__(self, driver, puppet_id, output_file=None):
        output_file = output_file or f"./{puppet_id}_out.csv"
        super().__init__(driver, output_file)
        self._id = puppet_id

    def pre_run_routine(self, k=3):
        """
            Watches a few videos from a predefined set.
        """
        fname = f"./prime_{self._id[:2]}.csv"
        urls = list()
        with open(fname, 'r') as f:
            urls = f.readlines()
        
        picks = random.sample(urls, k=k)
        watchtime = 2 # Fraction of total time

        for p in picks:

            self._driver.get(p)
            # Check if video available
            error_msg = self._wait_el_by_xpath("/html/body/div[2]/div[2]/div[2]/div[1]/div/p[1]")
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

            random_wait(1) # Random wait before moving on

    def video_relevant(self, vidinfo):
        """
            For a given VideoInfo object, returns true
            if the video is considered relevant enough for the puppet to like.
        """ 
        # This is implementation specific, since more engaged bots have lower standards of relevance.
        raise NotImplementedError

    def creator_relevant(self, creator):
        """
            For a given creator, returns true
            if the given creator is considered relevant enough for the puppet to follow.
        """
        # False by default, but implementation specific depending on engagement
        return False


"""
    Passive puppet:
        - Only browses FYP
        - Only watches relevant content, and doesn't watch posts more than once per run
        - Occassionally likes posts
"""
class PuppetPassive(PuppetBase):
    pass


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