import argparse
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from llm_values.models import engine, Topic, Answer, Setup
from llm_values.utils.stats import get_all_discrepancies, get_cleaned_discrepancies, get_refusal_ratio, \
    get_average_discrepancy, get_average_refusal_rate, get_language_refusal_rate, get_language_std, \
    get_cleaned_language_std
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
            all_discrepancies = {}
            all_cleaned_discrepancies = {}
            all_refusal_ratios = {}
            for question in questions:
                aggregated_answers = [answer for answer in results if answer.question_id == question.id]
                all_discrepancies[question.number] = get_all_discrepancies(aggregated_answers)
                all_cleaned_discrepancies[question.number] = get_cleaned_discrepancies(aggregated_answers)
                all_refusal_ratios[question.number] = get_refusal_ratio(aggregated_answers)

            all_stats["discrepancies"] = all_discrepancies
            all_stats["cleaned_discrepancies"] = all_cleaned_discrepancies
            all_stats["refusal_ratios"] = all_refusal_ratios

            all_stats["topic_discrepancy"] = get_average_discrepancy(all_discrepancies)
            all_stats["clean_topic_discrepancy"] = get_average_discrepancy(
                all_cleaned_discrepancies)
            all_stats["refusal_ratio"] = get_average_refusal_rate(all_refusal_ratios)

            all_stats["language_refusal_rate"] = get_language_refusal_rate(results)
            all_stats["language_std"] = get_language_std(results)
            all_stats["cleaned_language_std"] = get_cleaned_language_std(results)
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
            topic = [topic for topic in topics if topic.id == setup.topic_id][0]
            params = setup.dict()
            [params.pop(key) for key in ["stats", "id", "name"]]
            all_stats = await calc_stats(topic, params)
            setup.stats = all_stats
            flag_modified(setup, "stats")
            session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calc discrepancies for setups.")
    parser.add_argument("--setup", default="default (rating first, temperature=0, gpt-4o)",
                        help="name of the setup in setups.json")
    args = parser.parse_args()

    asyncio.run(analyze_results(args.setup))
