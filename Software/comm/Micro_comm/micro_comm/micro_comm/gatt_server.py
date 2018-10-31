from __future__ import print_function
import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

import array

import functools

try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject

from random import randint

import micro_comm.exceptions as exceptions
import micro_comm.adapters as adapters

BLUEZ_SERVICE_NAME = 'org.bluez'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

GATT_MANAGER_IFACE = 'org.bluez.GattManager1'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'



class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(MyoMouvementService(bus, 0))
<<<<<<< HEAD:Software/comm/Micro_comm/gatt_server.py
        # self.add_service(HeartRateService(bus, 1))
=======
>>>>>>> refs/remotes/origin/master:Software/comm/Micro_comm/micro_comm/micro_comm/gatt_server.py

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        print('GetManagedObjects')

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 interface implementation
    """
    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_SERVICE_IFACE: {
                        'UUID': self.uuid,
                        'Primary': self.primary,
                        'Characteristics': dbus.Array(
                                self.get_characteristic_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise exceptions.InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]


class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_CHRC_IFACE: {
                        'Service': self.service.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                        'Descriptors': dbus.Array(
                                self.get_descriptor_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise exceptions.InvalidArgsException()

        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print('Default ReadValue called, returning error')
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print('Default StartNotify called, returning error')
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print('Default StopNotify called, returning error')
        raise exceptions.NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class Descriptor(dbus.service.Object):
    """
    org.bluez.GattDescriptor1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_DESC_IFACE: {
                        'Characteristic': self.chrc.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise exceptions.InvalidArgsException()

        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print('Default ReadValue called, returning error')
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise exceptions.NotSupportedException()


class MyoMouvementService(Service):
    MYOMV_UUID = '69a0977f-8fd5-434f-b506-0000658c1749'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.MYOMV_UUID, True)
        self.add_characteristic(MyoMouvementPoseChrc(bus, 0, self))
        self.add_characteristic(MyoMouvementModeChrc(bus, 1, self))

class MyoMouvementPoseChrc(Characteristic):
    MYOMV_POSE_UUID = '69a0977f-8fd5-434f-b506-0001658c1749'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.MYOMV_POSE_UUID,
                ['notify'],
                service)
        self.notifying = False

    def update(self, pose_number):
        value = []
        #value identifier for the microcontroller
        value.append(dbus.Byte(0x0))
        value.append(dbus.Byte(pose_number))
        self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': value }, [])
        return self.notifying

    def StartNotify(self):
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True
        self.update(0)

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False
        self.update(0)


class MyoMouvementModeChrc(Characteristic):
    MYOMV_MODE_UUID = '69a0977f-8fd5-434f-b506-0002658c1749'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.MYOMV_MODE_UUID,
                ['read'],
                service)
        #Default mode. behavior to be defined
        self.prot_mode = 0

    def update(self, mode):
        if mode <= 0 or mode >= 1:
            return "Invalide mode"
        else:
            self.prot_mode = mode
            return "Ok"

    def ReadValue(self, options):
        return self.prot_mode

def register_app_cb():
    print('GATT application registered')


def register_app_error_cb(mainloop, error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()


#Wrapper
class char_data_handler():
    def __init__(self, apps, name, path, mode):
        #tuple:(service_n, char_n)
        self.path = path
        #string: "readonly", "writeonly", "update"
        self.mode = mode

    def info():
        print(self.name+' mode: '+self.mode)
        print('Path: service[%d] characteristic[%d]'%path)


#Launches gatt server applications handlers
def gatt_server_main(mainloop, bus, adapter_name):
    adapter = adapters.find_adapter(bus, GATT_MANAGER_IFACE, adapter_name)
    if not adapter:
        raise Exception('GattManager1 interface not found')

    service_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter),
            GATT_MANAGER_IFACE)

    #Curently, only one app is used and on contains only one H3C 1K3service and one char
    apps = []
    apps.append(Application(bus))

    data_handler = {
            'Pose': apps[0].services[0].characteristics[0],
            'Mode': apps[0].services[0].characteristics[1]
            }

    print('Registering GATT application...')

    try:
        service_manager.RegisterApplication(apps[0].get_path(), {},
                                    reply_handler=register_app_cb,
                                    error_handler=functools.partial(register_app_error_cb, mainloop))
    except:
        pass
    return data_handler
