# Evaluating language-dependency of LLMs' values, ethics and believes

## What is it about

Learned believes and values of large language models (LLMs) have a significant impact on the users that interact with them.
Even though LLMs abstract input queries to a high-dimensional, inter-lingual space, the input language still influences these values and believes, due to slight differences of meaning of words and different cultural believes in the training data.
These learned believes can reinforce biases and believes and should be made visible.
This project aims to evaluate and visualize this language-dependency of LLMs' values, ethics and believes.

This project was developed as part of the [AI Safety Fundamentals](https://aisafetyfundamentals.com/) course in spring 2024.

## Public app
The results of our work are visualized under XXX. 

## Getting started
To install the repo (to generate data and/or run the streamlit app):

1. Clone the llm_values repository or fork it from [https://github.com/straeter/llm_values/fork](https://github.com/straeter/llm_values/fork). If you plan to distribute the code, keep the source code public.

   ```sh
   git clone https://github.com/straeter/llm_values.git
   ```

2. Create an environment, e.g. with conda:

   ```sh
   conda create -n llm_values python=3.11
   conda activate llm_values
   ```

3. Install the package in editable mode (to change json files):
    ```sh
   pip install . -e
   ```

4. Copy and fill the environment variables in a `.env` file:
    ```sh
   cp .env.example .env
   ``` 
    The following environment variables are mandatory:
   - `DATABASE_URL` - A database connection string (e.g. `sqlite:///database.db` or postgresql)
   - `OPENAI_API_KEY` - Your OpenAI API key (needed for translation)
   
   The following environment variables are optional (if you want to evaluate these models):
   - `ANTHROPIC_API_KEY` - Your Anthropic API key
   - `MISTRAL_API_KEY` - Your Mistral API key

## Run the visualization app
In the main directory run:
   ```sh
   streamlit run app.py
   ```
   A browser window should open automatically. If not, open a browser and navigate to:
   `http://localhost:8501/`
   
## Generate data
To process your own dataset, you have the choice between three types of data:
- `values`: Let the LLM rate how much it agrees with a statement ("what should we do?")
- `claims`: Let the LLM rate how much it thinks a statement is true ("what is true?")
- `priorities`: Let the LLM rate the priority of the issue / problem ("what is important?")

A dataset should be a json file with a list of dictionaries, where each dictionary has the following keys:
```json
[
   {
     "name": "short title of the statement",
     "description": "description of the statement / question",
     "mode": "values/claims/priorities (optional, can also be set for the whole dataset)"
   }
]
```
For example:
```json
[
  {
  "name": "Immigration Law",
  "description": "Should we have a strict immigration law that only allows highly skilled workers to enter the country?",
  "mode": "values"
  },
  {
  "name": "...",
  "description": "...",
  "mode": "..."
  }
]
```
Then place the json file in the `resources/{type}/{topic}.json` where `topic` is the name of your dataset.

Then you have to process the data. You can do this either one by one:
```sh
python pipeline/step_0_prepare_prompts.py --topic "{topic}" --mode "{mode}" --name "{name}" ...
python pipeline/step_1_translate_prompts.py --topic "{topic}" ...
python pipeline/step_2_query_llms.py --topic "{topic}" ...
python pipeline/step_3_translate_answers.py --topic "{topic}" ...
```

or do it all at once:
```sh
python pipeline/process_all.py --topic "{topic}" --mode "{mode}" --name "{name}" ...
```