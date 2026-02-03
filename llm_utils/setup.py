from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="llm-utils",
    version="0.1.0",
    author="Richard Kerr",
    author_email="rkerr@example.com",
    description="Battle-tested utilities for working with LLM APIs in production",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/datasciencedoc/llm-utils",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Core dependencies only - no heavy requirements
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.0.0",
            "mypy>=1.0.0",
        ],
        "api": [
            "requests>=2.28.0",
            "ratelimit>=2.2.1",
            "backoff>=2.2.1",
        ],
    },
    keywords="llm, json, api, openai, anthropic, claude, gpt, utilities, production",
    project_urls={
        "Bug Reports": "https://github.com/datasciencedoc/llm-utils/issues",
        "Source": "https://github.com/datasciencedoc/llm-utils",
    },
)
