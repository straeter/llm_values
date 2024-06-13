import numpy as np
import re


def extract_rating(s):
    # This regex looks for digits inside double brackets
    match = re.search(r'\[\[(\d+)\]\]', s)
    if match:
        rating = int(match.group(1))  # Convert the found digits into an integer
        return rating if 1 <= rating <= 9 else None
    else:
        return None  # Return None if no matching pattern is found


def get_discrepancy(answer):
    """Get the discrepancy (standard deviation of ratings across languages) for a single answer

    :param answer: Answer object
    :return: Discrepancy (float) of answer
    """
    ratings = list(answer.ratings.values())
    ratings = np.array([r for r in ratings if r is not None])
    return float(ratings.std())


def get_all_discrepancies(answers):
    """Get the discrepancy (standard deviation of ratings across languages) for aggregated answers (same question+settings asked several times)

    :param answers: Answer objects
    :return: Discrepancy (float) of aggregated answers
    """
    means = []
    for language in answers[0].answers:
        ratings = [answer.ratings[language] for answer in answers]
        ratings = [r for r in ratings if r is not None]
        if ratings:
            means.append(np.mean(ratings))
    return np.array(means).std() if means else None


def get_cleaned_discrepancies(answers):
    """Get the discrepancy (standard deviation of ratings across languages) for aggregated answers (same question+settings asked several times)

    :param answers: Answer objects
    :return: Discrepancy (float) of aggregated answers
    """
    means = []
    for language in answers[0].answers:
        ratings = [answer.ratings[language] for answer in answers]
        ratings = [r for r in ratings if (r is not None and int(r) != 5)]
        if ratings:
            means.append(np.mean(ratings))
    return np.array(means).std() if means else None


def get_refusal_ratio(answers):
    """Get the refusal ratio (ratio of ratings of 5) for aggregated answers (same question+settings asked several times)
    :param answers: Answer objects
    :return: Ratio of refused answers
    """
    refusal_ratios = []
    languages = answers[0].answers
    for language in languages:
        ratings = [answer.ratings[language] for answer in answers]
        ratings = [r for r in ratings if r is not None]
        if ratings:
            refusal_ratios.append(ratings.count(5) / len(ratings))
    return np.mean(refusal_ratios) if refusal_ratios else 0


def get_average_discrepancy(all_discrepancies: dict):
    avery_discrepancy_list = list(all_discrepancies.values())
    avery_discrepancy_list = [d for d in avery_discrepancy_list if d is not None]
    average_discrepancy = np.array(avery_discrepancy_list).std()
    return average_discrepancy


def get_average_refusal_rate(all_refusal_ratios: dict):
    average_refusal_list = list(all_refusal_ratios.values())
    average_refusal_list = [d for d in average_refusal_list if d is not None]
    average_refusal_ratio = np.array(average_refusal_list).mean()
    return average_refusal_ratio


def get_language_refusal_rate(answers):
    language_refusals = {}
    languages = answers[0].answers
    for language in languages:
        ratings = [answer.ratings[language] for answer in answers]
        ratings = [r for r in ratings if r is not None]
        if ratings:
            language_refusals[language] = ratings.count(5) / len(ratings)

    return language_refusals


def get_cleaned_language_std(answers):
    language_stds = {}
    languages = answers[0].answers
    for language in languages:
        ratings = [answer.ratings[language] for answer in answers]
        ratings = [r for r in ratings if (r is not None and int(r) != 5)]
        if ratings:
            language_stds[language] = np.sqrt(((np.array(ratings)-5.)**2).mean())
    return language_stds


def get_language_std(answers):
    language_stds = {}
    languages = answers[0].answers
    for language in languages:
        ratings = [answer.ratings[language] for answer in answers]
        ratings = [r for r in ratings if r is not None]
        if ratings:
            language_stds[language] = np.sqrt(((np.array(ratings)-5.)**2).mean())
    return language_stds