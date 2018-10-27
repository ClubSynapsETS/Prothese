# Calibration_Pipeline

# Features
    - Normalizes input data according to input calibration file.
    - Data is centered according to the emg value associated with a relaxed pose.
    - Data is scaled according to emg value associated with maximum contraction.
    - Output data values are in the interval : [-1, 1].

# System requirements
    - Python3.6
    - pip3

# Installing python requirements
    - pip3 install -r requirements.txt
    
# Installing the Calibration_Pipeline package
    - Navigate to the "Calibration_Pipeline" folder
    - pip3 install -e Calibration_Pipeline