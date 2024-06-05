from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from joblib import Memory

cache_dir = ".cache/plots/"

memory = Memory(cache_dir, verbose=0)


def fig_to_pil(fig, dpi=600):
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=dpi)
    buf.seek(0)
    img = Image.open(buf)
    return img


def get_plot(question_stats, fname="", dpi=300, figsize=(10, 5)):
    fig, ax = plt.subplots(figsize=figsize)

    languages = list(question_stats[0].answers.keys())
    means = []
    stds = []
    for language in languages:
        ratings = [question_stats[i].ratings[language] for i in range(len(question_stats))]
        ratings = [r if r is not None else 0 for r in ratings]
        means.append(np.mean(ratings))
        stds.append(np.std(ratings))

    # Creating bar plot
    bars = ax.bar(languages, means, yerr=stds, capsize=5,
                  color=plt.cm.get_cmap('tab20').colors[:len(languages)])

    ax.set_ylim([0, 9.5])
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    fig.subplots_adjust(bottom=0.2)

    img = fig_to_pil(fig, dpi=dpi)

    if fname:
        plt.savefig(fname, dpi=dpi)

    plt.close(fig)
    return img


@memory.cache
def get_plot_cached(question_stats, fname="", dpi=300):
    return get_plot(question_stats, fname, dpi)
