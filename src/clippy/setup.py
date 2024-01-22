from setuptools import setup, find_packages

# NOT SURE IF I NEED THIS AS USING PDM AND JUST WANT MONOREPO WITH MULTIPLE PACKAGES
setup(
    name="clippy",
    version="0.1.0",
    packages=find_packages(include=["clippy"]),
)
