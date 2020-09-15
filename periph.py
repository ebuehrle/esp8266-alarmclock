from machine import Pin, SPI, PWM
from tft import TFT_GREEN

_dc = Pin(4, Pin.OUT)
_cs = Pin(15, Pin.OUT)
_rst = Pin(2, Pin.OUT)
_spi = SPI(1, baudrate=16000000, polarity=0, phase=0)
TFT = TFT_GREEN(128, 160, _spi, _dc, _cs, _rst, rotate=90)

display_led_pwm = PWM(Pin(5), freq=1000)


from base import Buttons

primary_button = Pin(16, Pin.IN | Pin.PULL_UP)
buttons_watcher = Buttons([primary_button])


from base import ICTime

ic_time = ICTime()


from base import AlarmManager

alarm_manager = AlarmManager()


from base import Audio

_audio_pin = Pin(12, Pin.OUT)
_audio_pin.value(0)
audio = Audio(_audio_pin)
