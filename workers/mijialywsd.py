import logging
import time
from interruptingcow import timeout

from mqtt import MqttMessage
from workers.base import BaseWorker
import logger

REQUIREMENTS = ['bluepy']
_LOGGER = logger.get(__name__)


# Bluepy might need special settings
# sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/local/lib/python3.6/dist-packages/bluepy/bluepy-helper

class MijialywsdWorker(BaseWorker):

  SCAN_TIMEOUT = 60

  def status_update(self):
    return [MqttMessage(topic=self.format_topic(), payload=self._get_value())]

  def _get_value(self):
    """
    https://www.domoticz.com/wiki/Domoticz_API/JSON_URL%27s#Temperature.2Fhumidity
    {
      "command": "udevice",
      "idx" : 7,
      "nvalue" : 0,
      "svalue" : "TEMP;HUM;HUM_STAT"
    }
    """
    from bluepy import btle

    scan_processor = ScanProcessor(self.mac)
    scanner = btle.Scanner().withDelegate(scan_processor)
    scanner.scan(self.SCAN_TIMEOUT, passive=True)

    with timeout(self.SCAN_TIMEOUT, exception=TimeoutError('Retrieving the temperature and humidity from {} device {} timed out after {} seconds'.format(repr(self), self.mac, self.SCAN_TIMEOUT))):
      while not all([scan_processor.temperature, scan_processor.humidity]):
        time.sleep(1)
      return {
        "command": "udevice",
        "idx" : self.domoticz_idx,
        "nvalue" : 0,
        "svalue" : "%s;%s;0" % (scan_processor.temperature, scan_processor.humidity)
      }

    return -1


class ScanProcessor():
  def __init__(self, mac):
    self._mac = mac
    self._temp = None
    self._hum = None
    self._data_mapping = {
      '04': '_temp',
      '06': '_hum',
    }

  def handleDiscovery(self, dev, isNewDev, isNewData):
    _LOGGER.debug('>>> handleDiscovery: %s, %s, %s', dev, isNewDev, isNewData)
    if dev.addr == self.mac.lower():
      for (sdid, desc, data) in dev.getScanData():
        if data.startswith('95fe') and sdid == 22:
          _LOGGER.debug('>>> Received Message: %s', data)
          data_type = data[28:30]
          measured = int(data[36:]+data[34:36], 16) * 0.1
          if data_type in self._data_mapping:
            setattr(self, self._data_mapping[data_type], round(measured, 2))

  @property
  def mac(self):
    return self._mac

  @property
  def temperature(self):
    return self._temp

  @property
  def humidity(self):
    return self._hum
