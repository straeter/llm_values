import argparse
import json

from sqlalchemy.orm import Session

from llm_values.models import engine, Topic, Answer, Question


def data_to_json(topic: str, filename: str):
    """Convert data (answers joined with questions) from database to JSON file.
    :param topic: Name of the topic / dataset to load.
    :param filename: Name of the output json file
    """
    with Session(engine) as session:
        topic_object = session.query(Topic).filter(Topic.name == topic).first()
        if not topic_object:
            topic_object = session.query(Topic).filter(Topic.filename == topic).first()
        if not topic_object:
            raise ValueError(f"Topic '{topic}' not found in database.")
        answers = session.query(Answer).filter(
            Answer.topic_id == topic_object.id,
        ).join(Question).all()
        answers_json = []
        for answer in answers:
            answer_dict = answer.dict()
            answer_dict["question"] = answer.question.dict()
            answers_json.append(answer_dict)

        with open(filename, "w") as f:
            json.dump(answers_json, f, indent=4, default=str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate questions into multiple languages.")
    parser.add_argument("--topic", default="un_global_issues", help="name of the topic in llm_values/data/resources")
    parser.add_argument("--filename", default="data.json", help="name of output file")
    args = parser.parse_args()

    data_to_json(args.topic, args.filename)
