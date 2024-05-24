#! /usr/bin/python
##
## basic clock/weather app using pygame
##


import pygame as pg
import paho.mqtt.client as mqtt
import time
import datetime
import json
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
                #print("Weather Response is:", value)
                weather = json.loads(value)
                return weather
            else:
                print(f'Weather fetch failed: status={resp.status}, reason={resp.reason}')
                return None         # ???

        # response = urllib.request.urlopen(DATA_SOURCE)
        # if response.getcode() == 200:
        #     value = response.read()
        #     #print("Response is", value)
        #     weather = json.loads(value.decode('utf-8'))
        #     return weather
        # else:
        #     return None         # ???



# The callback for when the client receives a CONNACK response from the server.
def mqtt_on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    userdata.on_connect(client)

# The callback for when a PUBLISH message is received from the server.
def mqtt_on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
    userdata.on_message(client, msg)

class MQTT_Listener:
    def __init__(self, secure=False, persist=False):
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
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            userdata=self,
            client_id=client_id, clean_session=cleanup,
            transport='tcp'
        )
            # protocol=mqtt.MQTTProtocolVersion.MQTTv311,
        mqttc.username_pw_set(            
            username=secrets["AIO_USERNAME"],
            password=secrets["AIO_KEY"],
        )
        mqttc.on_connect = mqtt_on_connect
        mqttc.on_message = mqtt_on_message
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

    def on_connect(self, client):
        # Subscribe to Group
        print('MQTT on_connect() called.')
        client.subscribe("tpavell/groups/Porch/json")

    def on_message(self, client, msg):
        #print('MQTT on_message() called for', msg.topic)
        data = json.loads(msg.payload.decode('utf-8'))
        #print('MQTT msg data =', data)
        for key,val in data['feeds'].items():
            #logger.info(f'MQTT update: {key} = {val}')
            self.values[key] = float(val)

    def get_curr_values(self):
        return self.values

# # IP address of your MQTT broker, using ipconfig to look up it
# client.connect('192.168.1.109', 1883)
# # start a new thread
# client.loop_start()
# # 'greenhouse/#' means subscribe all topic under greenhouse
# client.subscribe('greenhouse/#')


def get_time_strings():
    """Wrapper function to convert current time/date into a pair of strings."""
    USE_AMPM = True
    now = datetime.datetime.now()
    if USE_AMPM:
        timestr = now.strftime('%l:%M:%S %P')
    else:
        timestr = now.strftime('%H:%M:%S')
    datestr = now.strftime('%a, %b %e %Y')
    # 'Tue, Dec 7 2024'

    return timestr, datestr


class App:
    WIDTH = 1024
    HEIGHT = 600

    def __init__(self):
        self.running = True
        self.display = None
        self.fonts = None
        self.size = (self.WIDTH/2, self.HEIGHT/2)
        self.bgcolor = (60, 0, 60)    # dark purple
        self.fgcolor = (255, 255, 0)  # yellow
        #self.fgcolor = (0, 255, 0)   # green
        self.weather = OpenWeather()
        self.next_update = 0
        self.mqtt = MQTT_Listener()

    def on_init(self):
        pg.init()

        size = (pg.display.Info().current_w, 
                pg.display.Info().current_h)
        print("Default Framebuffer size: %d x %d" % (size[0], size[1]))
        print(f'Chosen window size: {self.size}')

        self.display = pg.display.set_mode(self.size, pg.SHOWN)
        # Use pygame.FULLSCREEN for kiosk mode

        print('PyGame driver =', pg.display.get_driver())

        # Initialise font support
        pg.font.init()
        self.fonts = {}
        self.fonts['CLOCK'] = pg.font.SysFont('freesans', 80)
        self.fonts['MEDIUM'] = pg.font.SysFont('freesans', 24)
        self.fonts['SMALL'] = pg.font.SysFont('freesans', 16, bold=True)
        self.fonts['ICON'] = pg.font.Font('meteocons.ttf', 48)

        self.running = True
        return self.running
 
    def on_event(self, event):
        if event.type == pg.QUIT:
            self.running = False
        elif event.type == pg.KEYDOWN:
            keys = pg.key.get_pressed()
            if keys[pg.K_q]:
                self.running = False

    def on_loop(self):
        now = time.time()
        if now > self.next_update:
            self.weather.update_weather(self.weather.get_weather_info())
            print(f'Weather: {self.weather.city_name} - {self.weather.temperature}')
            # wait 15 min
            self.next_update = now + 15 * 60 

        # waiting too long hurts keypress latency
        pg.time.wait(100)       # in msec


    def on_render(self):
        self.display.fill(self.bgcolor)

        timestr, datestr = get_time_strings()
        surface = self.fonts['CLOCK'].render(
            timestr,
            True, 
            self.fgcolor)
        self.display.blit(surface, (30, 30))
        surface = self.fonts['MEDIUM'].render(
            datestr,
            True, 
            self.fgcolor)
        self.display.blit(surface, (50, 110))

        surface = self.fonts['MEDIUM'].render(
            self.weather.city_name, 
            True, 
            self.fgcolor)
        self.display.blit(surface, (50, 190))
        surface = self.fonts['ICON'].render(
            self.weather.icon, 
            True, 
            self.fgcolor)
        self.display.blit(surface, (50, 230))
        surface = self.fonts['MEDIUM'].render(
            self.weather.temperature, 
            True, 
            self.fgcolor)
        self.display.blit(surface, (120, 230))
        surface = self.fonts['SMALL'].render(
            self.weather.description, 
            True, 
            self.fgcolor)
        self.display.blit(surface, (120, 260))

        probe_vals = self.mqtt.get_curr_values()
        surface = self.fonts['MEDIUM'].render(
            'Outdoor probe',
            True, 
            self.fgcolor)
        self.display.blit(surface, (300, 190))
        temp = probe_vals.get('alt-temp', 0)
        surface = self.fonts['MEDIUM'].render(
            f'{temp:.0f} °F',
            True, 
            self.fgcolor)
        self.display.blit(surface, (300, 230))
        batt = probe_vals.get('battery-charge', 42)
        surface = self.fonts['SMALL'].render(
            f'Bat: {batt:.0f} %',
            True, 
            self.fgcolor)
        self.display.blit(surface, (300, 260))
        humid = probe_vals.get('alt-humidity', 0)
        surface = self.fonts['SMALL'].render(
            f'Hum: {humid:.1f} %',
            True, 
            self.fgcolor)
        self.display.blit(surface, (390, 230))
        bar = probe_vals.get('pressure', 42)
        surface = self.fonts['SMALL'].render(
            f'Bar: {bar:.1f} in',
            True, 
            self.fgcolor)
        self.display.blit(surface, (390, 260))

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
    theApp = App()
    theApp.on_execute()

    
if __name__ == "__main__" :
    main()



# Font list:
# c059
# caladea
# cantarell
# carlito
# comfortaa
# d050000l
# dejavusans
# dejavusansmono
# droidarabickufi
# droidsans
# droidsansarmenian
# droidsansdevanagari
# droidsansethiopic
# droidsansfallback
# droidsansgeorgian
# droidsanshebrew
# droidsansjapanese
# droidsanstamil
# droidsansthai
# freesans
# jomolhari
# khmerossystem
# latinmodernmono
# latinmodernmonocaps
# latinmodernmonolight
# latinmodernmonolightcond
# latinmodernmonoprop
# latinmodernmonoproplight
# latinmodernmonoslanted
# latinmodernroman
# latinmodernromancaps
# latinmodernromandemi
# latinmodernromandunhill
# latinmodernromanslanted
# latinmodernromanunslanted
# latinmodernsans
# latinmodernsansdemicond
# latinmodernsansquotation
# liberationmono
# liberationsans
# liberationserif
# lohitassamese
# lohitbengali
# lohitdevanagari
# lohitgujarati
# lohitkannada
# lohitmarathi
# lohitodia
# lohittamil
# lohittelugu
# mingzat
# nimbusmonops
# nimbusroman
# nimbussans
# nimbussansnarrow
# notocoloremoji
# notonaskharabic
# notosans
# notosansarmenian
# notosanscanadianaboriginal
# notosanscherokee
# notosanscjkhk
# notosanscjkjp
# notosanscjkkr
# notosanscjksc
# notosanscjktc
# notosansethiopic
# notosansgeorgian
# notosansgurmukhi
# notosanshebrew
# notosanslao
# notosansmath
# notosansmono
# notosansmonocjkhk
# notosansmonocjkjp
# notosansmonocjkkr
# notosansmonocjksc
# notosansmonocjktc
# notosanssinhala
# notosansthaana
# notoserif
# nuosusil
# opensans
# opensymbol
# p052
# padauk
# paktypenaskhbasic
# ritmeeranew
# sourcecodepro
# standardsymbolsps
# stix
# symbola
# urwbookman
# urwgothic
# z003
