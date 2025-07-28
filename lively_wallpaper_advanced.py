import time
import random
import subprocess
import threading
import os
import pygame
import sys
import configparser
from datetime import datetime

class AdaptiveWallpaperConfig:
    def __init__(self, config_file="config.ini"):
        self.config = configparser.ConfigParser()
        if os.path.exists(config_file):
            self.config.read(config_file)
        else:
            print(f"Config file {config_file} not found, using defaults")
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration"""
        self.config['PATHS'] = {
            'livelycu_path': r'C:\Users\jerrb\Downloads\lively_command_utility\livelycu.exe',
            'wallpaper_dir': 'wallpapers',
            'sound_dir': 'sounds'
        }
        self.config['TIMING'] = {
            'morning_start': '5',
            'day_start': '12',
            'evening_start': '17',
            'night_start': '20',
            'min_rain_duration': '30',
            'max_rain_duration': '300',
            'min_clear_duration': '60',
            'max_clear_duration': '300',
            'transition_duration': '8'
        }
        self.config['AUDIO'] = {
            'background_volume': '0.3',
            'music_volume': '0.1',
            'rain_fade_steps': '20',
            'rain_fade_delay': '0.25',
            'enable_background_sounds': 'true',
            'enable_music': 'true',
            'enable_rain_sounds': 'true'
        }
        self.config['DEBUG'] = {
            'verbose_logging': 'true',
            'show_status_updates': 'true',
            'status_update_interval': '5'
        }
    
    def get(self, section, key, fallback=None):
        return self.config.get(section, key, fallback=fallback)
    
    def getboolean(self, section, key, fallback=False):
        return self.config.getboolean(section, key, fallback=fallback)
    
    def getint(self, section, key, fallback=0):
        return self.config.getint(section, key, fallback=fallback)
    
    def getfloat(self, section, key, fallback=0.0):
        return self.config.getfloat(section, key, fallback=fallback)

class AdaptiveWallpaper:
    def __init__(self, config_file="config.ini"):
        self.config = AdaptiveWallpaperConfig(config_file)
        self.run = True
        self.current_weather = ""
        self.time_window = ""
        self.rain_playing = False
        self.rain_sound = None
        self.background_sounds = []
        self.music_playlist = []
        self.current_music_index = 0
        
        # Load configuration
        self.livelycu_path = self.config.get('PATHS', 'livelycu_path')
        self.wallpaper_dir = self.config.get('PATHS', 'wallpaper_dir')
        self.sound_dir = self.config.get('PATHS', 'sound_dir')
        
        # Initialize audio if enabled
        if self._audio_enabled():
            self.init_audio()
        
    def _audio_enabled(self):
        """Check if any audio features are enabled"""
        return (self.config.getboolean('AUDIO', 'enable_background_sounds') or
                self.config.getboolean('AUDIO', 'enable_music') or
                self.config.getboolean('AUDIO', 'enable_rain_sounds'))
        
    def log(self, message):
        """Log message if verbose logging is enabled"""
        if self.config.getboolean('DEBUG', 'verbose_logging'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")

    def init_audio(self):
        """Initialize pygame audio system"""
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            self.log("Audio system initialized")
            
            # Load background sounds
            if self.config.getboolean('AUDIO', 'enable_background_sounds'):
                background_files = [
                    os.path.join(self.sound_dir, "rainforest.mp3"),
                    os.path.join(self.sound_dir, "wind.mp3")
                ]
                volume = self.config.getfloat('AUDIO', 'background_volume')
                
                for sound_file in background_files:
                    if os.path.exists(sound_file):
                        try:
                            sound = pygame.mixer.Sound(sound_file)
                            sound.play(-1).set_volume(volume)
                            self.background_sounds.append(sound)
                            self.log(f"Playing background sound: {sound_file}")
                        except pygame.error as e:
                            self.log(f"Error loading background sound {sound_file}: {e}")
            
            # Load rain sound
            if self.config.getboolean('AUDIO', 'enable_rain_sounds'):
                rain_file = os.path.join(self.sound_dir, "rain.wav")
                if os.path.exists(rain_file):
                    try:
                        self.rain_sound = pygame.mixer.Sound(rain_file)
                        self.log("Rain sound loaded")
                    except pygame.error as e:
                        self.log(f"Error loading rain sound: {e}")
            
            # Setup music playlist
            if self.config.getboolean('AUDIO', 'enable_music'):
                music_files = [os.path.join(self.sound_dir, f"track{i}.mp3") for i in range(1, 8)]
                self.music_playlist = [f for f in music_files if os.path.exists(f)]
                random.shuffle(self.music_playlist)
                
                if self.music_playlist:
                    volume = self.config.getfloat('AUDIO', 'music_volume')
                    pygame.mixer.music.set_volume(volume)
                    self.log(f"Music playlist loaded with {len(self.music_playlist)} tracks")
            
        except pygame.error as e:
            self.log(f"Audio initialization failed: {e}")
            self.log("Running without audio...")

    def get_time_window(self):
        """Get current time window based on hour"""
        hour = datetime.now().hour
        morning_start = self.config.getint('TIMING', 'morning_start')
        day_start = self.config.getint('TIMING', 'day_start')
        evening_start = self.config.getint('TIMING', 'evening_start')
        night_start = self.config.getint('TIMING', 'night_start')
        
        if morning_start <= hour < day_start:
            return "morning"
        elif day_start <= hour < evening_start:
            return "day"
        elif evening_start <= hour < night_start:
            return "evening"
        else:
            return "night"

    def set_wallpaper(self, video_name):
        """Set wallpaper using livelycu with proper cleanup"""
        try:
            video_path = os.path.abspath(os.path.join(self.wallpaper_dir, f"{video_name}.mov"))
            if not os.path.exists(video_path):
                self.log(f"Video file not found: {video_path}")
                return False
            
            self.log(f"Setting wallpaper: {video_name}")
            
            # Close all existing wallpapers first
            try:
                subprocess.run([self.livelycu_path, "closewp", "--monitor", "-1"], 
                             capture_output=True, text=True, timeout=10)
                time.sleep(1.0)  # Give time for proper cleanup
            except:
                pass
            
            # Set wallpaper without monitor specification - let Lively handle duplication
            try:
                result = subprocess.run([
                    self.livelycu_path, "setwp", "--file", video_path
                ], capture_output=True, text=True, check=True, timeout=15)
                
                self.log(f"✓ Wallpaper set: {video_name}")
                return True
                
            except subprocess.CalledProcessError as e:
                self.log(f"✗ Failed to set wallpaper: {e}")
                self.log(f"Error output: {e.stderr if e.stderr else 'No error details'}")
                return False
                    
            except subprocess.TimeoutExpired:
                self.log("✗ Timeout setting wallpaper")
                return False
                
        except Exception as e:
            self.log(f"Unexpected error setting wallpaper: {e}")
            return False

    def start_rain_sound(self):
        """Start rain sound with fade in"""
        if not self.config.getboolean('AUDIO', 'enable_rain_sounds') or not self.rain_sound:
            return
            
        if not self.rain_playing:
            try:
                self.rain_sound.set_volume(0)
                self.rain_sound.play(-1)
                
                # Fade in rain sound
                fade_steps = self.config.getint('AUDIO', 'rain_fade_steps')
                fade_delay = self.config.getfloat('AUDIO', 'rain_fade_delay')
                
                for i in range(fade_steps):
                    if not self.run:
                        break
                    self.rain_sound.set_volume(i / (fade_steps * 2))
                    time.sleep(fade_delay)
                
                self.rain_playing = True
                self.log("Rain sound started")
            except Exception as e:
                self.log(f"Error starting rain sound: {e}")

    def stop_rain_sound(self):
        """Stop rain sound with fade out"""
        if not self.config.getboolean('AUDIO', 'enable_rain_sounds') or not self.rain_sound:
            return
            
        if self.rain_playing:
            try:
                # Fade out rain sound
                fade_steps = self.config.getint('AUDIO', 'rain_fade_steps')
                fade_delay = self.config.getfloat('AUDIO', 'rain_fade_delay')
                
                for i in range(fade_steps):
                    if not self.run:
                        break
                    self.rain_sound.set_volume((fade_steps - i) / (fade_steps * 2))
                    time.sleep(fade_delay)
                
                self.rain_sound.stop()
                self.rain_playing = False
                self.log("Rain sound stopped")
            except Exception as e:
                self.log(f"Error stopping rain sound: {e}")

    def music_player(self):
        """Background music player"""
        if not self.config.getboolean('AUDIO', 'enable_music') or not self.music_playlist:
            return
            
        while self.run:
            try:
                current_track = self.music_playlist[self.current_music_index]
                self.log(f"Playing: {os.path.basename(current_track)}")
                
                pygame.mixer.music.load(current_track)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy() and self.run:
                    time.sleep(0.1)
                
                self.current_music_index = (self.current_music_index + 1) % len(self.music_playlist)
                
            except pygame.error as e:
                self.log(f"Music playback error: {e}")
                time.sleep(1)
            except Exception as e:
                self.log(f"Unexpected music error: {e}")
                time.sleep(1)

    def weather_simulation(self):
        """Simulate weather changes with wallpaper transitions"""
        while self.run:
            try:
                # Update time window
                self.time_window = self.get_time_window()
                
                # Transition to rain
                transition_to_rain = f"{self.time_window}_to_rain"
                if self.set_wallpaper(transition_to_rain):
                    self.current_weather = transition_to_rain
                    self.log(f"Weather: Transitioning to rain ({self.time_window})")
                
                # Start rain sound
                self.start_rain_sound()
                
                # Wait for transition
                transition_duration = self.config.getint('TIMING', 'transition_duration')
                time.sleep(transition_duration)
                
                # Full rain
                rain_weather = f"{self.time_window}_rain"
                if self.set_wallpaper(rain_weather):
                    self.current_weather = rain_weather
                    self.log(f"Weather: Raining ({self.time_window})")
                
                # Rain duration
                min_rain = self.config.getint('TIMING', 'min_rain_duration')
                max_rain = self.config.getint('TIMING', 'max_rain_duration')
                rain_duration = random.randint(min_rain, max_rain)
                self.log(f"Rain will last for {rain_duration} seconds")
                time.sleep(rain_duration)
                
                # Transition back to clear
                transition_to_clear = f"rain_to_{self.time_window}"
                if self.set_wallpaper(transition_to_clear):
                    self.current_weather = transition_to_clear
                    self.log(f"Weather: Transitioning to clear ({self.time_window})")
                
                # Stop rain sound
                self.stop_rain_sound()
                
                # Wait for transition
                time.sleep(transition_duration)
                
                # Clear weather
                if self.set_wallpaper(self.time_window):
                    self.current_weather = self.time_window
                    self.log(f"Weather: Clear ({self.time_window})")
                
                # Clear weather duration
                min_clear = self.config.getint('TIMING', 'min_clear_duration')
                max_clear = self.config.getint('TIMING', 'max_clear_duration')
                clear_duration = random.randint(min_clear, max_clear)
                self.log(f"Clear weather will last for {clear_duration} seconds")
                time.sleep(clear_duration)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log(f"Weather simulation error: {e}")
                time.sleep(10)

    def time_window_updater(self):
        """Update time window and wallpaper when time changes"""
        last_time_window = self.get_time_window()
        
        while self.run:
            try:
                current_time_window = self.get_time_window()
                
                # If time window changed and we're not in a weather transition
                if (current_time_window != last_time_window and 
                    not any(transition in self.current_weather for transition in ["_to_", "_rain"])):
                    
                    self.time_window = current_time_window
                    if self.set_wallpaper(self.time_window):
                        self.current_weather = self.time_window
                        self.log(f"Time window changed to: {self.time_window}")
                    last_time_window = current_time_window
                
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log(f"Time updater error: {e}")
                time.sleep(60)

    def close_wallpaper(self):
        """Close current wallpaper properly"""
        try:
            subprocess.run([self.livelycu_path, "closewp", "--monitor", "-1"], 
                         capture_output=True, text=True, check=True, timeout=10)
            time.sleep(0.5)  # Allow cleanup time
            self.log("Closed all wallpapers")
        except subprocess.CalledProcessError as e:
            self.log(f"Error closing wallpaper: {e}")
        except subprocess.TimeoutExpired:
            self.log("Timeout closing wallpaper")

    def run_wallpaper(self):
        """Main function to run the adaptive wallpaper"""
        print("=" * 50)
        print("Adaptive Minecraft Wallpaper with Lively")
        print("=" * 50)
        print("Press Ctrl+C to stop")
        print()
        
        # Check if livelycu exists
        if not os.path.exists(self.livelycu_path):
            print(f"Error: livelycu not found at {self.livelycu_path}")
            print("Please update the path in config.ini")
            return
        
        # Initialize
        self.time_window = self.get_time_window()
        self.current_weather = self.time_window
        
        # Set initial wallpaper
        if self.set_wallpaper(self.time_window):
            self.log(f"Initial wallpaper set: {self.time_window}")
        else:
            print("Failed to set initial wallpaper")
            return
        
        # Start background threads
        threads = []
        
        if self.config.getboolean('AUDIO', 'enable_music') and self.music_playlist:
            music_thread = threading.Thread(target=self.music_player, daemon=True)
            music_thread.start()
            threads.append(music_thread)
        
        weather_thread = threading.Thread(target=self.weather_simulation, daemon=True)
        weather_thread.start()
        threads.append(weather_thread)
        
        time_thread = threading.Thread(target=self.time_window_updater, daemon=True)
        time_thread.start()
        threads.append(time_thread)
        
        try:
            # Keep main thread alive and show status
            if self.config.getboolean('DEBUG', 'show_status_updates'):
                update_interval = self.config.getint('DEBUG', 'status_update_interval')
                while self.run:
                    current_time = datetime.now().strftime("%H:%M:%S")
                    status = f"[{current_time}] {self.current_weather} | Rain: {'Yes' if self.rain_playing else 'No'}"
                    print(f"\r{status:<80}", end="", flush=True)
                    time.sleep(update_interval)
            else:
                while self.run:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.run = False
            
            # Stop audio
            if pygame.mixer.get_init():
                pygame.mixer.stop()
                pygame.mixer.quit()
            
            # Close wallpaper
            self.close_wallpaper()
            print("Goodbye!")

def main():
    wallpaper = AdaptiveWallpaper()
    wallpaper.run_wallpaper()

if __name__ == "__main__":
    main()
