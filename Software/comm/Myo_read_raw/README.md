# Myo_read_raw

# Features
    - Acquires raw data from the myo and fills buffer (numpy.array) with movement segments.
    - The raw data is unfiltered and relayed directly to the calling process.
    
# System requirements
    - linux (ubuntu)
    - Python3.6
    - pip3
    - redis server (sudo apt-get install redis-server)

# Installing python requirements
    - pip3 install -r requirements.txt
    
# Installing the Myo_read_raw package
    - Copy the "myo_read_raw" folder next to the "exemple.py" file
    - Paste the folder in the wanted location (ex : Downloaded modules folder) 
    - From the command line, navigate to the pasted folder
    - pip3 install -e myo_read_raw