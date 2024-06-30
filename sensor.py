##
## Wrapper for reading Adafruit BME680 on RPi OS
##

import time
import asyncio
import logging

#import RPi.GPIO as GPIO
import smbus2
import bme680

## Use the Pimoroni driver
# pip install bme680
## or
# git clone https://github.com/pimoroni/bme680-python

## Alternate:
#import adafruit_bme680
# pip3 install adafruit-circuitpython-bme680


## utility function:
def avg_last_n(points, n=5):
    """Return the mean of the last N data points in POINTS"""
    sublist = points[-n:]
    return sum(sublist)/len(sublist)


class DummyBME680():
    def __init__(self):
        self.logger = logging.getLogger()
        self.gas_enable = False
        self.data = bme680.FieldData()
        self.logger.info('DummyBME680 called - <either Test env or I2C failure>')

    def get_sensor_data(self):
        self.data.temperature = 20.0 # C
        self.data.humidity = 42.0
        self.data.pressure = 998.984 # hPa
        if self.gas_enable:
            self.data.heat_stable = True
            self.data.gas_resistance = 111_000
        else:
            self.data.gas_resistance = 0
        self.logger.debug('Dummy BME680 get_sensor_data()')
        return True

    def set_temp_offset(self, temp_offset):
        self.logger.info(f'Dummy BME680 set_temp_offset({temp_offset})')
        return True

    def select_gas_heater_profile(self, nb_profile):
        self.logger.info(f'Dummy BME680 select_gas_heater_profile({nb_profile})')
        return True

    def set_gas_heater_profile(self, temp, duration, nb_profile=0):
        self.logger.info(
            f'Dummy BME680 set_gas_heater_profile({temp}, {duration}, {nb_profile})'
        )
        return True

    def set_gas_status(self, enable):
        self.logger.info(f'Dummy BME680 set_gas_status({enable})')
        self.gas_enable = enable
        return True             # should return old enable?


class BME_Probe:
    BUS_NUMBER = 1

    ## Connected via StemmaQT (which is I2C)
    TARGET_ADDR = 0x77   # default seems to be I2C_ADDR_SECONDARY??

    ## Other calibration
    TEMP_OFFSET = -3.0             # added to temp in C before returning
    #GAS_BASELINE = 108600         # based on burn-in measurement
    GAS_BASELINE = 400_000          # based on burn-in measurement

    # tags for a complete set of measurement results
    FIELDS = ('temperature', 'humidity', 'pressure', 'gas_resistance')

    def __init__(self):
        self.logger = logging.getLogger()

        try:
            self.bus = smbus2.SMBus(self.BUS_NUMBER)
            self.bme = bme680.BME680(i2c_addr=self.TARGET_ADDR, i2c_device=self.bus)
            self.logger.info(f'BME680 driver: variant={self.bme._variant} '
                             f'ambient temp={self.bme.ambient_temperature}')
        except (RuntimeError, IOError, PermissionError):
            self.bme = DummyBME680()
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

        # These are the "burn-in" settings from the read-all.py example
        # self.bme.set_gas_heater_temperature(320)
        # self.bme.set_gas_heater_duration(150)
        # self.bme.select_gas_heater_profile(0)

        # Up to 10 heater profiles can be configured, each
        # with their own temperature and duration.
        self.bme.set_gas_heater_profile(320, 500, nb_profile=1)
        self.bme.select_gas_heater_profile(1)

        # Initially, just ignore VOC and read the other measurements
        self.bme.set_gas_status(bme680.DISABLE_GAS_MEAS)

        # Cache the results of the last multi-sample measurement reading
        self.last_readings = {tag:0 for tag in self.FIELDS}

    def read_data(self, do_voc=False):
        if do_voc:
            self.bme.set_gas_status(bme680.ENABLE_GAS_MEAS)
        else:
            self.bme.set_gas_status(bme680.DISABLE_GAS_MEAS)

        if self.bme.get_sensor_data():
            # This shouldn't be necessary, as bme.data won't be overwritten
            # until another get_sensor_data() call is made.
            data = self.bme.data
            results = {}
            results['temperature'] = data.temperature
            results['pressure'] = data.pressure
            results['humidity'] = data.humidity
            if data.heat_stable:
                results['gas_resistance'] = data.gas_resistance
            else:
                if do_voc:
                    self.logger.warning('sensor read_data() no heat_stable')
                results['gas_resistance'] = 0
            self.logger.debug(f'sensor read_data(): {results}')
            return results
        else:
            return None

    async def read_loop(self):
        ## these could be optional params??
        NUM_PTS = 5             # measurements to average into a reading
        INTVL = 2               # seconds between measurement
        PAUSE_TIME = 20         # time between temp and VOC readings

        # Track the measurments here:
        points = {tag:[] for tag in self.FIELDS}

        # Track our timings
        #start = time.perf_counter()
        start_reading = time.time()
        duration_temps = 0
        elapsed_temps = 0

        # First read temp/humid/pressure w/o VOC
        for _ in range(2*NUM_PTS):
            start = time.time()
            results = self.read_data(do_voc=False)
            if results:
                for tag in self.FIELDS:
                    if tag != 'gas_resistance':
                        points[tag].append(results[tag])
            stop = time.time()
            duration_temps += (stop - start)
            await asyncio.sleep(INTVL)

        elapsed_temps = (time.time() - start_reading)
        # Sleep for a while
        await asyncio.sleep(PAUSE_TIME)

        start_vocs = time.time()
        duration_vocs = 0
        elapsed_vocs = 0

        # Then do a bunch of VOC measurement
        for _ in range(3*NUM_PTS):
            start = time.time()
            results = self.read_data(do_voc=True)
            if results and results['gas_resistance'] > 0:
                points['gas_resistance'].append(results['gas_resistance'])
            stop = time.time()
            duration_vocs += (stop - start)
            await asyncio.sleep(INTVL)

        stop_vocs = time.time()
        elapsed_vocs = (stop_vocs - start_vocs)
        duration_total = stop_vocs - start_reading
        self.logger.info(f'sensor read_loop(): {duration_total:.3f}s = '
              f'Temps: {len(points["temperature"])} in {duration_temps*1000:.3f}ms for {elapsed_temps:.3f}s, '
              f'VOCs: {len(points["gas_resistance"])} in {duration_vocs*1000:.3f}ms for {elapsed_vocs:.3f}s'
            )

        # average the last 5 points
        results = {tag: avg_last_n(points[tag], n=NUM_PTS) for tag in self.FIELDS}
        self.last_readings = results
        self.logger.info(f'sensor read_loop(): {results}')
        return results

    def get_curr_temp(self):
        """return temperature in deg-C"""
        value = self.bme.data.temperature
        temp = value * 9 / 5 + 32 # convert to F
        return temp

    def get_curr_humidity(self):
        """return relative humidity in percent"""
        value = self.bme.data.humidity
        return value            # no conversion

    def get_curr_barom(self):
        """return pressure in in-Hg"""
        # 1 in-Hg = 3,386.388640341 Pa = 33.8638864 hPa
        value = self.bme.data.pressure
        return value/ 33.8638864 

    def get_curr_voc(self):
        """return resistance in Ohms as a measure of Volatile Organic Compounds"""
        value = self.bme.data.gas_resistance # in Ohms
        return value                           # convert to AQI (someday)?

    def get_last_temp(self):
        """return temperature in deg-C"""
        value = self.last_readings['temperature']
        temp = value * 9 / 5 + 32 # convert to F
        return temp

    def get_last_humidity(self):
        """return relative humidity in percent"""
        return  self.last_readings['humidity']

    def get_last_barom(self):
        """return pressure in in-Hg"""
        # 1 in-Hg = 3,386.388640341 Pa = 33.8638864 hPa
        value = self.last_readings['pressure']
        return value/ 33.8638864

    def get_last_voc(self):
        """return resistance in Ohms as a measure of Volatile Organic Compounds"""
        return  self.last_readings['gas_resistance']


def test():
    sensor = BME_Probe()
    INTVL = 3
    #MODE = 'raw'
    #MODE = 'sync'
    MODE = 'async'

    try:
        if MODE == 'raw':
            sensor.bme.set_gas_status(bme680.ENABLE_GAS_MEAS)
        if MODE == 'sync':
            alternate = True

        print('Start polling:')
        while True:
            if MODE == 'raw':
                if sensor.bme.get_sensor_data():
                    output = '{0:.2f} C,{1:.2f} hPa,{2:.2f} %RH'.format(
                        sensor.bme.data.temperature,
                        sensor.bme.data.pressure,
                        sensor.bme.data.humidity
                    )
                    print(output, end='')
                    if sensor.bme.data.heat_stable:
                        print(' {0:.3f} kOhms'.format(
                            sensor.bme.data.gas_resistance/1000.0
                        ))
                    else:
                        print() # add newline
            elif MODE == 'sync':
                if sensor.read_data(do_voc=alternate):
                    print(
                        f'sensor: Temp: {sensor.get_curr_temp():.2f}F  '
                        f'Hum: {sensor.get_curr_humidity():.1f}%  '
                        f'Bar: {sensor.get_curr_barom():.1f}in  '
                        f'VOC: {sensor.get_curr_voc()/1000:.2f} kOhm  '
                    )
                alternate = not alternate # flip back and forth
            elif MODE == 'async':
                asyncio.run(sensor.read_loop())
                #print(result)
                print(
                    f'sensor: Temp: {sensor.get_last_temp():.2f}F  '
                    f'Hum: {sensor.get_last_humidity():.1f}%  '
                    f'Bar: {sensor.get_last_barom():.1f}in  '
                    f'VOC: {sensor.get_last_voc()/1000:.2f} kOhm  '
                )
                # addl time between VOC and next temp reading
                time.sleep(20)

            time.sleep(INTVL)

    except KeyboardInterrupt:
        return


if __name__ == "__main__" :
    level = logging.INFO
    #level = logging.WARNING
    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s',
                        level=level)
    test()
