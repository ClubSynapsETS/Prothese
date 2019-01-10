import numpy as np
import json

# importing time utilities 
from time import sleep

# importing pipeline utilities
from myo_read_raw.pipeline_buffer import maintain_pipeline_buffer, reset_pipeline_buff_flags
from myo_read_raw.pipeline_buffer import init_redis_variables, redis_db_id

# importing threading utilities
import redis
from multiprocessing import Process
from multiprocessing.managers import BaseManager

# importing pose definitions
from myo_read_raw.myo_raw import Pose

# keyboard detection utilities
import keyboard

# defining acquisition parameters
max_span = 1
relax_span = 5
json_file_name = "Calibration_out.json"

# handles state messages
# acq_states : 
# 0 : (init) 
# 1 : (clenched fist capture)
# 2 : (rest capture)
# 3 : (acquisition finished)
def display_ui_message(curr_acq_state, old_acq_state): 
    if(curr_acq_state == 1 and old_acq_state != 1): 
        print("\n\nClench your fist with max/moderate force. Press \"Space bar\" when done.\n")        
    elif(curr_acq_state == 2 and old_acq_state != 2):
        print("Leave your hand in a relaxed position. Press \"Space bar\" when done.\n")
    elif(curr_acq_state == 3 and old_acq_state != 3):
        print("Acquisition completed.\n\n")



# computes the (absolute avg) for n data points in X
# returns the avg according to the (specifier)
# input : 
#   X : ndaray of shape (n_sensors, n_data_points)
#   span : then span over which to calculate the average
#   specifier :  specifies which avg value to return values : ("smallest", "biggest")
def get_specified_avg(X, span, specifier):

    n_channels = X.shape[0]
    n_data = X.shape[1]
    avg_container = np.zeros((n_channels, span))
    final_avg = 0
    real_avg = 0

    if(span > n_data): 
        raise(ValueError("Not enough data to fill specified span"))

    if(specifier == "smallest"): final_avg = 10000 
    elif(specifier == "biggest"): final_avg = 0

    # first filling of the container
    avg_container[:,:] = X[:, 0 : span] 

    # walking the container across the data
    for i in range(n_data - span):

        channels_avgs = np.zeros(n_channels)

        # the channel in the avg_container with the smallest avg wins
        if(specifier == "smallest"):
            for i in range(n_channels): 
                channels_avgs[i] = np.absolute(avg_container[i, :]).mean()    
            current_avg = channels_avgs.min()
            real_avg = avg_container[np.argmin(channels_avgs), : ].mean()

        # the channel in the avg_container with the biiggest avg wins
        elif(specifier == "biggest"): 
            for i in range(n_channels): 
                channels_avgs[i] = np.absolute(avg_container[i, :]).mean()
            current_avg = channels_avgs.max()

        # update the avg container
        avg_container[:,:] = X[ : , i : span+i]

        # updating the final avg
        if(specifier == "smallest"):
            if(final_avg > current_avg): final_avg = real_avg
        if(specifier == "biggest"):
            if(final_avg < current_avg): final_avg = current_avg

    return final_avg



if __name__ == "__main__":

    # creating redis connection pool (for multiple connected processes)
    conn_pool = redis.ConnectionPool(host='localhost', port=6379, db=redis_db_id, decode_responses=True)
    
    # creating redis connection 
    r_server = redis.StrictRedis(connection_pool=conn_pool)
    r_server = init_redis_variables(r_server)

    # defining the size for the pipeline buffer
    pipeline_buffer_size = 50

    # launching the buffer maintenance as a subprocess
    buffer_maintenance_p = Process(target=maintain_pipeline_buffer, args=(conn_pool, pipeline_buffer_size))
    buffer_maintenance_p.start()
 
    batch_processed = False
    acquisition_done = False
    curr_acq_state = 0
    old_acq_state = 0
    center_rest_value = 1000
    max_effort_value = 0

    # waiting for confirmation that myo is connected (data  is received)
    while(r_server.get("buffer_ready") != "1"): sleep(0.05)   

    # while the incoming buffer is maintained
    while(r_server.get("buffer_maintained") == "1" and not acquisition_done):

        # getting data from the myo
        if(r_server.get("buffer_ready") == "1"):
            pipeline_buff =  np.array(json.loads(r_server.get("pipeline_buff")))
            reset_pipeline_buff_flags(r_server)
            batch_processed = False

        # marking the init state
        if(curr_acq_state == 0): curr_acq_state = 1

        # handling display for different states
        display_ui_message(curr_acq_state, old_acq_state)
        
        # acquisition for clenched fist
        if(curr_acq_state == 1):
            if(not batch_processed): 
                batch_processed = True
                batch_max = get_specified_avg(pipeline_buff, max_span, "biggest")
                if(batch_max > max_effort_value): max_effort_value = batch_max

        # acquisition for rest
        if(curr_acq_state == 2):
            if(not batch_processed): 
                batch_processed = True
                batch_min = get_specified_avg(pipeline_buff, relax_span, "smallest")
                if(batch_min < center_rest_value): center_rest_value = batch_min

        # exit state
        if(curr_acq_state == 3):
            data = {"Rest_value_mean" : center_rest_value, 
                    "Max_effort_mean" : max_effort_value} 
            with open(json_file_name, 'w') as outfile:
                json.dump(data, outfile)
            break

        # handling state changes
        old_acq_state = curr_acq_state
        if(keyboard.is_pressed('space')): 
            curr_acq_state += 1
            sleep(1)

    buffer_maintenance_p.join()
