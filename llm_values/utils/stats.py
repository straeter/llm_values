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
    return ratings.std()


def get_all_discrepancies(answers):
    """Get the discrepancy (standard deviation of ratings across languages) for aggregated answers (same question+settings asked several times)

    :param answers: Answer objects
    :return: Discrepancy (float) of aggregated answers
    """
    means = []
    for language in answers[0].answers:
        ratings = [answer.ratings[language] for answer in answers]
        ratings = [r if r is not None else 0 for r in ratings]
        means.append(np.mean(ratings))
    return np.array(means).std()



