##
## Wrapper for fetching current readings from OpenWeatherMap.org
##

import logging
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
        self.logger = logging.getLogger()
        self.temperature = None
        self.city_name = None
        self.main_text = None
        self.description = None
        self.icon = None
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

