import argparse
import asyncio
import os

from joblib import Memory
from sqlalchemy.orm import Session

from llm_values.models import engine, Topic, Answer
from llm_values.pipeline.step_1_translate_prompts import translate_task
from llm_values.utils.gpt import GPT
from llm_values.utils.llm_cost import estimate_cost
from llm_values.utils.prompts import get_prefix, get_format_rating, get_format_order, get_language_prompt
from llm_values.utils.utils import load_json_file, extract_rating

cache_dir = ".cache/formats/"
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
memory = Memory(cache_dir, verbose=0)

llm = GPT()


async def api_call(
        new_answer, language
):
    instruction = new_answer.prefixes[language] + new_answer.formats[language]
    question = new_answer.prompts[language]
    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": question}
    ]

    response = llm._create_conversation_completion(
        model=new_answer.model,
        conversation=messages,
        json_mode=False,
        temperature=float(new_answer.temperature),
        # max_tokens=new_answer.max_tokens  # --> do not really apply max_tokens to not cut off answer
    )

    return response.choices[0].message.content


async def api_call_test(
        **kwargs
):
    return "test [[5]]"


async def query_task(
        new_answer, languages
):
    language_tasks = [api_call(new_answer, language) for language in languages]
    results = await asyncio.gather(*language_tasks, return_exceptions=True)
    ratings = {}
    answers = {}
    for result, language in zip(results, languages):
        ratings[language] = extract_rating(result)
        answers[language] = result
    new_answer.ratings = ratings
    new_answer.answers = answers

    return new_answer


@memory.cache
async def prepare_formats(
        rating_last: bool, question_english: bool, answer_english: bool, max_tokens: int, languages: list[str], mode: str
) -> tuple[dict[str, str], ...]:
    """Prepare the prompt prefixes (settings-independent) and formats (settings-dependent) for the LLM query
    :param rating_last: If rating should come after explanation
    :param question_english: If question should be asked in English
    :param answer_english: If answer should be given in English
    :param max_tokens: Max token of response
    :param languages: List of target languages
    :param mode: Mode of the topic, one of priorities/values/claims
    :return: Translated prefixes and formats
    """

    prefix_english = get_prefix()
    rating_format_english = get_format_rating(mode=mode)
    order_format_english = get_format_order(max_tokens=max_tokens, rating_last=rating_last)
    language_format_english = get_language_prompt("English") if answer_english else get_language_prompt()

    if question_english:
        prefixes = {language: prefix_english for language in languages}
        rating_formats = {language: rating_format_english for language in languages}
        order_formats = {language: order_format_english for language in languages}
        language_formats = {language: get_language_prompt(language) for language in languages}
        total_formats = {language: rating_formats[language] + order_formats[language] + language_formats[language]
                         for language in languages}
        prefixes_retranslated = {language: "" for language in languages}
        formats_retranslated = {language: "" for language in languages}
    else:
        prefix_task = translate_task(prefix_english, languages, source="English", model="gpt-4o-2024-05-13")
        rating_format_task = translate_task(rating_format_english, languages, source="English",
                                            model="gpt-4o-2024-05-13")
        order_format_task = translate_task(order_format_english, languages, source="English",
                                           model="gpt-4o-2024-05-13")
        language_format_task = translate_task(language_format_english, languages, source="English",
                                              model="gpt-4o-2024-05-13")
        [prefixes, rating_formats, order_formats, language_formats] = await asyncio.gather(
            prefix_task, rating_format_task, order_format_task, language_format_task)

        total_formats = {language: rating_formats[language] + order_formats[language] + language_formats[language]
                         for language in languages}

        prefixes_retranslated_tasks = [translate_task(prefix, ["English"], source=lang, model="gpt-4o-2024-05-13")
                                       for lang, prefix in prefixes.items()]
        prefixes_retranslated = {lang: result["English"]
                                 for lang, result in zip(languages, await asyncio.gather(*prefixes_retranslated_tasks))}
        formats_retranslated_tasks = [translate_task(form, ["English"], source=lang, model="gpt-4o-2024-05-13")
                                      for lang, form in total_formats.items()]
        formats_retranslated = {lang: result["English"]
                                for lang, result in zip(languages, await asyncio.gather(*formats_retranslated_tasks))}

    return prefixes, total_formats, prefixes_retranslated, formats_retranslated


async def query_llms(
        topic: str,
        model: str,
        num_queries: int = 3,
        temperature: float = 0,
        max_tokens: int = 100,
        rating_last: bool = False,
        answer_english: bool = False,
        question_english: bool = False,
        testing: bool = False,
        overwrite: bool = False,
        budget: float = 0.1
):
    """Query LLMs for answers to questions for different languages + models and given settings

    :param topic: Topic / dataset name
    :param model: LLM model to query
    :param num_queries: Number of repeated questions (with exact same settings)
    :param temperature: Temperature for LLM
    :param max_tokens: Max tokens for LLM response
    :param rating_last: If rating should come after explanation
    :param question_english: If question should be asked in English
    :param answer_english: If answer should be given in English
    :param testing: Testing mode (reduced number of questions and models)
    :param overwrite: Whether to overwrite previous answers (otherwise skip existing answers)
    :param budget: Budget for LLM calls. Get warning if exceeded
    """
    if question_english and answer_english:
        raise ValueError("Both question and answer cannot be in English")

    languages = load_json_file('languages.json')  # assuming models are stored in a list

    with Session(engine) as session:
        # Load questions and existing answers
        topic_object = session.query(Topic).filter(Topic.name == topic).first()
        if not topic_object:
            topic_object = session.query(Topic).filter(Topic.filename == topic).first()
        if not topic_object:
            raise ValueError(f"Topic '{topic}' not found in database.")

        questions = topic_object.questions

    # Reduced testing mode
    if testing:
        questions = questions[:1]
        num_queries = 1

    # Estimate total query cost
    prefixes, total_formats, prefixes_retranslated, formats_retranslated = await prepare_formats(
        rating_last, question_english, answer_english, max_tokens, languages, mode=questions[0].mode
    )
    all_strings = [value for q in questions for key, value in q.translations.items()]
    all_strings += [value for _ in questions for key, value in prefixes.items()]
    all_strings += [value for _ in questions for key, value in total_formats.items()]
    estimate_cost(
        all_strings,
        multiplier=num_queries,
        model=model,
        max_token=max_tokens,
        budget=budget
    )

    # Loop each question
    for j, question in enumerate(questions):
        print(f"QUESTION {question}")

        # Prepare option-dependent prefix and format
        prefixes, total_formats, prefixes_retranslated, formats_retranslated = await prepare_formats(
            rating_last, question_english, answer_english, max_tokens, languages, mode=question.mode
        )
        with Session(engine) as session:
            # Check if answers already exists
            answers = session.query(Answer).filter(
                Answer.topic_id == topic_object.id,
                Answer.question_id == question.id,
                Answer.model == model,
                Answer.temperature == temperature,
                Answer.max_tokens == max_tokens,
                Answer.rating_last == rating_last,
                Answer.answer_english == answer_english,
                Answer.question_english == question_english
            ).all()

            if answers:
                if overwrite:
                    for answer in answers:
                        session.delete(answer)
                    session.commit()
                else:
                    continue

        # Loop each iteration
        query_tasks = []
        for _ in range(num_queries):
            if question_english:
                prompts = {language: question.translations["English"] for language in languages}
            else:
                prompts = question.translations

            new_answer = Answer(
                prompts=prompts,
                prefixes=prefixes,
                formats=total_formats,
                prefixes_retranslated=prefixes_retranslated,
                formats_retranslated=formats_retranslated,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                rating_last=rating_last,
                answer_english=answer_english,
                question_english=question_english,
                question_id=question.id,
                topic_id=topic_object.id
            )

            query_tasks.append(query_task(new_answer, languages))

        results = await asyncio.gather(*query_tasks, return_exceptions=True)

        with Session(engine) as session:
            for result in results:
                session.add(result)
                session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate questions into multiple languages.")
    parser.add_argument("--topic", default="un_global_issues", help="name of the topic in llm_values/data/resources")
    parser.add_argument("--model", default="gpt-4o-2024-05-13", help="LLM model to query")
    parser.add_argument("--temperature", default=0.0, help="name of the topic in llm_values/resources")
    parser.add_argument("--max_tokens", default=100, help="max token for response (+20% will be added to be safe)")
    parser.add_argument("--num_queries", default=3, help="How often each question should be repeated")
    parser.add_argument("--question_english", action="store_true", default=False,
                        help="Ask the question in English (but answer in target language)")
    parser.add_argument("--answer_english", action="store_true", default=False,
                        help="Get answer in English (but ask question in target language)")
    parser.add_argument("--rating_last", action="store_true", default=False,
                        help="Rating after explanation (chain of thought)")
    parser.add_argument("--testing", action="store_true", default=False, help="Run the script in testing mode")
    parser.add_argument("--budget", default=0.1,
                        help="How much you want to spend on LLM calls (get a warning if budget is exceeded)")
    args = parser.parse_args()
    asyncio.run(query_llms(**args.__dict__))
