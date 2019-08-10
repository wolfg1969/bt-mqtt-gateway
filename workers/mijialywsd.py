import time
from interruptingcow import timeout

from mqtt import MqttMessage
from workers.base import BaseWorker

REQUIREMENTS = ['bluepy']


# Bluepy might need special settings
# sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/local/lib/python3.6/dist-packages/bluepy/bluepy-helper

class MijialywsdWorker(BaseWorker):

  SCAN_TIMEOUT = 5

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

  def handleDiscovery(self, dev, isNewDev, _):
    if dev.addr == self.mac.lower() and isNewDev:
      for (sdid, desc, data) in dev.getScanData():
        print(sdid, desc, data)
        # if data.startswith('1d18') and sdid == 22:
          # measured = int((data[8:10] + data[6:8]), 16) * 0.01

          # self._weight = round(measured / 2, 2)

  @property
  def mac(self):
    return self._mac

  @property
  def temperature(self):
    return self._temp

  @property
  def humidity(self):
    return self._hum
