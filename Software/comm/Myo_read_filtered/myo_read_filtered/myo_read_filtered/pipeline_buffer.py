import pandas as pd
import numpy as np
import json

# utilities to remove rest zones
from .rest_zones import segment_data, DataCluster

# importing myo bluetooth utilities
from time import sleep, time
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
data_cluster_store = []
data_store_max_size = 5000



# defining custom bluetooth exception (when connection fails)
class BluetoothFailedConnection(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)



# creating necessary variables for redis session
def init_redis_variables(r_server):

    # defining buffer maintenance flags
    r_server.set("buffer_ready", "0")
    r_server.set("last_seg", "0")
    r_server.set("buffer_maintained", "1")
    r_server.set("incoming_data", "1")
    r_server.set("raw_data_ready", "0")
    r_server.set("reset_buff_size", "0")
    r_server.set("pose_data_ready", "0")

    # defining shared buffer containers
    r_server.set("raw_data", "")
    r_server.set("pipeline_buff", "")
    r_server.set("myo_pose", "")

    return r_server



# resets the buffer maintenace flag after data is read in main process 
def reset_pipeline_buff_flags(r_server):
    r_server.set("buffer_ready", "0")
    r_server.set("last_seg", "0")
    r_server.set("reset_buff_size", "1")



# creates a connected myo bluetooth object
# input : redis server connection
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



# extracts data from the a myo instance and fills the raw_data buffer
# this function is ment to be run a seperate process
# input : redis connection pool
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

    # pulling data from the myo
    try :
        while(True): myo_connection.run(1)
    except :
        myo_connection.disconnect()
        r_server.set("incoming_data", "0")
        print("Buffer maintenance thread aborted, error while reading from myo")
        print("myo disconnected")
        return



# maintains the pipeline buffer, which contains data ready for further pipelines
# this function is ment to be run a a seperate process
# input : connection pool for redis
def maintain_pipeline_buffer(conn_pool, new_pipeline_buff_size=None):

    global data_cluster_store, data_store_max_size, pipeline_buff_size

    # changing the pipeline_buff_size (global var) for all functions
    if new_pipeline_buff_size is None : 
        pipeline_buff_size = new_pipeline_buff_size

    # local version of the pipeline buffer
    pipeline_buff = np.empty((n_incoming_sensors, pipeline_buff_size))
    buff_content_size = 0

    # creating redis connection for current process
    r_server = redis.StrictRedis(connection_pool=conn_pool)

    # launching data collecting thread
    data_collection_p = Process(target=collect_myo_data, args=(conn_pool,))
    data_collection_p.start()

    # as long as the program is receiving myo data
    while(r_server.get("incoming_data") == "1"):

        # turning a full raw data buffer to a DataCLuster and queueing
        if(r_server.get("raw_data_ready") == "1"):
            new_raw_data = np.array(json.loads(r_server.get("raw_data")))
            data_cluster_store.append(segment_data(new_raw_data, rest_thresh_val=5))
            r_server.set("raw_data", "")
            r_server.set("raw_data_ready", "0")
            
        # data can be fead to the parent process
        if(len(data_cluster_store) > 0 and r_server.get("buffer_ready") == "0"):
            
            # resetting the pipeline buffer size
            if(r_server.get("reset_buff_size") == "1"):
                buff_content_size = 0
                r_server.set("reset_buff_size", "0")
        
            # adding clensed data to the pipeline buffer
            buffer_info = fill_pipeline_buff(data_cluster_store[0], pipeline_buff, buff_content_size)
            last_seg_flag = buffer_info["last_segment"]            
            used_cluster = buffer_info["data_cluster"]
            pipeline_buff = buffer_info["pipeline_buffer"]
            buff_content_size = buffer_info["buffer_size"]

            # pipeline buffer is full or movement ended
            if((buff_content_size == pipeline_buff_size) or last_seg_flag):
                r_server.set("pipeline_buff", json.dumps(pipeline_buff.tolist()))
                if(last_seg_flag): r_server.set("last_seg", "1")
                r_server.set("buffer_ready", "1")
                
            # putting used cluster back in storage
            if(used_cluster is None): del data_cluster_store[0]
            else: data_cluster_store[0] = used_cluster

        # maintaning data_cluster_store size
        if(len(data_cluster_store) > data_store_max_size):
            data_cluster_store.pop()

    # marking the end of buffer maintenance
    r_server.set("buffer_maintained", "0")
    data_collection_p.join()

    
        
# function to add data to the pipeline buffer
# modifies :
# pipeline buffer (which is passed by reference)
# returns :
# clensed data : none -> remove the element from storage, not none -> replace the element in storage 
# true/false : true -> last buffer fill for current movement, false -> current movement is still under way
def fill_pipeline_buff(data_cluster, pipeline_buff, buff_content_size):

    last_buffer_fill = False
    last_seg_selected = False
    new_content_size = 0

    # preparing the return container 
    buffer_info = {"data_cluster": None, "pipeline_buffer": None, "buffer_size": None}

    # continuous data in the cluster
    if(not data_cluster.rest_zone_detected): 
        new_data = data_cluster.whole_data
    
    # cluster contains segments 
    else :

        # cluster contains segmented data
        if(data_cluster.curr_mov_last_seg is not None):
            new_data = data_cluster.curr_mov_last_seg
            last_seg_selected = True
        elif(data_cluster.next_mov_first_seg is not None): 
            new_data = data_cluster.next_mov_first_seg
        
        # no data in the cluster
        else :
            buffer_info["data_cluster"] = None
            buffer_info["pipeline_buffer"] = pipeline_buff
            buffer_info["buffer_size"] = buff_content_size
            buffer_info["last_segment"] = False
            return buffer_info

    # getting space information
    new_data_size = new_data.shape[1]
    available_buff_space = pipeline_buff_size - buff_content_size

    # if the clensed data can all fit in the buffer
    if(new_data_size <= available_buff_space):
        pipeline_buff[ : , buff_content_size : (buff_content_size + new_data_size)] = new_data[ : , : ]
        new_data = None
        new_content_size = buff_content_size + new_data_size
        # if new data is lastsegment for the movement 
        if(last_seg_selected): last_buffer_fill = True

    # if the new data size exceeds remainning buffer space (buffer is sure to be filled)
    elif(new_data_size > available_buff_space):
        pipeline_buff[ : , buff_content_size : ] = new_data[ : , : available_buff_space]
        new_data = new_data[ : , available_buff_space : ]
        new_content_size = pipeline_buff_size

    # putting remaining new data back in the data cluster
    if(not data_cluster.rest_zone_detected):
        data_cluster.whole_data = new_data
    else :
        if(data_cluster.curr_mov_last_seg is not None):
            data_cluster.curr_mov_last_seg = new_data
        elif(data_cluster.next_mov_first_seg is not None): 
            data_cluster.next_mov_first_seg = new_data

    # checking if the data cluster is empty
    if(data_cluster.is_empty()) : data_cluster = None

    buffer_info["data_cluster"] = data_cluster
    buffer_info["pipeline_buffer"] = pipeline_buff
    buffer_info["buffer_size"] = new_content_size
    buffer_info["last_segment"] = last_buffer_fill
    return buffer_info
