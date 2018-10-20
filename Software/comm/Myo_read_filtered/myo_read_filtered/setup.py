import setuptools

setuptools.setup(
    name="myo_read_filtered",
    version="1.0",
    author="David Olivier, Zacharie Bolduc",
    description="Data acquisition for the myo via bluetooth",
    long_description="This module contains functionalities for pulling raw data from the myo.\
                      The raw data is filtered to across all 8 chanels (8 sensors).\
                      A threshold is applied on all 8 channels at once.\
                      For a piece of data to be part of movement, all 8 values must be higher then the given threshold value.\
                      The tresh value is applied to a RMS (computed on N consecutive data instances)",
    content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: Linux",
    ],
)
