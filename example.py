#! /usr/bin/python
##
## basic pygame example
##


import pygame
#import pygame as pg
#from pygame.locals import *

 
class App:
    def __init__(self):
        self._running = True
        self._display_surf = None
        self._image_surf = None
        #self.IMAGE_NAME = 'cat.bmp'
        self.IMAGE_NAME = "myimage.jpg"
        self.size = (640, 480)
 
    def on_init(self):
        pygame.init()

        size = (pygame.display.Info().current_w, 
                pygame.display.Info().current_h)
        print("Default Framebuffer size: %d x %d" % (size[0], size[1]))

        self._display_surf = pygame.display.set_mode(
            self.size, 
            pygame.SHOWN
        )
        # Use pygame.FULLSCREEN for kiosk mode

        ## Modes:
        # pygame.FULLSCREEN    create a fullscreen display
        # pygame.DOUBLEBUF     only applicable with OPENGL
        # pygame.HWSURFACE     (obsolete in pygame 2) hardware accelerated, only in FULLSCREEN
        # pygame.OPENGL        create an OpenGL-renderable display
        # pygame.RESIZABLE     display window should be sizeable
        # pygame.NOFRAME       display window will have no border or controls
        # pygame.SCALED        resolution depends on desktop size and scale graphics
        # pygame.SHOWN         window is opened in visible mode (default)
        # pygame.HIDDEN        window is opened in hidden mode
        print('PyGame driver =', pygame.display.get_driver())

        self._running = True
        self._image_surf = pygame.image.load('images/' + self.IMAGE_NAME).convert()
        # Initialise font support
        pygame.font.init()

        print('Font list:')
        for f in pygame.font.get_fonts():
            print(f)

        return True
 
    def on_event(self, event):
        if event.type == pygame.QUIT:
            self._running = False
        elif event.type == pygame.KEYDOWN:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_q]:
                self._running = False

    def on_loop(self):
        pass

    def on_render(self):
        self._display_surf.blit(self._image_surf, (0,0))

        font = pygame.font.Font(None, 64)
        text_surface = font.render('Test', True, (255, 255, 0))  # Yellow text
        self._display_surf.blit(text_surface, (400, 300))

        pygame.display.update()

    def on_cleanup(self):
        pygame.quit()
 
    def on_execute(self):
        if self.on_init() == False:
            self._running = False
 
        while( self._running ):
            for event in pygame.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()
        self.on_cleanup()


def main():
    theApp = App()
    theApp.on_execute()
    
if __name__ == "__main__" :
    main()
