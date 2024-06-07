import argparse
import asyncio

from sqlalchemy.orm import Session

from llm_values.models import engine, Topic, Answer
from llm_values.utils.gpt import GPT
from llm_values.utils.llm_cost import estimate_cost
from llm_values.utils.translate import translate_task

llm = GPT()


async def translate_single(answer: Answer):
    languages = list(answer.answers.keys())
    re_tasks = []
    for language in languages:
        s_language = "English" if answer.answer_english else language
        t_language = language if answer.answer_english else "English"
        re_tasks.append(translate_task(answer.answers.get(language), [t_language], source=s_language))

    translated_answers = await asyncio.gather(*re_tasks, return_exceptions=True)
    answer.translations = {lang: trans[lang] if answer.answer_english else trans["English"]
                           for lang, trans in zip(languages, translated_answers)}
    return answer


async def translate_answers(topic: str, testing=False, overwrite=False):
    """Translate answers back to English (or target language, if answer is given in English)

    :param topic: Topic / dataset name
    :param testing: Testing mode (reduced number of questions and models)
    :param overwrite: Whether to re-translate answers or keep existing translations
    """

    # Load answers
    with Session(engine) as session:
        topic_object = session.query(Topic).filter(Topic.name == topic).first()
        if not topic_object:
            topic_object = session.query(Topic).filter(Topic.filename == topic).first()
        answers = topic_object.answers

    if not overwrite:
        answers = [a for a in answers if not a.translations]

    if testing:
        answers = answers[:1]

    estimate_cost([value for q in answers for key, value in q.answers.items()])

    for answer in answers:
        translated_answer = await translate_single(answer)

        with Session(engine) as session:
            session.add(translated_answer)
            session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate answer back to English.")
    parser.add_argument("--topic", default="un_global_issues", help="name of the topic in llm_values/resources/")
    parser.add_argument("--testing", action="store_true", default=False, help="Run the script in testing mode")
    args = parser.parse_args()

    asyncio.run(translate_answers(args.topic, testing=args.testing))
