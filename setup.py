from setuptools import find_packages, setup

setup(
    name="wahoo",
    version="1.0.0",
    packages=find_packages(exclude=("tests",)),
    install_requires=[
        "bittensor>=7.0.0",
        "httpx>=0.25.0",
        "torch>=2.0.0",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.10",
)
