import argparse
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from llm_values.models import engine, Topic, Answer, Setup
from llm_values.utils.stats import get_question_discrepancy, get_cleaned_question_discrepancy, \
    get_average, get_language_failure_rate, get_language_refusal_rate, get_language_assertiveness, \
    get_cleaned_language_assertiveness, get_refusal_rates, get_failure_rates, get_question_assertiveness, \
    get_language_means, get_language_std
from llm_values.utils.utils import load_json_file


def add_setups():
    all_setups = load_json_file("setups.json", "data")

    with Session(engine) as session:

        topics = session.query(Topic).all()

        for setup, params in all_setups.items():
            for topic in params.get("topics", []):
                topic_object = [tp for tp in topics if (tp.name == topic or tp.filename == topic)][0]

                setup_dict = {k: v for k, v in params.items() if k != "topics"}
                setup_object = session.query(Setup).filter_by(topic_id=topic_object.id, **setup_dict).first()
                if setup_object is None:
                    setup_object = Setup(
                        topic_id=topic_object.id,
                        name=setup,
                        **setup_dict
                    )
                    session.add(setup_object)
                    session.commit()
                    print(f"Added setup {setup} for topic {topic_object.name}")


async def calc_stats(topic_object, params: dict):
    all_stats = {}
    with Session(engine) as session:
        # Load answers
        questions = topic_object.questions
        results = session.query(Answer).filter_by(**params).all()

        try:
            question_discrepancies = {}
            question_cleaned_discrepancies = {}
            question_assertivenesses = {}
            question_refusal_rates = {}
            question_failure_rates = {}
            question_language_means = {}
            question_language_std = {}
            for question in questions:
                aggregated_answers = [answer for answer in results if answer.question_id == question.id]
                question_language_means[question.number] = get_language_means(aggregated_answers)
                question_language_std[question.number] = get_language_std(aggregated_answers)
                question_discrepancies[question.number] = get_question_discrepancy(aggregated_answers)
                question_cleaned_discrepancies[question.number] = get_cleaned_question_discrepancy(aggregated_answers)
                question_assertivenesses[question.number] = get_question_assertiveness(aggregated_answers)
                question_refusal_rates[question.number] = get_refusal_rates(aggregated_answers)
                question_failure_rates[question.number] = get_failure_rates(aggregated_answers)

            all_stats["discrepancies"] = question_discrepancies
            all_stats["cleaned_discrepancies"] = question_cleaned_discrepancies
            all_stats["assertivenesses"] = question_assertivenesses
            all_stats["refusal_rates"] = question_refusal_rates
            all_stats["failure_rates"] = question_failure_rates

            all_stats["dataset_discrepancy"] = get_average(question_discrepancies)
            all_stats["cleaned_dataset_discrepancy"] = get_average(question_cleaned_discrepancies)
            all_stats["dataset_assertiveness"] = get_average(question_assertivenesses)
            all_stats["refusal_rate"] = get_average(question_refusal_rates)
            all_stats["failure_rate"] = get_average(question_failure_rates)

            all_stats["language_means"] = question_language_means
            all_stats["language_std"] = question_language_std
            all_stats["language_refusal_rate"] = get_language_refusal_rate(results)
            all_stats["language_failure_rate"] = get_language_failure_rate(results)
            all_stats["language_assertiveness"] = get_language_assertiveness(results)
            all_stats["cleaned_language_assertiveness"] = get_cleaned_language_assertiveness(results)

        except Exception as e:
            print(e)
    return all_stats


async def analyze_results(setup_name: str):
    add_setups()

    with Session(engine) as session:
        if setup_name == "all" or not setup_name:
            setups = session.query(Setup).all()
        else:
            setups = session.query(Setup).filter_by(name=setup_name).all()

        topics = session.query(Topic).all()

        for setup in setups:
            print(f"Calculating stats for setup {setup.name}")
            topic = [topic for topic in topics if topic.id == setup.topic_id][0]
            params = setup.dict()
            [params.pop(key) for key in ["stats", "id", "name"]]
            all_stats = await calc_stats(topic, params)
            setup.stats = all_stats
            flag_modified(setup, "stats")
            session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calc discrepancies for setups.")
    parser.add_argument("--setup", default="A) default (rating first, temperature=0, gpt-4o)",
                        help="name of the setup in setups.json")
    args = parser.parse_args()

    asyncio.run(analyze_results(args.setup))
