#! /usr/bin/python
##
## basic clock/weather app using pygame
##


import pygame as pg
import time
import datetime
import asyncio
import logging

#from secrets import secrets
#from weather import OpenWeather
from mqtt import MQTT_Listener
from sensor import BME_Probe


def run_once(loop):
    """Helper function to run all loop Tasks that are ready and then return."""
    loop.call_soon(loop.stop)
    loop.run_forever()


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
    #BGCOLOR = (30, 0, 40)    # dark purple
    BGCOLOR = (0, 0, 0)       # black
    #FGCOLOR = (255, 255, 120)  # light yellow
    FGCOLOR = (178, 235, 242)  # light blue
    FGWARNING = (255, 255, 0)  # yellow
    FGERROR = (255, 0 , 0)     # red
    MQTT_SERVER = "io.adafruit.com"
    UPDATE_INTERVAL = 5 * 60

    def __init__(self):
        self.logger = logging.getLogger()
        self.running = True
        self.display = None
        self.fonts = None
        self.size = (self.WIDTH, self.HEIGHT)
        self.next_update = 0
        self.bgloop = asyncio.new_event_loop()
        # self.weather = OpenWeather()
        self.mqtt = MQTT_Listener(host=self.MQTT_SERVER, secure=True)
        self.sensor = BME_Probe()

    def on_init(self):
        pg.init()

        # print out some info
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
        self.fonts['LARGE'] = pg.font.SysFont('freesans', 120)
        self.fonts['MEDIUM'] = pg.font.SysFont('freesans', 48)
        self.fonts['SMALL'] = pg.font.SysFont('freesans', 32)
        #self.fonts['SMALL'] = pg.font.SysFont('freesans', 16, bold=True)
        #self.fonts['ICON'] = pg.font.Font('meteocons.ttf', 48)

        # Hide mouse cursor:
        pg.mouse.set_visible(False)

        self.clock = pg.time.Clock()
        self.running = True
        time.sleep(0.1)           # brief delay to let driver init settle
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
        now = time.time()
        if now > self.next_update:
            self.do_update()
            self.next_update = now + self.UPDATE_INTERVAL

        # run any BG tasks
        run_once(self.bgloop)

        # waiting too long hurts keypress latency
        #pg.time.wait(100)       # in msec
        self.clock.tick(1)


    async def update_start(self):
        #start = time.perf_counter()
        #start = time.time()

        results = await self.sensor.read_loop()

        #stop = time.time()
        #duration = (stop - start) * 1000

        return results

    async def update_end(self, task):
        # wait for the BME680 update task to finish
        await task
        values = [('Indoor-Temp', self.sensor.get_last_temp()),
                  ('Indoor-Humidity', self.sensor.get_last_humidity()),
                  ('Indoor-Pressure', self.sensor.get_last_barom()),
                  ('Indoor-VOC', self.sensor.get_last_voc()),
                  ]
        # in theory, this should be an async publish
        self.mqtt.publish_indoor(values)

    def do_update(self):
        self.logger.debug('do_update() called...')

        task = self.bgloop.create_task(self.update_start())
        self.bgloop.create_task(self.update_end(task))

        #     self.weather.update_weather(self.weather.get_weather_info())
        #     self.logger.info(
        #         f'Weather: {self.weather.city_name} - {self.weather.temperature}'
        #     )

        return True             # ??


    def on_render(self):
        self.display.fill(self.BGCOLOR)

        timestr, datestr = get_time_strings()
        surface = self.fonts['CLOCK'].render(
            timestr,
            True, 
            self.FGCOLOR)
        self.display.blit(surface, (80, 50))
        surface = self.fonts['MEDIUM'].render(
            datestr,
            True, 
            self.FGCOLOR)
        self.display.blit(surface, (260, 270))

        # surface = self.fonts['MEDIUM'].render(
        #     self.weather.city_name,
        #     True,
        #     self.FGCOLOR)
        # self.display.blit(surface, (50, 190))
        # surface = self.fonts['ICON'].render(
        #     self.weather.icon,
        #     True,
        #     self.FGCOLOR)
        # self.display.blit(surface, (50, 230))
        # surface = self.fonts['MEDIUM'].render(
        #     self.weather.temperature,
        #     True,
        #     self.FGCOLOR)
        # self.display.blit(surface, (120, 230))
        # surface = self.fonts['SMALL'].render(
        #     self.weather.description,
        #     True,
        #     self.FGCOLOR)
        # self.display.blit(surface, (120, 260))

        ## Outdoor block
        block_x = 780
        probe_vals = self.mqtt.get_curr_values()
        surface = self.fonts['SMALL'].render(
            'Outdoor:',
            True, 
            self.FGCOLOR)
        self.display.blit(surface, (block_x+15, 400))
        temp = probe_vals.get('alt-temp', 0)
        surface = self.fonts['LARGE'].render(
            f'{temp:.0f}°',
            True, 
            self.FGCOLOR)
        self.display.blit(surface, (block_x, 450))
        block_x = 560
        humid = probe_vals.get('alt-humidity', 0)
        surface = self.fonts['SMALL'].render(
            f'Hum:  {humid:.0f} %',
            True, 
            self.FGCOLOR)
        self.display.blit(surface, (block_x, 400))
        bar = probe_vals.get('pressure', 0)
        surface = self.fonts['SMALL'].render(
            f'Bar:  {bar:.1f} in',
            True, 
            self.FGCOLOR)
        self.display.blit(surface, (block_x, 460))
        batt = probe_vals.get('battery-charge', 0)
        surface = self.fonts['SMALL'].render(
            f'Bat:  {batt:.0f} %',
            True, 
            self.FGCOLOR)
        self.display.blit(surface, (block_x, 520))

        ## Indoor block
        block_x = 50
        surface = self.fonts['SMALL'].render(
            'Indoor:',
            True,
            self.FGCOLOR)
        self.display.blit(surface, (block_x+15, 400))
        temp = self.sensor.get_last_temp()
        surface = self.fonts['LARGE'].render(
            f'{temp:.0f}°',
            True,
            self.FGCOLOR)
        self.display.blit(surface, (block_x, 450))
        block_x = 290
        humid = self.sensor.get_last_humidity()
        surface = self.fonts['SMALL'].render(
            f'Hum:  {humid:.0f} %',
            True,
            self.FGCOLOR)
        self.display.blit(surface, (block_x, 400))
        barom = self.sensor.get_last_barom()
        surface = self.fonts['SMALL'].render(
            f'Bar:  {barom:.1f} in',
            True,
            self.FGCOLOR)
        self.display.blit(surface, (block_x, 460))
        voc = self.sensor.get_last_voc()/1000
        if voc < 20:
            color = self.FGERROR
        elif voc < 100:
            color = self.FGWARNING
        else:
            color = self.FGCOLOR
        surface = self.fonts['SMALL'].render(
            f'VOC:  {voc:.0f} kΩ',
            True,
            color)
        self.display.blit(surface, (block_x, 520))

        pad = 10
        rect = (pad, pad, self.WIDTH-2*pad, self.HEIGHT-2*pad)
        pg.draw.rect(self.display, self.FGCOLOR, rect, width=1)

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
