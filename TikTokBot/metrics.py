"""
    Metrics for evaluating feed diversity.
    Unless otherwise specified, feeds are passed using Pandas Dataframes containing VideoInfo.
"""
import pandas as pd
from itertools import chain

def jaccard_index(f1, f2, feature="v_id"):
    """
        Returns the Jaccard Index between two feeds.
    """
    # Jaccard Index = overlap between two sets = (size of intersection / size of union)
    f1_items = set(f1[feature])
    f2_items = set(f2[feature])
    return len(f1_items & f2_items) / len(f1_items | f2_items)


def feature_presence(feed, feature="creator"):
    """
        Returns ratio of unique values of feature over total number of values.
        1 = all values are unique (most diversity), ~0 = almost all values are repeated at least once
    """
    if not isinstance(f1[feature][0], list):
        # Single valued feature (e.g. creator), ratio = unique / total
        return len(feed[feature].unique()) / len(feed)
    else:
        # Feature is a list, we need to look at the individual items in the lists
        all_items = [i for l in feed[feature] for i in l]
        return len(set(all_items)) / len(all_items)



if __name__ == "__main__":
    import TikTokBot.preprocessing as preproc

    # Testing/Experimenting
    DATA_DIR = "./data/tags"
    f1 = pd.read_csv(DATA_DIR + "/antivax/nojab.csv")
    f2 = pd.read_csv(DATA_DIR + "/antivax/nopoke.csv")
    f1 = preproc.prep_vidinfo(f1)
    f2 = preproc.prep_vidinfo(f2)

    print(feature_presence(f1, "tags"))
    print(feature_presence(f2, "tags"))
