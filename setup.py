import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="bargtd",
    version="0.0.1a1",
    author="LI Daobing",
    author_email="lidaobing@gmail.com",
    description="A GTD tool in the titlebar",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lidaobing/bargtd",
    packages=setuptools.find_packages(),
    scripts=['bin/bargtd'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
