import pygame
from pygame.locals import QUIT
import cv2
import threading
import sys 
import time
from datetime import datetime
import random

run = True

weekconv = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday"
}

pygame.init()

pygame.display.set_caption('Adaptive Minecraft Wallpaper')
icon = pygame.image.load("icon.png")
pygame.display.set_icon(icon)

width, height = pygame.display.Info().current_w, pygame.display.Info().current_h - 1
window = pygame.display.set_mode((width, height), pygame.NOFRAME)
CENTER = (width / 2, height / 2)


def setFont(size=11, bold = False, italic = False, font = "Azonix.otf"):
    pygfont = pygame.font.Font(font, size)

    pygfont.set_bold(bold)
    pygfont.set_italic(italic)

    return pygfont

clock = pygame.time.Clock()

pygame.font.init()
# Initialize mixer with specific settings for better compatibility
try:
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.mixer.init()
except pygame.error as e:
    print(f"Audio initialization failed: {e}")
    print("Running without audio...")

playlist = ["sounds/track1.mp3", "sounds/track2.mp3", "sounds/track3.mp3", "sounds/track4.mp3", "sounds/track5.mp3", "sounds/track6.mp3", "sounds/track7.mp3"]
random.shuffle(playlist)

background = ["sounds/rainforest.mp3", "sounds/wind.mp3"]

# Only try to play background sounds if mixer is initialized
if pygame.mixer.get_init():
    for noise in background:
        try:
            noise = pygame.mixer.Sound(noise)
            noise.play(-1).set_volume(0.3)
        except pygame.error as e:
            print(f"Background sound error: {e}")

    try:
        rain = pygame.mixer.Sound("sounds/rain.wav")
    except pygame.error as e:
        print(f"Rain sound error: {e}")
        rain = None
else:
    rain = None

baudrate = 9600
historical = []

time_window = ""
weather = ""  # Initialize as empty, will be set properly below
old_weather = ""

local_time = time.localtime()
hour = int(time.strftime("%H", local_time))

if 5 <= hour < 12:
    frame = "Morning"
    time_window = "morning"
elif 12 <= hour < 17:
    frame = "Afternoon"
    time_window = "day"
elif 17 <= hour < 20:
    frame = "Evening"
    time_window = "evening"
else:
    frame = "Night"
    time_window = "night"

# Now properly initialize weather with the correct time_window
weather = time_window

def avg(l):
    return sum(l) / len(l)



def music():
    global playlist, run
    index = 0

    # Check if mixer is initialized before proceeding
    if not pygame.mixer.get_init():
        print("Audio mixer not initialized, skipping music playback")
        return

    pygame.mixer.music.set_volume(0.1)

    while run:
        try:
            pygame.mixer.music.load(playlist[index])
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and run:
                time.sleep(0.1)  # Small delay to prevent busy waiting
            index = (index + 1) % len(playlist)
        except pygame.error as e:
            print(f"Music playback error: {e}")
            time.sleep(1)  # Wait before trying again

def weather_loop():
    global weather, old_weather, time_window, run
    while run:

        weather = f"{time_window}_to_rain"
        if rain:
            rain.set_volume(0)
            rain.play(-1)

        for i in range(0, 20):
            if rain:
                rain.set_volume((1 / 40) * i)
            time.sleep(0.25)
        time.sleep(8)

        weather = f"{time_window}_rain"  # Use time-specific rain videos

        time.sleep(random.randint(0, 60 * 5))

        weather = f"rain_to_{time_window}"

        for i in range(0, 20):
            if rain:
                rain.set_volume((1 / 40) * (20 - i))
            time.sleep(0.25)
        time.sleep(8)
        if rain:
            rain.stop()

        weather = time_window

        time.sleep(random.randint(0, 60 * 5))



if __name__ == '__main__':

    # Start background threads as daemon threads so they exit when main exits
    weather_thread = threading.Thread(target=weather_loop)
    weather_thread.daemon = True
    weather_thread.start()
    
    music_thread = threading.Thread(target=music)
    music_thread.daemon = True
    music_thread.start()

    try:
        while run:
            local_time = time.localtime()
            
            for event in pygame.event.get():
                if event.type == QUIT:
                    run = False
                    pygame.quit()
                    sys.exit()

            if not old_weather == weather:

                video = cv2.VideoCapture(f"wallpapers/{weather}.mov")
                old_weather = weather

            clock.tick(30)
            
            hour = int(time.strftime("%H", local_time))

            if 5 <= hour < 12:
                frame = "Morning"
                time_window = "morning"
            elif 12 <= hour < 17:
                frame = "Afternoon"
                time_window = "day"
            elif 17 <= hour < 20:
                frame = "Evening"
                time_window = "evening"
            else:
                frame = "Night"
                time_window = "night"

            success, video_image = video.read()
            if success:
                video_surf = pygame.image.frombuffer(video_image.tobytes(), video_image.shape[1::-1], "BGR")
                # Scale the video to fit the screen
                video_surf = pygame.transform.scale(video_surf, (width, height))
            else:
                # Video ended, restart it and read the first frame
                video = cv2.VideoCapture(f"wallpapers/{weather}.mov")
                success, video_image = video.read()
                if success:
                    video_surf = pygame.image.frombuffer(video_image.tobytes(), video_image.shape[1::-1], "BGR")
                    video_surf = pygame.transform.scale(video_surf, (width, height))
                else:
                    # If still no success, create a black screen as fallback
                    video_surf = pygame.Surface((width, height))
                    video_surf.fill((0, 0, 0))
            
            window.blit(video_surf, (0, 0))

            timetext = setFont(64).render(time.strftime("%H:%M:%S", local_time), True, (255,255,255))
        
            window.blit(timetext, (width /2 - timetext.get_width() / 2, height / 2))
            datetext = setFont(36, bold=True).render(weekconv[datetime.weekday(datetime.now())].upper(), True, (255,255,255))
            window.blit(datetext, ( width / 2 - datetext.get_width() / 2, height / 2 + 80))


            text = setFont(25).render(f"GOOD {frame}!", True, (255,255,255))
            window.blit(text, (width / 2 - text.get_width() / 2, height / 2 - 50))

            pygame.display.flip()
            
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Shutting down...")
        run = False
        pygame.quit()
        sys.exit(0)
