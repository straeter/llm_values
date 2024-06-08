import numpy as np
import streamlit as st
from sqlalchemy.orm import Session

from llm_values.models import engine, Topic, Answer
from llm_values.utils.utils import load_json_file
from llm_values.utils.visualize import get_plot_cached

st.set_page_config(layout="wide")


def get_discrepancy(answers):
    means = {}
    for language in answers[0].answers:
        ratings = [answer.ratings[language] for answer in answers]
        ratings = [r if r is not None else 0 for r in ratings]
        means[language] = np.mean(ratings)
    return max(list(means.values())) - min(list(means.values()))


def discrepancy_color(discrepancy):
    if discrepancy <= 1:
        return "green"
    elif discrepancy <= 2.5:
        return "orange"
    else:
        return "red"


def init_app():
    if not hasattr(st.session_state, 'initialized'):
        # st.session_state.data = {}
        st.session_state.initialized = True
        st.session_state.topic_object = None

        st.session_state.questions = {}
        st.session_state.question_names = []
        st.session_state.question_selected = None
        st.session_state.answers = []
        st.session_state.plot = None

        st.session_state.setups = load_json_file("setups.json")
        st.session_state.setup_selected = [value for key, value in st.session_state.setups.items()
                                           if key.startswith("default")][0]

        with Session(engine) as session:
            topics = session.query(Topic).all()
            st.session_state.topics = sorted([topic.name for topic in topics])
        st.session_state.topic_selected = None
        st.session_state.languages = load_json_file("languages.json")


def main():
    topics = st.session_state.topics
    languages = st.session_state.languages

    with st.sidebar:

        st.title("LLM Values")
        st.markdown('<h2><a href="https://github.com/straeter/llm_values" target="_blank">Github</a></h2>',
                    unsafe_allow_html=True)
        st.markdown(
            "__Explore how, dependent on the prompt language, different LLMs evaluate ethical statements, controversial claims and priorities.__")

        topic = st.selectbox("Choose a dataset:", topics, index=0, key="topic")

        if topic != st.session_state.topic_selected:
            print(f"REFETCH TOPIC {topic}")
            st.session_state.topic_selected = topic
            with Session(engine) as session:
                tobic_object = session.query(Topic).filter(Topic.name == topic).first()
                st.session_state.questions = {q.name: q for q in tobic_object.questions}
                st.session_state.question_names = [q.name for q in tobic_object.questions]
                st.session_state.topic_object = tobic_object
        tobic_object = st.session_state.topic_object
        st.markdown(tobic_object.description)

        question_name = st.selectbox(
            "Choose a question:",
            options=st.session_state.question_names,
            index=0,
            key="question_name",
            # format_func=lambda x: x + " - " + f"{get_discrepancy(st.session_state.questions.get(x)):.2f}",
        )
        question = st.session_state.questions.get(question_name) or {}

        setup = st.selectbox("Choose a setup:", list(st.session_state.setups.keys()), index=0, key="setup")

        translation = st.selectbox("Choose language", languages, index=1, key="translation")

    params = st.session_state.setups[setup]

    if st.session_state.question_selected != question or \
            setup != st.session_state.setup_selected:

        print(f"REFETCH ANSWERS FOR QUESTION: {question.name}")
        with Session(engine) as session:
            results = session.query(Answer).filter(
                Answer.topic_id == st.session_state.topic_object.id,
                Answer.question_id == question.id,
                Answer.model == params.get("model"),
                Answer.answer_english == params.get("answer_english"),
                Answer.question_english == params.get("question_english"),
                Answer.temperature == params.get("temperature"),
                Answer.rating_last == params.get("rating_last")
            ).all()

            st.session_state.answers = results
        if st.session_state.answers:
            st.session_state.plot = get_plot_cached(st.session_state.answers)
        st.session_state.question_selected = question
        st.session_state.setup_selected = setup

    answers = st.session_state.answers
    plot = st.session_state.plot

    if answers:  # -> could be empty list

        col_left, col_right = st.columns([3, 2])
        with col_left:
            st.title(f"{question_name}")
            discrepancy = get_discrepancy(answers)
            st.subheader(f"Discrepancy: :{discrepancy_color(discrepancy)}[{discrepancy:.2f}]")
            if plot:
                st.image(plot)

        with col_right:
            st.title("Prompt (English)", help="The LLM prompt (prefix + format + question) translated to English.")
            questions_tabs = st.tabs(["Question", "Prefix", "Format"])
            with questions_tabs[0]:
                st.markdown(question.question, help="The actual question / statement for the LLM to evaluate.")
            with questions_tabs[1]:
                st.markdown(answers[0].prefixes["English"],
                            help="The prefix to explain the LLM what this survey is about. Part of the system message.")
            with questions_tabs[2]:
                st.markdown(answers[0].formats["English"],
                            help="The format how the LLM should answer. Part of the system message.")

            st.title("Settings", help="The settings used for the LLM call.")
            parameter = f"""
            model = "{params.get("model")}"
            temperature = {params.get("temperature")}
            question_english = {params.get("question_english")}
            answer_english = {params.get("answer_english")}
            rating_last = {params.get("rating_last")}
            """
            st.code(parameter, language="python", line_numbers=False)

        col_l, col_r = st.columns([2, 2])

        with col_l:
            st.title("Prompt (Original)")

            translated_questions_tabs = st.tabs(["Question", "Prefix", "Format"])
            with translated_questions_tabs[0]:
                if translation:
                    col_q_left, col_q_right = st.columns(2)
                    with col_q_left:
                        st.subheader(f"Original Question ({translation})")
                        st.write(question.translations[translation])
                    with col_q_right:
                        st.subheader("Re-Translated Question")
                        if question.re_translations[translation]:
                            st.write(question.re_translations[translation])

            with translated_questions_tabs[1]:
                if translation:
                    col_q_left, col_q_right = st.columns(2)
                    with col_q_left:
                        st.subheader(f"Translated Prefix ({translation})")
                        st.write(answers[0].prefixes[translation])
                    with col_q_right:
                        st.subheader("Re-Translated Prefix")
                        if answers[0].prefixes_retranslated[translation]:
                            st.write(answers[0].prefixes_retranslated[translation])
            with translated_questions_tabs[2]:
                if translation:
                    col_q_left, col_q_right = st.columns(2)
                    with col_q_left:
                        st.subheader(f"Translated Format ({translation})")
                        st.write(answers[0].formats[translation])
                    with col_q_right:
                        st.subheader("Re-Translated Format")
                        if answers[0].formats_retranslated[translation]:
                            st.write(answers[0].formats_retranslated[translation])

        with col_r:

            n_answers = len(answers)

            st.title(f"Answers")
            answer_tabs = st.tabs([f"Answer {i + 1}" for i in range(n_answers)])
            for tab_idx in range(n_answers):
                with answer_tabs[tab_idx]:
                    col_a_left, col_a_right = st.columns(2)
                    with col_a_left:
                        st.subheader(f"Original Answer {tab_idx + 1} ({translation})")
                        st.write(answers[tab_idx].answers[translation])
                    with col_a_right:
                        st.subheader(f"Translated Answer {tab_idx + 1} (English)")
                        if answers[tab_idx].translations:
                            st.write(answers[tab_idx].translations.get(translation))

    else:
        st.title("No data found for these settings")


if __name__ == '__main__':
    init_app()

    main()
