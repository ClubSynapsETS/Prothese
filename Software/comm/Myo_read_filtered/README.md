#Myo_read_filtered

# Features
    - Acquires raw data from the myo and fills buffer (numpy.array) with movement segments.
    - Raw data is filtered, before being inserted in the buffer. 
    - For a given piece of data, all 8 channels must exceed a certain threshold value to be considered part of a movement.
    
# System requirements
    - linux (ubuntu)
    - Python3.6
    - pip3
    - redis server (sudo apt-get install redis)

# Installing python requirements
    - pip3 install -r requirements.txt
    
# Installing the Myo_read_filtered package
    - Navigate to the "myo_read_filtered" folder
    - pip3 install -e myo_read_filtered