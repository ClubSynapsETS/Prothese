
import dbus, dbus.exceptions, dbus.mainloop.glib, dbus.service
import array

try:
  from gi.repository import GLib
except ImportError:
  import gobject as GObject
import argparse

from micro_comm import advertising, gatt_server

#Launching microcontroller commication handlers
def launch_micro_comm():
    #locate bluetooth dongle
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

    gatts_loop.run()

    return (gatts_loop, data_handler)

