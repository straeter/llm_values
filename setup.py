import setuptools
# read in the requirements from the requirements.txt file
with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="llm_values",
    version="1.0.0",
    author="Christoph Sträter",
    author_email="mail@christoph-straeter.com",
    description="Query language models for values and compare for different languages",
    long_description_content_type="text/markdown",
    url="https://github.com/straeter/llm_values",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.11',
)
