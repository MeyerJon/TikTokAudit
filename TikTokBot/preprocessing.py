import pandas as pd
import os, glob, re

### DATA LOADING ###
def load_folder(path):
    """
        Returns dataframe with all data in specified folder
    """
    pathlist = glob.glob(os.path.join(str(path), "*.csv"))
    return pd.concat([pd.read_csv(fname) for fname in pathlist], axis=0, ignore_index=True)

def load_folders(paths):
    dfs = list()
    for p in paths:
        dfs.append(load_folder(p))
    return pd.concat(dfs, axis=0, ignore_index=True)


### DATA FORMATTING ###
def tags_str_to_list(s):
    """
        Converts tags column from string to list
    """
    if s == '[]': return list()
    
    hashtags = ['#' + x.lower() for x in re.findall("#(.+?)'", s)]
    mentions = ['@' + x[:-1] for x in re.findall("@(.+?)[,\]]", s)]
    return hashtags + mentions


### DATA CLEANING ###
def remove_emojis(data):
    """
        Thanks to Denis da Mata & Karim Omaya on 
        https://stackoverflow.com/questions/33404752/removing-emojis-from-a-string-in-python
    """
    emoj = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642" 
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
                      "]+", re.UNICODE)
    return re.sub(emoj, '', data)

def common_filter_rules(tag):
    """
        Rule-based (regex) heuristic to remove common tags.
        False if tag matches with any of the rules.
    """
    patterns = "(f+y+p*)+"
    patterns += "|(fory)"
    patterns += "|(vira+l)"
    patterns = re.compile(patterns)
    return len(patterns.findall(tag.lower())) == 0 # If any matches exist, ditch the tag


### CONVENIENCE ###
def prep_vidinfo(df):
    """
        Takes a 'raw' VideoInfo dataframe and returns a preprocessed version.
    """
    # Dropping duplicate videos
    data = df.drop_duplicates(subset=["v_id"], keep="first")

    # Converting tags column from string to list
    data.loc[:, 'tags'] = data.loc[:, 'tags'].apply(tags_str_to_list)

    return data