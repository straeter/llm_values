import argparse
import asyncio

from sqlalchemy.orm import Session

from llm_values.models import engine, Topic, Question
from llm_values.utils.prompts import get_prompt
from llm_values.utils.utils import load_json_file


async def add_questions(items: list[dict[str, str]], topic: str, filename: str, description: str, mode: str):
    """Add questions to the database.

    :param items: List of questions / statements
    :param topic: Topic / dataset name
    :param filename: Filename of dataset
    :param description: Description of topic (optional)
    :param mode: Mode, one of priorities/values/claims
    """

    with Session(engine) as session:

        topic_object = session.query(Topic).filter(Topic.name == topic).first()
        if not topic_object:
            topic_object = session.query(Topic).filter(Topic.filename == topic).first()

        if not topic_object:
            topic_object = Topic(name=topic, description=description)
            session.add(topic_object)
            session.commit()

        existing_questions = [itm.name for itm in topic_object.questions]
        max_number = max([q.number for q in topic_object.questions]) if existing_questions else 0

        for j, item in enumerate(items):
            if item["name"] in existing_questions:
                continue
            question_mode = item.get("mode", mode)
            question = get_prompt(item["name"], item["description"], question_mode)
            new_question = Question(
                name=item["name"],
                description=item["description"],
                question=question,
                topic_id=topic_object.id,
                mode=question_mode,
                number=j+1+max_number
            )
            session.add(new_question)
        session.commit()


async def prepare_prompts(topic: str, description: str, mode: str):
    """Load questions from file and add to database.

    :param topic: Topic / dataset name
    :param description: Description of topic (optional)
    :param mode: Mode, one of priorities/values/claims
    """

    topic_json = load_json_file(f"{topic}.json", "resources")
    topic_name = topic_json.get("name", topic)
    filename = topic_json.get("filename", topic)
    topic_description = topic_json.get("description", description)
    topic_mode = topic_json.get("mode", mode)
    topic_items = topic_json.get("questions")
    topic_items_sorted = sorted(topic_items, key=lambda x: x["name"])

    await add_questions(topic_items_sorted, topic_name, filename, topic_description, topic_mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess priorities into questions.")
    parser.add_argument("--topic", default="", help="Name of the topic")
    parser.add_argument("--description", default="", help="Description of the topic")
    parser.add_argument("--mode", default="", help="Mode of the topic, one of priorities/values/claims")
    args = parser.parse_args()

    asyncio.run(prepare_prompts(topic=args.topic, description=args.description, mode=args.mode))

