import logging
import time
from interruptingcow import timeout

from mqtt import MqttMessage
from workers.base import BaseWorker
import logger

REQUIREMENTS = ['bluepy', 'lywsd02']
monitoredAttrs = ["temperature", "humidity"]
_LOGGER = logger.get(__name__)


# Bluepy might need special settings
# sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/local/lib/python3.6/dist-packages/bluepy/bluepy-helper

class Mijialywsd02Worker(BaseWorker):

  def _setup(self):
    from lywsd02 import Lywsd02Client

    self._devices = {}

    _LOGGER.info("Adding %d %s devices", len(self.devices), repr(self))
    for device in self.devices:
      name = device.get('name')
      mac = device.get('mac')
      domoticz_idx = device.get('domoticz_idx')
      _LOGGER.debug("Adding %s device '%s' (%s)", repr(self), name, mac)
      self._devices[name] = {"mac": mac, "client": Lywsd02Client(mac), "domoticz_idx": domoticz_idx}

  def config(self):
    ret = []
    for name, data in self._devices.items():
      ret += self.config_device(name, data["mac"])
    return ret

  def config_device(self, name, mac):
    ret = []
    device = {
      "identifiers": [mac, self.format_discovery_id(mac, name)],
      "manufacturer": "Xiaomi",
      "model": "LYWSD2",
      "name": self.format_discovery_name(name)
    }

    for attr in monitoredAttrs:
      payload = {
        "unique_id": self.format_discovery_id(mac, name, attr),
        "name": self.format_discovery_name(name, attr),
        "state_topic": self.format_topic(name, attr),
        "device_class": attr,
        "device": device
      }

      if attr == 'temperature':
        payload["unit_of_measurement"] = "°C"
      elif attr == 'humidity':
        payload["unit_of_measurement"] = "%"
      elif attr == 'battery':
        payload["unit_of_measurement"] = "%"

      ret.append(MqttConfigMessage(MqttConfigMessage.SENSOR, self.format_discovery_topic(mac, name, attr), payload=payload))

    return ret

  def status_update(self):
    _LOGGER.info("Updating %d %s devices", len(self.devices), repr(self))
    ret = []
    for name, data in self._devices.items():
      _LOGGER.debug("Updating %s device '%s' (%s)", repr(self), name, data["mac"])
      from btlewrap import BluetoothBackendException
      try:
        device_state = self.update_device_state(name, data["client"])

        domoticz_idx = data.get('domoticz_idx')
        if domoticz_idx:
          """
          https://www.domoticz.com/wiki/Domoticz_API/JSON_URL%27s#Temperature.2Fhumidity
          {
            "command": "udevice",
            "idx" : 7,
            "nvalue" : 0,
            "svalue" : "TEMP;HUM;HUM_STAT"
          }
          """
          ret.append(MqttMessage(topic=self.format_topic(), payload={
            "command": "udevice",
            "idx" : domoticz_idx,
            "nvalue" : 0,
            "svalue" : "{};{};0".format(*device_state[:2])
          })
        else:
          for attr in monitoredAttrs:
            index = monitoredAttrs.index(attr)
            ret.append(MqttMessage(topic=self.format_topic(name, attr), payload=domoticz_idx[index]))

      except BluetoothBackendException as e:
        logger.log_exception(_LOGGER, "Error during update of %s device '%s' (%s): %s", repr(self), name, data["mac"], type(e).__name__, suppress=True)
    return ret

  def update_device_state(self, name, client):
    return [getattr(client, attr) for attr in monitoredAttrs]
