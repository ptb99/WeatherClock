##
## Wrapper for reading Adafruit BME680 on RPi OS
##

#import time
import logging

#import RPi.GPIO as GPIO
import smbus
import bme680

## Use the Pimoroni driver
# pip install bme680
## or
# git clone https://github.com/pimoroni/bme680-python

## Alternate:
#import adafruit_bme680
# pip3 install adafruit-circuitpython-bme680





class BME_Probe:
    BUS_NUMBER = 1

    ## Connected via StemmaQT (which is I2C)
    TARGET_ADDR = 0x77   # default seems to be I2C_ADDR_SECONDARY??

    ## Other calibration
    TEMP_OFFSET = -2.7             # added to temp in C before returning
    #GAS_BASELINE = 108600         # based on burn-in measurement
    GAS_BASELINE = 124000          # based on burn-in measurement


    def __init__(self):
        self.logger = logging.getLogger()

        self.bus = smbus.SMBus(self.BUS_NUMBER)

        self.bme = bme680.BME680(i2c_addr=self.TARGET_ADDR, i2c_device=self.bus)
        # SMBus(1) is the default if i2c_device not specified...
        #self.bme = bme680.BME680()

        ## These are the defaults:
        # bme.set_humidity_oversample(bme680.OS_2X)
        # bme.set_pressure_oversample(bme680.OS_4X)
        # bme.set_temperature_oversample(bme680.OS_8X)
        # bme.set_filter(bme680.FILTER_SIZE_3)

        # # Default oversampling and filter register values.
        # self._pressure_oversample = 0b011
        # self._temp_oversample = 0b100
        # self._humidity_oversample = 0b010
        # self._filter = 0b010

        # calibration adjustment for temperature
        self.bme.set_temp_offset(self.TEMP_OFFSET)

        ## Need more research here...
        # These are the "burn-in" settings from the read-all.py example
        # self.bme.set_gas_heater_temperature(320)
        # self.bme.set_gas_heater_duration(150)
        # self.bme.select_gas_heater_profile(0)

        # Up to 10 heater profiles can be configured, each
        # with their own temperature and duration.
        self.bme.set_gas_heater_profile(320, 900, nb_profile=1)
        self.bme.select_gas_heater_profile(1)

        # Initially, just ignore VOC and read the other measurements
        #self.bme.set_gas_status(bme680.DISABLE_GAS_MEAS)
        self.bme.set_gas_status(bme680.ENABLE_GAS_MEAS)

        # This is likely superfluous
        self.results = {}

    def read_data(self):
        if self.bme.get_sensor_data():
            # This shouldn't be necessary, as bme.data won't be overwritten
            # until another get_sensor_data() call is made.
            data = self.bme.data
            self.results['temperature'] = data.temperature
            self.results['pressure'] = data.pressure
            self.results['humidity'] = data.humidity
            if data.heat_stable:
               self.results['gas_resistance'] = data.gas_resistance
            return True
        else:
            return False

    def get_temp(self):
        #value = self.results['temperature']
        value = self.bme.data.temperature
        temp = value * 9 / 5 + 32 # convert to F
        return temp

    def get_humidity(self):
        #value = self.results['humidity']
        value = self.bme.data.humidity
        return value            # no conversion

    def get_barom(self):
        """return pressure in in-Hg"""
        # 1 in-Hg = 3,386.388640341 Pa = 33.8638864 hPa
        #value = self.results['pressure']
        value = self.bme.data.pressure
        return value/ 33.8638864 

    def get_voc(self):
        #value = self.results['gas_resistance'] # in Ohms
        value = self.bme.data.gas_resistance # in Ohms
        return value                           # convert to AQI (someday)?


# # Example code
# while True:
#     if sensor.get_sensor_data():
#         output = "{0:.2f} C,{1:.2f} hPa,{2:.2f} %RH".format(
#            sensor.data.temperature, sensor.data.pressure, sensor.data.humidity)
#         if sensor.data.heat_stable:
#             print("{0},{1} Ohms".format(output, sensor.data.gas_resistance))
#         else:
#             print(output)
#     time.sleep(1)
    
