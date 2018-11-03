import numpy as np
import json

# importing time utilities 
from time import sleep

# importing myo communication utilities
from myo_read_raw.pipeline_buffer import launch_myo_comm, reset_pipeline_buff_flags

# importing pose definitions
from myo_read_raw.myo_raw import Pose

# defining the size for the pipeline buffer
pipeline_buffer_size = 25


if __name__ == "__main__":

    # starting the buffer maintenance process
    r_server, buffer_maintenance_p = launch_myo_comm(pipeline_buffer_size)

    try:

        # while the incoming buffer is maintained
        while(r_server.get("buffer_maintained") == "1"):

            # pipeline buffer is ready to be read
            if(r_server.get("buffer_ready") == "1"):
                pipeline_buff = np.array(json.loads(r_server.get("pipeline_buff")))
                for i in range(pipeline_buff.shape[0]) : print(pipeline_buff[i, : ])
                # marking buffer as read, so it may be refilled
                reset_pipeline_buff_flags(r_server)

            # pose data is ready to be read
            if(r_server.get("pose_data_ready") == "1"):
                print(Pose(int(r_server.get("myo_pose"))))
                # marking current pose as read
                r_server.set("pose_data_ready", "0")

    except:
        # unsetting continuation flag for the child process
        r_server.set("incoming_data", "0")

    #waiting for the child process to end
    buffer_maintenance_p.join()