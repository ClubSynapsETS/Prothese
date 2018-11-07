import numpy as np
import json, array

from __future__ import print_function

# importing multi-process utilities
from multiprocessing import Process

# importing myo communication utilities
from myo_read_raw.pipeline_buffer import launch_myo_comm, reset_pipeline_buff_flags

#import main loop from micro comm API
from micro_comm.connect import launch_micro_comm

# importing pose definitions
from myo_read_raw.myo_raw import Pose

# defining the size for the pipeline buffer
pipeline_buffer_size = 25

if __name__ == '__main__':

    #NOT A PROCESS, dbus mainloop object
    microcomm_loop, microh = launch_micro_comm()
    microcomm_p = Process(target=microcomm_loop.run, name="micro_comm")
    microcomm_p.start()

    #Start Myo connection and and link to redis buffer
    r_server, myocomm_p = launch_myo_comm(pipeline_buffer_size)

    # status print
    print("redis status: " + str(r_server.get("buffer_maintained")) + "comm loop="
          + str(microcomm_loop.is_running()))
    
    try:
        
        while(r_server.get("buffer_maintained") == "1" and microcomm_loop.is_running()):
                
            # pipeline buffer is ready to be read
            # if(r_server.get("buffer_ready") == "1"):
                # pipeline_buff =  np.array(json.loads(r_server.get("pipeline_buff")))
                # for i in range(pipeline_buff.shape[0]) : print(pipeline_buff[i, : ])
                # marking buffer as read, so it may be refilled
                # reset_pipeline_buff_flags(r_server)

            # pose data is ready to be read
            if(r_server.get("pose_data_ready") == "1"):
                #send pose to prosthesis
                microh['Pose'].update(int(r_server.get("myo_pose")))
                # marking current pose as read
                print(Pose(int(r_server.get("myo_pose"))))
                r_server.set("pose_data_ready", "0")

    except:
        # unsetting continuation flag for the child process
        r_server.set("incoming_data", "0")

    # waiting for the child processes to end
    myocomm_p.join()
    microcomm_loop.quit()
    microcomm_p.join(10)
