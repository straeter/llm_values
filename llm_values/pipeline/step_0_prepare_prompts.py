import argparse
import asyncio

from sqlalchemy.orm import Session

from llm_values.models import engine, Topic, Question
from llm_values.utils.prompts import get_prompt
from llm_values.utils.utils import load_json_file


async def add_questions(items: list[dict[str, str]], topic: str, description: str, mode: str):
    """Add questions to the database.

    :param topic: Topic / dataset name
    :param description: Description of topic (optional)
    :param mode: Mode, one of priorities/values/claims
    """

    with Session(engine) as session:

        topic_object = session.query(Topic).filter(Topic.name == topic).first()

        if not topic_object:
            topic_object = Topic(name=topic, description=description)
            session.add(topic_object)
            session.commit()

        existing_questions = [itm.name for itm in topic_object.questions]

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
                mode=question_mode
            )
            session.add(new_question)
        session.commit()


async def prepare_prompts(topic: str, description: str, mode: str):
    """Load questions from file and add to database.

    :param topic: Topic / dataset name
    :param description: Description of topic (optional)
    :param mode: Mode, one of priorities/values/claims
    """

    items = load_json_file(f"{topic}.json", "resources")

    await add_questions(items, topic, description, mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess priorities into questions.")
    parser.add_argument("--topic", default="un_global_issues", help="Name of the topic")
    parser.add_argument("--description", default="", help="Description of the topic")
    parser.add_argument("--mode", default="priorities", help="Mode of the topic, one of priorities/values/claims")
    args = parser.parse_args()

    asyncio.run(prepare_prompts(topic=args.topic, description=args.description, mode=args.mode))

