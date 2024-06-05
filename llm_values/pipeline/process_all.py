import argparse
import asyncio

from llm_values.pipeline.step_0_prepare_prompts import prepare_prompts
from llm_values.pipeline.step_1_translate_prompts import translate_prompts
from llm_values.pipeline.step_2_query_llms import query_llms
from llm_values.pipeline.step_3_translate_answers import translate_answers


async def main(
        topic: str,
        model: str,
        description: str,
        mode: str,
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
    await prepare_prompts(topic=topic, description=description, mode=mode)
    await translate_prompts(topic=topic, testing=testing)
    await query_llms(topic=topic, num_queries=num_queries, temperature=temperature, max_tokens=max_tokens,
                     rating_last=rating_last, answer_english=answer_english, question_english=question_english,
                     testing=testing, budget=budget)
    await translate_answers(topic=topic, testing=testing, overwrite=overwrite)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess priorities into questions.")
    parser.add_argument("--topic", default="un_global_issues", help="Name of the topic")
    parser.add_argument("--model", default="gpt-4o-2024-05-13", help="LLM model to query")
    parser.add_argument("--description", default="", help="Description of the topic")
    parser.add_argument("--mode", default="priorities", help="Mode of the topic, one of priorities/values/claims")
    parser.add_argument("--temperature", default=0.0, help="name of the topic in llm_values/data/resources")
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

    asyncio.run(main(**args.__dict__))
