from setuptools import setup, find_packages

setup(
    name="llm-git-commits",
    version="1.1.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "llm-git-commits=llm_git_commits.main:main",
        ],
    },
    author="Slipstream",
    author_email="me@slipstreamm.dev",
    description="Intelligent Git Commit Tool with LLM Integration",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Slipstreamm/llm-git-commits",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
