import numpy as np
import json

# importing pipeline utilities
from myo_read_filtered.pipeline_buffer import maintain_pipeline_buffer, reset_pipeline_buff_flags
from myo_read_filtered.pipeline_buffer import init_redis_variables, redis_db_id

# importing threading utilities
import redis
from multiprocessing import Process
from multiprocessing.managers import BaseManager

# importing pose definitions
from myo_read_filtered.myo_raw import Pose

if __name__ == "__main__":

    # creating redis connection pool (for multiple connected processes)
    conn_pool = redis.ConnectionPool(host='localhost', port=6379, db=redis_db_id, decode_responses=True)
    
    # creating redis connection 
    r_server = redis.StrictRedis(connection_pool=conn_pool)
    r_server = init_redis_variables(r_server)

    # defining the size for the pipeline buffer
    pipeline_buffer_size = 25

    # launching the buffer maintenance as a subprocess
    buffer_maintenance_p = Process(target=maintain_pipeline_buffer, args=(conn_pool, pipeline_buffer_size))
    buffer_maintenance_p.start()

    # while the incoming buffer is maintained
    while(r_server.get("buffer_maintained") == "1"):
        
        # pipeline buffer is ready to be read
        if(r_server.get("buffer_ready") == "1"):
            if(r_server.get("last_seg") == "1") : print("LAST SEGMENT")
            pipeline_buff =  np.array(json.loads(r_server.get("pipeline_buff")))
            for i in range(pipeline_buff.shape[0]) : print(pipeline_buff[i, : ])
            # marking buffer as read, so it may be refilled
            reset_pipeline_buff_flags(r_server)

        # pose data is ready to be read
        if(r_server.get("pose_data_ready") == "1"):
            print(Pose(int(r_server.get("myo_pose"))))
            # marking current pose as read
            r_server.set("pose_data_ready", "0")


    buffer_maintenance_p.join()
    