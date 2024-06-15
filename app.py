import streamlit as st
from sqlalchemy.orm import Session

from llm_values.models import engine, Topic, Answer, Setup
from llm_values.utils.utils import load_json_file
from llm_values.utils.visualize import get_plot_cached

st.set_page_config(layout="wide")
st.html("""<style>[alt=Logo] {height: 3rem;}</style>""")
st.logo("static/llm_values.jpg")


def discrepancy_color(discrepancy):
    if discrepancy <= 1:
        return "green"
    elif discrepancy <= 2.5:
        return "orange"
    else:
        return "red"


def question_mode(mode: str):
    if mode == "values":
        return "How much do you agree? (9=totally, 5=undecided, 1=not at all)"
    if mode == "claims":
        return "Do you think it is true? (9=absolutely true, 5=don't know, 1=absolutely wrong)"
    if mode == "priorities":
        return "How much resources should we spend? (9=much more, 5=same as now, 1=nothing)"


def init_app():
    if not hasattr(st.session_state, 'initialized'):
        # st.session_state.data = {}
        st.session_state.initialized = True
        st.session_state.topic_object = None

        st.session_state.questions = {}
        st.session_state.question_names = []
        st.session_state.question_selected = None
        st.session_state.answers = []
        st.session_state.discrepancies = {}
        st.session_state.plot = None

        # st.session_state.setups = load_json_file("setups.json")
        # st.session_state.setup_selected = [value for key, value in st.session_state.setups.items()
        #                                    if key.startswith("default")][0]

        with Session(engine) as session:
            st.session_state.setups = session.query(Setup).all()
            st.session_state.setup_selected = None
            st.session_state.topics = {tpc.name: tpc for tpc in session.query(Topic).all()}
            st.session_state.topic_selected = None

        st.session_state.languages = load_json_file("languages.json")


def main():
    languages = st.session_state.languages

    with st.sidebar:

        st.markdown(
            "<div style='font-weight: 600'>Explore how, dependent on the prompt language, different LLMs evaluate ethical statements, controversial claims and priorities. Code is on <a href='https://github.com/straeter/llm_values' target='_blank'>Github</a></div>",
            unsafe_allow_html=True
        )

        topics = sorted(list(st.session_state.topics.keys()))
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

        setup_list = sorted([stp.name for stp in st.session_state.setups
                             if tobic_object.id == stp.topic_id])
        setup_selected = st.selectbox("Choose a setup:", setup_list, index=0, key="setup")

        language = st.selectbox("Choose language", languages, index=1, key="language")

    setup = [stp for stp in st.session_state.setups if stp.name == setup_selected and tobic_object.id == stp.topic_id][0]

    if st.session_state.question_selected != question or setup_selected != st.session_state.setup_selected:

        print(f"REFETCH ANSWERS FOR QUESTION: {question.name}")
        with Session(engine) as session:
            results = session.query(Answer).filter(
                Answer.topic_id == st.session_state.topic_object.id,
                Answer.question_id == question.id,
                Answer.model == setup.model,
                Answer.answer_english == setup.answer_english,
                Answer.question_english == setup.question_english,
                Answer.temperature == setup.temperature,
                Answer.rating_last == setup.rating_last
            ).all()

            st.session_state.answers = results
        if st.session_state.answers:
            st.session_state.plot = get_plot_cached(st.session_state.answers)
        st.session_state.question_selected = question
        st.session_state.setup_selected = setup_selected

    answers = st.session_state.answers
    plot = st.session_state.plot

    if answers:  # -> could be empty list

        col_left, col_right = st.columns([3, 2])
        with col_left:
            st.header(question.description[:150])
            st.markdown(f"<h5>{question_mode(question.mode)}</h5>", unsafe_allow_html=True)
            if plot:
                st.image(plot)

                discrepancy = setup.stats["discrepancies"].get(str(question.number))
                st.markdown(f"<div style='color: {discrepancy_color(discrepancy)}'>discrepancy d_q = {discrepancy:.3f}</div>", unsafe_allow_html=True)
                refusal_rate = setup.stats["refusal_rates"].get(str(question.number))
                st.markdown(f"<div style='color: {discrepancy_color(refusal_rate*20)}'>refusal rate r_q = {refusal_rate:.3f}</div>", unsafe_allow_html=True)
                failure_rate = setup.stats["refusal_rates"].get(str(question.number))
                st.markdown(f"<div style='color: {discrepancy_color(refusal_rate*20)}'>refusal rate r_q = {refusal_rate:.3f}</div>", unsafe_allow_html=True)

        with col_right:
            st.header("Prompt (English)", help="The LLM prompt (prefix + format + question) translated to English.")
            questions_tabs = st.tabs(["Question", "Prefix", "Format"])
            with questions_tabs[0]:
                st.markdown(question.question, help="The actual question / statement for the LLM to evaluate.")
            with questions_tabs[1]:
                st.markdown(answers[0].prefixes["English"],
                            help="The prefix to explain the LLM what this survey is about. Part of the system message.")
            with questions_tabs[2]:
                st.markdown(answers[0].formats["English"],
                            help="The format how the LLM should answer. Part of the system message.")

            st.header("Settings", help="The settings used for the LLM call.")
            parameter = f"""
            model = "{setup.model}"
            temperature = {setup.temperature}
            question_english = {setup.question_english}
            answer_english = {setup.answer_english}
            rating_last = {setup.rating_last}
            """
            st.code(parameter, language="python", line_numbers=False)

            st.header("Dataset Metrics", help="Metrics calculated for this dataset and setup (see blog post).")
            stats = f"""
            dataset discrepancy d_s = {setup.stats.get("dataset_discrepancy"):.3f}
            cleaned dataset discrepancy d_c =  {setup.stats.get("cleaned_dataset_discrepancy"):.3f}
            refusal rate r_s =  {setup.stats.get("cleaned_dataset_discrepancy"):.3f}
            failure rate f_s =  {setup.stats.get("failure_rate"):.3f}
            """
            st.code(stats, language="python", line_numbers=False)

        translation = "English" if setup.question_english else language

        col_l, col_r = st.columns([2, 2])
        with col_l:
            st.header("Prompt (Original)")

            translated_questions_tabs = st.tabs(["Question", "Prefix", "Format"])
            with translated_questions_tabs[0]:
                if language:
                    col_q_left, col_q_right = st.columns(2)
                    with col_q_left:
                        st.subheader(f"Original Question ({translation})")
                        st.write(question.translations[translation])
                    with col_q_right:
                        st.subheader("Re-Translated Question")
                        if setup.question_english:
                            st.write(question.translations[language])
                        elif question.re_translations[translation]:
                            st.write(question.re_translations[translation])

            with translated_questions_tabs[1]:
                if language:
                    col_q_left, col_q_right = st.columns(2)
                    with col_q_left:
                        st.subheader(f"Translated Prefix ({language})")
                        st.write(answers[0].prefixes[language])
                    with col_q_right:
                        st.subheader("Re-Translated Prefix")
                        if answers[0].prefixes_retranslated[language]:
                            st.write(answers[0].prefixes_retranslated[language])
            with translated_questions_tabs[2]:
                if language:
                    col_q_left, col_q_right = st.columns(2)
                    with col_q_left:
                        st.subheader(f"Translated Format ({language})")
                        st.write(answers[0].formats[language])
                    with col_q_right:
                        st.subheader("Re-Translated Format")
                        if answers[0].formats_retranslated[language]:
                            st.write(answers[0].formats_retranslated[language])

        answer_translation = "English" if setup.answer_english else language
        answer_retranslation = language if setup.answer_english else "English"
        with col_r:
            n_answers = len(answers)

            st.header(f"Answers")
            answer_tabs = st.tabs([f"Answer {i + 1}" for i in range(n_answers)])
            for tab_idx in range(n_answers):
                with answer_tabs[tab_idx]:
                    col_a_left, col_a_right = st.columns(2)
                    with col_a_left:
                        st.subheader(f"Original Answer {tab_idx + 1} ({answer_translation})")
                        st.write(answers[tab_idx].answers[language])
                    with col_a_right:
                        st.subheader(f"Translated Answer {tab_idx + 1} ({answer_retranslation})")
                        if answers[tab_idx].translations:
                            st.write(answers[tab_idx].translations.get(language))

    else:
        st.title("No data found for these settings")


if __name__ == '__main__':
    init_app()

    main()
