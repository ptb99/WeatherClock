import asyncio
import pygame

async def short_coroutine():
    print("ALPHA")
    await asyncio.sleep(0.1)
    print("BRAVO")
    await asyncio.sleep(0.1)
    print("CHARLIE")
    return None

async def long_running_coroutine():
    await short_coroutine()
    print("ONE")
    await asyncio.sleep(10)
    print("TWO")
    await asyncio.sleep(10)
    print("THREE")
    await asyncio.sleep(10)
    print("FOUR")

async def third_coroutine():
    print("GROUCHO")
    await asyncio.sleep(0.1)
    print("HARPO")
    await asyncio.sleep(0.1)
    print("ZEPPO")
    await asyncio.sleep(0.1)
    print("KARL")
    await asyncio.sleep(0.1)

async def fourth_coroutine():
    print("ONE FISH")
    await asyncio.sleep(0.1)
    print("TWO FISH")
    await asyncio.sleep(0.1)
    print("RED FISH")
    await asyncio.sleep(0.1)
    print("BLUE FISH")
    await asyncio.sleep(0.1)

async def bg_tasks():
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(long_running_coroutine())
        task2 = tg.create_task(third_coroutine())
        task3 = tg.create_task(fourth_coroutine())
    #print(f"Both tasks have completed now: {task1.result()}, {task2.result()}")


def run_once(loop):
    loop.call_soon(loop.stop)
    loop.run_forever()

#loop = asyncio.get_event_loop()
loop = asyncio.new_event_loop()


if False:
    loop.run_until_complete(short_coroutine())
    # loop.run_until_complete(asyncio.gather(
    #     long_running_coroutine(),
    #     third_coroutine(),
    #     fourth_coroutine()))
    loop.run_until_complete(bg_tasks())
else:
    #loop.run_until_complete(short_coroutine())
    task = loop.create_task(long_running_coroutine())
    task2 = loop.create_task(fourth_coroutine())


pygame.init()

blob_yposition=30
blob_yspeed=0
achievement=False

gravity=1

screen_size=640,480
screen=pygame.display.set_mode(screen_size)

clock=pygame.time.Clock()
running=True
flying_frames=0
best=0
color=(50,50,50)
font=pygame.font.SysFont("Helvetica Neue,Helvetica,Ubuntu Sans,Bitstream Vera Sans,DejaVu Sans,Latin Modern Sans,Liberation Sans,Nimbus Sans L,Noto Sans,Calibri,Futura,Beteckna,Arial", 16)

while running:
    clock.tick(30)

    events=pygame.event.get()
    for e in events:
        if e.type==pygame.QUIT:
            running=False
        if e.type==pygame.KEYDOWN and e.key==pygame.K_UP:
            blob_yspeed+=10

    # ...
    # move sprites around, collision detection, etc

    blob_yposition+=blob_yspeed
    blob_yspeed-=gravity

    if blob_yposition<=30:
        blob_yspeed=0
        blob_yposition=30
        flying_frames=0
    else:
        flying_frames+=1
        if flying_frames>best:
            best=flying_frames
        if not achievement and best>300:
            # 10 seconds
            print("ACHIEVEMENT UNLOCKED")
            achievement=True
            color=(100,0,0)

    if blob_yposition>480:
        blob_yposition=480
        blob_yspeed=-1*abs(blob_yspeed)

    # ...
    # draw 
    screen.fill((255,255,255))

    pygame.draw.rect(screen,color,
                        pygame.Rect(screen_size[0]/2,
                                    screen_size[1]-blob_yposition,
                                    18,25))
    fps=clock.get_fps()
    message=f"current:{flying_frames//30},   best:{best//30},   fps:{fps}"
    surf=font.render(message, True, (0,0,0))
    screen.blit(surf,(0,0)) 

    pygame.display.update()
    run_once(loop)

# while len(asyncio.all_tasks(loop)):
#     print("Running cleanup loop")
#     loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
#     #loop.run_until_complete(loop.shutdown_asyncgens())

print("Running cleanup loop")
loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))

loop.close()
print("Thank you for playing!")




# loop = asyncio.get_event_loop()
# loop.run_until_complete(short_coroutine())

# task = loop.create_task(long_running_coroutine())
# task2 = loop.create_task(fourth_coroutine())

# def run_once(loop):
#     loop.call_soon(loop.stop)
#     loop.run_forever()

# while True:
#     run_once(loop)
#     if input("Press RETURN >")=="exit":
#         break
# loop.close()

#     # tell event loop to run once
#     # if there are no i/o events, this might return right away
#     # if there are events or tasks that don't need to wait for i/o, then
#     # run ONE task until the next "await" statement
#     run_once(loop)

#     # we run this *after* display.update(), but *before* 
#     # clock.tick(fps) and getting input events. This way i/o only eats
#     # into the time when clock.tick(fps) would wait anyway.

# while len(asyncio.Task.all_tasks(loop)):
#     run_once(loop)
#     loop.shutdown_asyncgens()
#     loop.close()
#     print("Thank you for playing!")


## see also: https://github.com/AlexElvers/pygame-with-asyncio
