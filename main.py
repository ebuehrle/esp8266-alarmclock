from views import DisplayDimmer, App
import machine
import network
import periph

app_config = {
    'alarm1': {
        'alarm-hour': 7,
        'alarm-minute': 30,
        'alarm-on': False,
    }
}

style = {
    'background-color': (81, 45, 168),
    'color': (255, 64, 129),
}

def get_connection():
    import wifimgr
    import sys
    import gc

    wlan = None
    while not wlan:
        wlan = wifimgr.get_connection()
    
    del wifimgr
    del sys.modules['wifimgr']
    gc.collect()
    
    return wlan

def main():

    wlan = get_connection()

    periph.TFT.init()

    app = App(style, app_config)
    dimmer = DisplayDimmer(app, 0.005, periph.display_led_pwm)
    dimmer.displayOn()

    periph.buttons_watcher.subscribeHandler(lambda pin, action: app.onInput(pin, action))

    while True:
        periph.buttons_watcher.update()
        periph.alarm_manager.update()
        dimmer.update()
