#! /usr/bin/python
##
## basic clock/weather app using pygame
##


import pygame as pg
import paho.mqtt.client as mqtt
#import time
import datetime
import json
import logging
import urllib.request
import urllib.parse

from secrets import secrets


# Map the OpenWeatherMap icon code to the appropriate font character
# See http://www.alessioatzeni.com/meteocons/ for icons
ICON_MAP = {
    "01d": "B",
    "01n": "C",
    "02d": "H",
    "02n": "I",
    "03d": "N",
    "03n": "N",
    "04d": "Y",
    "04n": "Y",
    "09d": "Q",
    "09n": "Q",
    "10d": "R",
    "10n": "R",
    "11d": "Z",
    "11n": "Z",
    "13d": "W",
    "13n": "W",
    "50d": "J",
    "50n": "K",
}

class OpenWeather:
    """Class to wrap API for OpenWeather.org"""
    # Use cityname, country code where countrycode is ISO3166 format.
    # E.g. "New York, US" or "London, GB"
    LOCATION = "San Jose, US"
    DATA_SOURCE_URL = "http://api.openweathermap.org/data/2.5/weather"

    def __init__(self):
        self.logger = logging.getLogger()
        self.temperature = None
        self.city_name = None
        self.main_text = None
        self.description = None
        #self.weather_icon = None
        #self.time_text = None
        self.use_celsius = False # set in constructor?

    def update_weather(self, weather):
        self.city_name = weather["name"] + ", " + weather["sys"]["country"]
        self.main_text = weather["weather"][0]["main"]
        self.icon = ICON_MAP[weather["weather"][0]["icon"]]

        d = weather["weather"][0]["description"]
        self.description = d[0].upper() + d[1:]
        # "thunderstorm with heavy drizzle"

        temp = weather["main"]["temp"] - 273.15  # its...in kelvin
        if self.use_celsius:
            self.temperature = f'{temp:.1f} °C'
        else:
            temp = ((temp * 9 / 5) + 32)
            self.temperature = f'{temp:.1f} °F'

    def get_weather_info(self):
        # You'll need to get a token from openweathermap.org, put it here:
        OPEN_WEATHER_TOKEN = secrets['OPEN_WEATHER_TOKEN']
        if len(OPEN_WEATHER_TOKEN) == 0:
            raise RuntimeError(
                "You need to set your token first. If you don't already have one,"
                " you can register for a free account at "
                "https://home.openweathermap.org/users/sign_up"
            )

        # Set up where we'll be fetching data from
        params = {"q": self.LOCATION, "appid": OPEN_WEATHER_TOKEN}
        DATA_SOURCE = self.DATA_SOURCE_URL + "?" + urllib.parse.urlencode(params)
        # quoted_location = LOCATION.replace(' ', '+')
        # DATA_SOURCE = ( DATA_SOURCE_URL + "?" + "q=" + quoted_location +
        #                 "&appid=" + OPEN_WEATHER_TOKEN )

        with urllib.request.urlopen(DATA_SOURCE) as resp:
            ## urllib will raise an exception if not 200/etc
            if resp.status == 200:
                value = resp.read().decode('utf-8')
                self.logger.debug("Weather Response is: {value}")
                weather = json.loads(value)
                return weather
            else:
                self.logger.info(
                    f'Weather fetch failed: status={resp.status}, reason={resp.reason}'
                )
                return None         # ???

        # response = urllib.request.urlopen(DATA_SOURCE)
        # if response.getcode() == 200:
        #     value = response.read()
        #     #print("Response is", value)
        #     weather = json.loads(value.decode('utf-8'))
        #     return weather
        # else:
        #     return None         # ???



class MQTT_Listener:
    def __init__(self, secure=False, persist=False):
        self.logger = logging.getLogger()
        self.values = {}
        # Initialize a new MQTT Client object
        if persist:
            # use persistent conn and queued messages
            client_id = 'Clock_123'
            cleanup = False
        else:
            client_id = ''
            cleanup = True
        mqttc = mqtt.Client(
            userdata=self,
            client_id=client_id, clean_session=cleanup,
            transport='tcp'
        )
            # callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            # protocol=mqtt.MQTTProtocolVersion.MQTTv311,
        mqttc.username_pw_set(            
            username=secrets["AIO_USERNAME"],
            password=secrets["AIO_KEY"],
        )
        mqttc.on_connect = self.on_connect
        mqttc.on_message = self.on_message
        # Alt:
        #mqttc.message_callback_add('Porch/#', mqtt_on_message)
        if secure:
            mqttc.tls_set_context()
            mqttc.connect(
                host="io.adafruit.com", port=8883, keepalive=60
            )
        else:
            mqttc.connect(
                host="io.adafruit.com", port=1883, keepalive=60
            )
        # start a new thread
        mqttc.loop_start()
        self.mqtt_client = mqttc

    # For v2, use this signature:
    #def on_connect(self, client, userdata, flags, reason_code, properties):
    def on_connect(self, client, userdata, flags, reason_code):
        # Subscribe to Group
        client.subscribe("tpavell/groups/Porch/json")

    def on_message(self, client, userdata, msg):
        self.logger.debug(f"MQTT msg: {msg.topic} {str(msg.payload)}")
        data = json.loads(msg.payload.decode('utf-8'))
        for key,val in data['feeds'].items():
            #logger.info(f'MQTT update: {key} = {val}')
            self.values[key] = float(val)

    def get_curr_values(self):
        return self.values


def get_time_strings():
    """Wrapper function to convert current time/date into a pair of strings."""
    USE_AMPM = True
    now = datetime.datetime.now()
    if USE_AMPM:
        timestr = now.strftime('%l:%M %P')
    else:
        timestr = now.strftime('%H:%M')
    #datestr = now.strftime('%a, %b %e, %Y')
    # 'Tue, Dec 7, 2024'
    datestr = now.strftime('%A, %B %e, %Y')
    # 'Tuesday, December 7, 2024'

    return timestr, datestr


class App:
    WIDTH = 1024
    HEIGHT = 600

    def __init__(self):
        self.logger = logging.getLogger()
        self.running = True
        self.display = None
        self.fonts = None
        self.size = (self.WIDTH, self.HEIGHT)
        self.bgcolor = (30, 0, 40)    # dark purple
        self.fgcolor = (255, 255, 120)  # yellow
        #self.fgcolor = (0, 255, 0)   # green
        #self.weather = OpenWeather()
        #self.next_update = 0
        self.mqtt = MQTT_Listener(secure=True, persist=False)

    def on_init(self):
        pg.init()

        fb_size = (pg.display.Info().current_w,
                   pg.display.Info().current_h)
        self.logger.info("Default Framebuffer size: %d x %d" %
                         (fb_size[0], fb_size[1]))
        self.logger.info(f'Chosen window size: {self.size}')

        # Use pygame.FULLSCREEN for kiosk mode
        if fb_size[1] > self.size[1] + 100:
            self.display = pg.display.set_mode(self.size, pg.SHOWN)
        else:
            self.display = pg.display.set_mode(self.size, pg.FULLSCREEN)

        self.logger.info(f'PyGame driver = {pg.display.get_driver()}')

        # Initialise font support
        pg.font.init()
        self.fonts = {}
        self.fonts['CLOCK'] = pg.font.SysFont('freesans', 200)
        self.fonts['LARGE'] = pg.font.SysFont('freesans', 100)
        self.fonts['MEDIUM'] = pg.font.SysFont('freesans', 48)
        self.fonts['SMALL'] = pg.font.SysFont('freesans', 32)
        #self.fonts['SMALL'] = pg.font.SysFont('freesans', 16, bold=True)
        #self.fonts['ICON'] = pg.font.Font('meteocons.ttf', 48)

        # Hide mouse cursor:
        pg.mouse.set_visible(False)

        self.running = True
        return self.running

 
    def on_event(self, event):
        if event.type == pg.QUIT:
            self.running = False
        elif event.type == pg.KEYDOWN:
            keys = pg.key.get_pressed()
            if keys[pg.K_q]:
                self.running = False
        # Could maybe use mouse-presses for UI buttons (someday)...

    def on_loop(self):
        # now = time.time()
        # if now > self.next_update:
        #     self.weather.update_weather(self.weather.get_weather_info())
        #     self.logger.info(
        #         f'Weather: {self.weather.city_name} - {self.weather.temperature}'
        #     )
        #     # wait 15 min
        #     self.next_update = now + 15 * 60

        # waiting too long hurts keypress latency
        pg.time.wait(100)       # in msec


    def on_render(self):
        self.display.fill(self.bgcolor)

        timestr, datestr = get_time_strings()
        surface = self.fonts['CLOCK'].render(
            timestr,
            True, 
            self.fgcolor)
        self.display.blit(surface, (80, 50))
        surface = self.fonts['MEDIUM'].render(
            datestr,
            True, 
            self.fgcolor)
        self.display.blit(surface, (270, 270))

        # surface = self.fonts['MEDIUM'].render(
        #     self.weather.city_name,
        #     True,
        #     self.fgcolor)
        # self.display.blit(surface, (50, 190))
        # surface = self.fonts['ICON'].render(
        #     self.weather.icon,
        #     True,
        #     self.fgcolor)
        # self.display.blit(surface, (50, 230))
        # surface = self.fonts['MEDIUM'].render(
        #     self.weather.temperature,
        #     True,
        #     self.fgcolor)
        # self.display.blit(surface, (120, 230))
        # surface = self.fonts['SMALL'].render(
        #     self.weather.description,
        #     True,
        #     self.fgcolor)
        # self.display.blit(surface, (120, 260))

        probe_vals = self.mqtt.get_curr_values()
        surface = self.fonts['SMALL'].render(
            'Outdoor:',
            True, 
            self.fgcolor)
        self.display.blit(surface, (110, 400))
        temp = probe_vals.get('alt-temp', 0)
        surface = self.fonts['LARGE'].render(
            f'{temp:.0f}°F',
            True, 
            self.fgcolor)
        self.display.blit(surface, (100, 450))

        humid = probe_vals.get('alt-humidity', 0)
        surface = self.fonts['SMALL'].render(
            f'Hum:  {humid:.0f} %',
            True, 
            self.fgcolor)
        self.display.blit(surface, (600, 400))
        bar = probe_vals.get('pressure', 0)
        surface = self.fonts['SMALL'].render(
            f'Bar:  {bar:.1f} in',
            True, 
            self.fgcolor)
        self.display.blit(surface, (600, 450))
        batt = probe_vals.get('battery-charge', 0)
        surface = self.fonts['SMALL'].render(
            f'Bat:  {batt:.0f} %',
            True, 
            self.fgcolor)
        self.display.blit(surface, (600, 500))

        pad = 10
        rect = (pad, pad, self.WIDTH-2*pad, self.HEIGHT-2*pad)
        pg.draw.rect(self.display, self.fgcolor, rect, width=1)

        pg.display.update()


    def on_cleanup(self):
        pg.quit()

    def on_execute(self):
        if self.on_init() == False:
            self.running = False
 
        while( self.running ):
            for event in pg.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()

        self.on_cleanup()


def main():
    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s',
                        level=logging.INFO)

    theApp = App()
    theApp.on_execute()

    
if __name__ == "__main__" :
    # Any use for argv's?
    main()


## RPi output:
# PyGame driver = KMSDRM
# Font list:
# c059
# cantarell
# d050000l
# dejavusans
# dejavusansmono
# dejavuserif
# droidsansfallback
# freemono
# freesans
# freeserif
# liberationmono
# liberationsans
# liberationserif
# nimbusmonops
# nimbusroman
# nimbussans
# nimbussansnarrow
# notomono
# notosansmono
# p052
# piboto
# pibotocondensed
# pibotolt
# quicksand
# quicksandlight
# quicksandmedium
# standardsymbolsps
# urwbookman
# urwgothic
# z003
