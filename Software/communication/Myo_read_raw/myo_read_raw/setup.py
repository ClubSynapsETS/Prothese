import setuptools

setuptools.setup(
    name="myo_read_raw",
    version="1.0",
    author="David Olivier and Zacharie Bolduc",
    author_email='david.olivier404@gmail.com',
    url='http://github.com/ClubSynapseETS/Prothese',
    description="Data acquisition for the myo via bluetooth",
    long_description="This module contains functionalities for pulling raw data from the myo.\
                      The raw data is unfiltered and relayed directly to the calling process.\
                      The buffer by which the data is received, is of variable size.",
    content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: Linux",
    ],
)
