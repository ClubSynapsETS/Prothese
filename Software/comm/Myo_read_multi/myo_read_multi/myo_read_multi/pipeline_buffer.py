import pandas as pd
import numpy as np
import json

# importing myo bluetooth utilities
from time import sleep, time
from . import myo_raw
import sys

# importing multi processing utilities 
from multiprocessing import Process
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
#   r_server : redis server connection instance
#   n_clients : number of clients/models that will be accessing the db variables
#   n_outputs : number of outputs for the model/client (model is a classifier)
def init_redis_variables(r_server, n_clients, n_outputs):

    # defining reading flags for the client side
    r_server.set("pose_data_ready", "0")
    r_server.set("buffer_ready", "0")
    for _ in range(n_clients):
        r_server.lpush("client_read_data", "0")

    # defining the number of clients/models
    r_server.set("n_clients", str(n_clients))
    r_server.set("n_active_clients", "0")

    # defining list to store model predictions
    for client_i in range(n_clients):

        r_server.lpush("model_predictions", "X")
        r_server.lpush("prediction_step", "X")
        
        list_name = "output_probs_" + str(client_i)
        for _ in range(n_outputs):
            r_server.lpush(list_name, "X")

    # defining buffer maintenance flags
    r_server.set("raw_data_ready", "0")
    r_server.set("data_count", "0")

    # defining continuation flags
    r_server.set("read_from_myo", "1")
    r_server.set("buffer_maintained", "1")
    r_server.set("incoming_data", "1")

    # defining shared buffer containers
    r_server.set("raw_data", "")
    r_server.set("pipeline_buff", "")
    r_server.set("myo_pose", "")

    return r_server


# Resets proper maintenance flags when data is read in client/model process
# Inputs :
#   r_server : redis server connection instance
#   client_index : index of the client (specified at creation time)
def reset_pipeline_buff_flags(r_server, client_index):

    # if flags were already flipped
    if r_server.get("buffer_ready") == 0 : return

    # flipping flag for the specified client
    r_server.lset("client_read_data", client_index, "0")

    n_clients = int(r_server.get("n_clients"))
    data_count = int(r_server.get("data_count"))
     
    # not all clients need to have read the data
    if data_count <= n_clients : client_range = data_count
    else : client_range = n_clients

    # checking if all clients have read the buffer data
    buff_ready = True
    for i in range(client_range):
        if r_server.lindex("client_read_data", i) == 1 : 
            buff_ready = False
            break
    
    if buff_ready : r_server.set("buffer_ready", "0")
       

# Sets the buffer maintenance flags (use when the data is made available to clients)
# Inputs :
#   r_server : redis server connection instance
def set_pipeline_buff_flags(r_server):

    # main availability flag
    r_server.set("buffer_ready", "1")

    # availability flags for all clients
    n_clients = int(r_server.get("n_clients"))
    for i in range(n_clients):
        r_server.lset("client_read_data", i, "1")


# Stores latest prediction from specified model
# Inputs : 
#   r_server : redis server connection instance
#   client_index : index of the model/client
#   label : predicted label by the model with the specified client_index
#   probabilities : list of output probabilities of the current prediction
#   curr_step : the step at which the model made the prediction
def write_model_prediction(r_server, client_index, label, probabilities, curr_step):

    r_server.lset("model_predictions", client_index, label)
    r_server.lset("prediction_step", client_index, curr_step)

    prob_list_name = "output_probs_" + str(client_index)
    for prob_i in range(len(probabilities)) :
        r_server.lset(prob_list_name, prob_i, str(probabilities[prob_i]))


# Checks if a model/client with index can start receiving data
# Inputs : 
#   r_server : redis server connection
#   client_index : index of the client/model (provided at creation)
# Returns : boolean, true = model can receive data
def wait_for_start_time(r_server, client_index):

    if int(r_server.get("data_count")) > client_index :
        n_active_clients = int(r_server.get("n_active_clients")) + 1
        r_server.set("n_active_clients", str(n_active_clients))
        print("Model #", client_index, " is activated")
        return True

    return False


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
        # trying to disconnect the myo
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

    n_clients = int(r_server.get("n_clients"))

    try:

        # as long as the program is receiving myo data
        while(r_server.get("incoming_data") == "1"):

            # buffer should take around 250 ms to fill (when pipeline_buff_size = 50)
            sleep(check_delay)

            # making sure models are synchronized
            models_active = True
            data_count = int(r_server.get("data_count"))
            if data_count < n_clients:
                models_active = int(r_server.get("n_active_clients")) >= data_count

            # data is not currently available to parent process
            # and child process cant write to raw data buffer
            if(r_server.get("buffer_ready") == "0" and r_server.get("raw_data_ready") == "1" and models_active):

                # transfering the raw data buffer content to the pipeline buffer
                r_server.set("pipeline_buff", r_server.get("raw_data"))    
                set_pipeline_buff_flags(r_server)

                # incrementing buffer transfer counter
                data_count = int(r_server.get("data_count")) + 1
                r_server.set("data_count", str(data_count))

                # marking the raw data buffer as read
                r_server.set("raw_data", "")
                r_server.set("raw_data_ready", "0")

    except:
        print("Buffer maintenance process has failed.")

    # unsetting continuation flag for parent and child process
    r_server.set("buffer_maintained", "0")
    r_server.set("read_from_myo", "0")

    data_collection_p.join()


# Launches the buffer maintenance process and returns the handle
# Inputs : 
#   pipeline_buffer_size : size of the buffer conataining myo data
#   n_clients : number of processes that will be reading accessing the pipeline buffer
#   check_delay : time between data availability checks (in seconds)
#   n_outputs : number of outputs for the model/client (model is a classifier)
# Returns : 
#   Redis server connection instance
#   Process handle for buffer maintenance process
#   * the process has to be lauched from the returned handle
def launch_myo_comm(pipeline_buffer_size, n_outputs, n_clients=1, check_delay=0.1):

    # creating redis connection pool (for multiple connected processes)
    conn_pool = redis.ConnectionPool(host='localhost', port=6379, db=redis_db_id, decode_responses=True)

    # creating redis connection 
    r_server = redis.StrictRedis(connection_pool=conn_pool)
    r_server = init_redis_variables(r_server, n_clients, n_outputs)

    # defining the buffer maintenance funtion as a subprocess
    buffer_maintenance_p = Process(target=maintain_pipeline_buffer, name="myo_raw",
                                   args=(conn_pool, pipeline_buffer_size, check_delay))

    return r_server, buffer_maintenance_p