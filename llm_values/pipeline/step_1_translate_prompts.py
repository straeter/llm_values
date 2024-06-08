import argparse
import asyncio

from sqlalchemy.orm import Session

from llm_values.models import engine, Topic
from llm_values.utils.gpt import GPT
from llm_values.utils.llm_cost import estimate_cost
from llm_values.utils.translate import translate_task
from llm_values.utils.utils import load_json_file

llm = GPT()


async def translate_all(questions: list, languages: list[str]):
    tasks = [translate_task(
        question.question,
        languages,
        source="English",
    ) for question in questions]
    translated_questions = await asyncio.gather(*tasks)

    for question, translations in zip(questions, translated_questions):
        question.translations = translations

    # Re-translations
    for question in questions:
        re_tasks = [translate_task(
            question.translations[language],
            languages=["English"],
            source=language,
        ) for language in
            languages]
        retranslated_questions = await asyncio.gather(*re_tasks)
        question.re_translations = {}
        for language, retranslation in zip(languages, retranslated_questions):
            question.re_translations[language] = retranslation["English"]

    return questions


async def translate_prompts(topic: str, testing=False):
    """Translate and re-translate prompts into target languages

    :param topic: Topic / dataset name
    :param testing: Testing mode (reduced number of questions and models)
    """

    languages = load_json_file('languages.json')

    with Session(engine) as session:
        topic_object = session.query(Topic).filter(Topic.name == topic).first()
        if not topic_object:
            topic_object = session.query(Topic).filter(Topic.filename == topic).first()
        questions = topic_object.questions

    if testing:
        questions = questions[:1]

    estimate_cost([q.question for q in questions], multiplier=2 * len(languages))

    translated_questions = await translate_all(questions, languages)

    with Session(engine) as session:

        for question in translated_questions:
            session.add(question)
        session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate questions into multiple languages.")
    parser.add_argument("--topic", default="un_global_issues", help="name of the topic in llm_values/resources/")
    parser.add_argument("--testing", action="store_true", default=False, help="Run the script in testing mode")
    args = parser.parse_args()

    asyncio.run(translate_prompts(args.topic, testing=args.testing))
