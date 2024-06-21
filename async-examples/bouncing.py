#! /usr/bin/python
##
## basic clock/weather app using pygame
##


import pygame as pg
import time
import asyncio
import logging


def run_once(loop):
    """Helper function to run all loop Tasks that are ready and then return.""" 
    loop.call_soon(loop.stop)
    loop.run_forever()


async def dummy_task():
    #start = time.perf_counter()
    start = time.time()
    await asyncio.sleep(0.200)
    stop = time.time()
    duration = (stop - start) * 1000
    return f'do_update() called for duration {duration:.3f} msec'


class App:
    WIDTH = 480
    HEIGHT = 320
    BGCOLOR = (60, 0, 80)    # dark purple
    FGCOLOR = (255, 255, 120)  # light yellow
    UPDATE_INTERVAL = 20

    def __init__(self):
        self.logger = logging.getLogger()
        self.running = True
        self.display = None
        self.fonts = None
        self.size = (self.WIDTH, self.HEIGHT)
        self.next_update = 0
        self.speed = [2, 2]
        self.bgloop = asyncio.new_event_loop()

    def on_init(self):
        pg.init()
        self.screen = pg.display.set_mode(self.size, pg.SHOWN)
        self.clock = pg.time.Clock()
        self.logger.info(f'PyGame {pg.__version__} driver = {pg.display.get_driver()}')

        self.ball = pg.image.load("images/ball.gif")
        self.ballrect = self.ball.get_rect()

        # Initialise font support
        pg.font.init()
        self.font = pg.font.SysFont('freesans', 16, bold=True)

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

        self.ballrect = self.ballrect.move(self.speed)
        if self.ballrect.left < 0 or self.ballrect.right > self.WIDTH:
            self.speed[0] = -self.speed[0]
        if self.ballrect.top < 0 or self.ballrect.bottom > self.HEIGHT:
            self.speed[1] = -self.speed[1]

        # run any BG tasks
        run_once(self.bgloop)

        # waiting too long hurts keypress latency
        #pg.time.wait(10)       # in msec
        self.clock.tick(100)

    async def done_callback(self, task):
        await task
        self.logger.info(f'do_update() result = {task.result()}')

    def do_update(self):
        #self.logger.debug('do_update() called...')
        task = self.bgloop.create_task(dummy_task())
        self.bgloop.create_task(self.done_callback(task))
        return True

    def on_render(self):
        self.screen.fill(self.BGCOLOR)
        self.screen.blit(self.ball, self.ballrect)

        fps = self.clock.get_fps()
        surf = self.font.render(f'fps: {fps:.1f}', True, self.FGCOLOR)
        self.screen.blit(surf, (10,5)) 

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
