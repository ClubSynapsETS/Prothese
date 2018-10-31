from __future__ import print_function
import dbus, dbus.exceptions, dbus.mainloop.glib, dbus.service
import array

try:
  from gi.repository import GLib
except ImportError:
  import gobject as GObject
import micro_comm.advertising as advertising
import micro_comm.gatt_server as gatt_server
import argparse

import numpy as np
import json

# importing time utilities 
from time import sleep

# importing myo communication utilities
from myo_read_raw.pipeline_buffer import maintain_pipeline_buffer, reset_pipeline_buff_flags
from myo_read_raw.pipeline_buffer import init_redis_variables, redis_db_id

# importing threading utilities
import redis
from multiprocessing import Process
from multiprocessing.managers import BaseManager

# importing pose definitions
from myo_read_raw.myo_raw import Pose


def myo_comm_main(conn_pool):

    # creating redis connection 
    r_server = redis.StrictRedis(connection_pool=conn_pool)
    r_server = init_redis_variables(r_server)
    # defining the size for the pipeline buffer
    pipeline_buffer_size = 25

    # launching the buffer maintenance as a subprocess
    buffer_maintenance_p = Process(target=maintain_pipeline_buffer, args=(conn_pool, pipeline_buffer_size))

    #return Process to the main thread
    return buffer_maintenance_p



def micro_comm_connection(conn_pool):

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--adapter-name', type=str, help='Adapter name', default='')
    args = parser.parse_args()
    adapter_name = args.adapter_name

    #Connect to dbus systemBus
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()
    gatts_loop = GLib.MainLoop()
    bus = dbus.SystemBus()
    GLib.threads_init()

    advertising.advertising_main(gatts_loop, bus, adapter_name)
    #Link to shared memory space in bluetooth handler
    data_handler = gatt_server.gatt_server_main(gatts_loop, bus, adapter_name)

    return (gatts_loop, data_handler)



if __name__ == '__main__':

    # creating redis connection pool (for multiple connected processes)
    conn_pool = redis.ConnectionPool(host='localhost', port=6379, db=redis_db_id, decode_responses=True)

    # creating redis connection 
    r_server = redis.StrictRedis(connection_pool=conn_pool)
    r_server = init_redis_variables(r_server)


    microc_param = micro_comm_connection(conn_pool)
    #NOT A PROCESS, dbus mainloop object
    microcomm_loop = microc_param[0]
    microcomm_p = Process(target=microcomm_loop.run)
    microcomm_p.name = "micro_comm"
    microcomm_p.start()
    # micro_comm data handler
    microh = microc_param[1]

    #Start Myo connection and and link to redis buffer
    myocomm_p = myo_comm_main(conn_pool)
    myocomm_p.name = "myo_raw"
    myocomm_p.start()

    print("redis status: "+str(r_server.get("buffer_maintained")) + "comm loop="
            +str(microcomm_loop.is_running()))
    while(r_server.get("buffer_maintained") == "1" and microcomm_loop.is_running()):

        print(Pose(int(r_server.get("myo_pose"))))
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

    myocomm_p.join()
    microcomm_loop.quit()
    microcomm_p.join(10)
