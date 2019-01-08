import numpy as np
import json

from multiprocessing import Process
from time import sleep

# importing myo communication package
from myo_read_multi.pipeline_buffer import launch_myo_comm, reset_pipeline_buff_flags, wait_for_start_time
from myo_read_multi.myo_raw import Pose

pipeline_buffer_size = 25
n_clients = 10

# specifying a check delay (default is 0.1)
# defines the wait time between pipeline checks in the buffer maintenance process
check_delay = 0.1

# client process for the myo server
def myo_client_process(r_server, client_index, check_delay):

    client_activated = False

    try :

        # while the incoming buffer is maintained
        while(r_server.get("buffer_maintained") == "1"):
            
            # once the model is activated, reduce resource consumption
            if client_activated : sleep(check_delay)

            # checking if the client is activated
            else :
                client_activated = wait_for_start_time(r_server, client_index)

            # pipeline buffer is ready to be read
            if(r_server.lindex("client_read_data", client_index) == "1" and client_activated):

                # reading data from the buffer
                #print("Raw data : ", np.array(json.loads(r_server.get("pipeline_buff"))))

                # marking buffer as read (by this client)
                reset_pipeline_buff_flags(r_server, client_index)
                
                print("Client with index : ", client_index, " received data.")
                
    except:
            # unsetting continuation flag for acquisition process
            r_server.set("incoming_data", "0")
            print("Client with index : ", client_index, " has failed.")



if __name__ == "__main__":

    # starting the buffer maintenance process
    r_server, buffer_maintenance_p = launch_myo_comm(pipeline_buffer_size, n_clients=n_clients, 
                                                    check_delay=check_delay)

    # lauching the client processes
    myo_clients = []
    for i in range(n_clients):
        p = Process(target=myo_client_process, args=(r_server, i, check_delay))
        p.start()
        myo_clients.append(p)

    # waiting for confirmation that myo is connected (data  is received)
    # launching the buffer maintenance process
    buffer_maintenance_p.start()
    while(r_server.get("buffer_ready") != "1"): sleep(0.05)

    # waiting for the processes to finish
    for p in myo_clients:
        p.join()
    buffer_maintenance_p.join()