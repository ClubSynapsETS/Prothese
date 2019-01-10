# Myo_read_multi

# Features
    - Acquires raw data from the myo and fills buffer (numpy.array) with movement segments.
    
    - This module is a modified version of the "myo_read_raw" module. 
      It is optimized to feed data from the myo arm band to multiple clients on the redis side.
    
    - The number of clients is specified upon initialization of the connection. 
      Clients are ment to be seperate processes.
    
    - The feeding of data to the clients is done in a pipeline formation. 
      The first client is one reading ahead of the second which in turn is one reading ahead of the third and so on.

    - The raw data is unfiltered and relayed directly to the calling process.

# System requirements
    - linux (ubuntu)
    - Python3.6
    - pip3
    - redis server (sudo apt-get install redis-server)

# Installing python requirements
    - pip3 install -r requirements.txt
    
# Installing the Myo_read_raw package
    - Copy the "myo_read_multi" folder next to the "exemple.py" file
    - Paste the folder in the wanted location (ex : Downloaded modules folder) 
    - From the command line, navigate to the pasted folder
    - pip3 install --user -e myo_read_raw