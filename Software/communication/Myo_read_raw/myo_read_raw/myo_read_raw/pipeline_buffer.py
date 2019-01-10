import pandas as pd
import numpy as np
import json

# importing myo bluetooth utilities
from time import sleep
from . import myo_raw
import sys

# importing multi processing utilities 
from multiprocessing import Process
import pickle
import redis

# defining the pipeline buffer size error
pipeline_buff_size = 25

# defining the amount of output sensors on the myo
n_incoming_sensors = 8

# defining inter-process communications
redis_db_id = 0 

# global containers (each process will fork these containers)
raw_incoming_data = np.zeros((8, 0))

# defining custom bluetooth exception (when connection fails)
class BluetoothFailedConnection(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


# Creates necessary variables for redis session
# Inputs : 
#   "r_server" : redis server connection instance
def init_redis_variables(r_server):

    # defining buffer maintenance flags
    r_server.set("buffer_ready", "0")
    r_server.set("raw_data_ready", "0")
    r_server.set("pose_data_ready", "0")

    # defining continuation flags
    r_server.set("read_from_myo", "1")
    r_server.set("buffer_maintained", "1")
    r_server.set("incoming_data", "1")

    # defining shared buffer containers
    r_server.set("raw_data", "")
    r_server.set("pipeline_buff", "")
    r_server.set("myo_pose", "")

    return r_server



# Resets proper maintenance flags when data is read in the client process
# Inputs :
#   r_server : redis server connection instance
def reset_pipeline_buff_flags(r_server):
    r_server.set("buffer_ready", "0")



# Creates a connected myo bluetooth object
# Inputs : 
#   r_server : redis server connection
def create_myo_connection(r_server):

    # creating a connection object
    connection_success = False
    n_tries = 20
    while(not connection_success):
        try:
            m = myo_raw.MyoRaw(sys.argv[1] if len(sys.argv) >= 2 else None)
            connection_success = True
        except ValueError:
            print("Myo dongle not found")
            n_tries -= 1
            sleep(1)
            if(n_tries == 0):
                raise BluetoothFailedConnection("Bluetooth connection failed")

    # defining the emg raw value handler
    def proc_emg(emg, moving, times=[]):

        global raw_incoming_data

        # appending incoming data to the raw data buffer
        emg_list = list(emg)
        raw_incoming_data = np.c_[raw_incoming_data, emg_list]

        # when raw data buffer reaches max size, transfering it to db
        if(raw_incoming_data.shape[1] == pipeline_buff_size):
            # parent process is ready for transfer
            if(r_server.get("raw_data_ready") == "0"):
                r_server.set("raw_data", json.dumps(raw_incoming_data.tolist()))
                raw_incoming_data = np.zeros((n_incoming_sensors, 0))
                r_server.set("raw_data_ready", "1")
            # making room for newer data, while waiting for parent
            else : raw_incoming_data = raw_incoming_data[ : , 5 : ]

    # defining the pose handler
    def proc_pose(pose):
        r_server.set("pose_data_ready", "1")
        r_server.set("myo_pose", str(pose.value))

    # attaching the handlers
    m.add_emg_handler(proc_emg)
    m.add_pose_handler(proc_pose)

    m.connect()
    print("myo connected")

    return m



# Extracts data from the a myo instance and fills the raw_data buffer
# This function is ment to be run a seperate process
# Inputs : 
#   conn_pool : connection pool for redis (server connections are made from connection pool)
def collect_myo_data(conn_pool):

    # creating redis for shared buffer objects
    r_server = redis.StrictRedis(connection_pool=conn_pool)

    # obtaining a connection to the myo
    try:
        myo_connection = create_myo_connection(r_server)
    except BluetoothFailedConnection :
        r_server.set("incoming_data", "0")
        print("Buffer maintenance thread aborted, failed to connect to myo")
        return 

    try :
        # pulling data from the myo
        while(r_server.get("read_from_myo") == "1"): 
            myo_connection.run(1)

    except :
        #trying to disconnect the myo
        try : myo_connection.disconnect()
        except : pass
        # telling parent processes that error occured
        r_server.set("incoming_data", "0")
        print("\nBuffer maintenance thread aborted, error while reading from myo")
        print("myo disconnected")



# Maintains the pipeline buffer, which forwards data from the myo
# This function is ment to be run a a seperate process
# Inputs : 
#   conn_pool : connection pool for redis (server connections are made from connection pool)
#   new_pipeline_buff_size : specifies a new value for the globally defined pipeline buffer
#   check_delay : time between data availability checks (in seconds)
def maintain_pipeline_buffer(conn_pool, new_pipeline_buff_size=None, check_delay=0.1):

    # changing the pipeline buffer size to a user defined value
    global pipeline_buff_size
    if new_pipeline_buff_size is not None : 
        pipeline_buff_size = new_pipeline_buff_size

    # creating redis connection for current process
    r_server = redis.StrictRedis(connection_pool=conn_pool)

    # launching data collecting thread
    data_collection_p = Process(target=collect_myo_data, args=(conn_pool,))
    data_collection_p.start()

    try:

        # as long as the program is receiving myo data
        while(r_server.get("incoming_data") == "1"):

            # buffer should take around 250 ms to fill (when pipeline_buff_size = 50)
            sleep(check_delay)

            # data is not currently available to parent process
            # and child process cant write to raw data buffer
            if(r_server.get("buffer_ready") == "0" and r_server.get("raw_data_ready") == "1"):

                # transfering the raw data buffer content to the pipeline buffer
                r_server.set("pipeline_buff", r_server.get("raw_data"))    
                r_server.set("buffer_ready", "1")
                
                # marking the raw data buffer as read
                r_server.set("raw_data", "")
                r_server.set("raw_data_ready", "0")

    except: pass

    # unsetting continuation flag for parent and child process
    r_server.set("buffer_maintained", "0")
    r_server.set("read_from_myo", "0")

    data_collection_p.join()



# Launches the buffer maintenance process and returns the handle
# Initializes redis server for inter-process communication 
# Input : 
#   pipeline_buffer_size : size of the buffer conataining myo data 
#   check_delay : time between data availability checks (in seconds)
# Returns : 
#   Redis server connection instance
#   Process handle for buffer maintenance process
def launch_myo_comm(pipeline_buffer_size, check_delay=0.1):

     # creating redis connection pool (for multiple connected processes)
    conn_pool = redis.ConnectionPool(host='localhost', port=6379, db=redis_db_id, decode_responses=True)

    # creating redis connection 
    r_server = redis.StrictRedis(connection_pool=conn_pool)
    r_server = init_redis_variables(r_server)

    # launching the buffer maintenance as a subprocess
    buffer_maintenance_p = Process(target=maintain_pipeline_buffer, name="myo_raw",
                                   args=(conn_pool, pipeline_buffer_size, check_delay))
    buffer_maintenance_p.start()

    # waiting for confirmation that myo is connected (data  is received)
    while(r_server.get("buffer_ready") != "1"): sleep(0.05)

    return r_server, buffer_maintenance_p