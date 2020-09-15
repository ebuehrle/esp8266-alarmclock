import network
import time
import ntptime

class Buttons:
    """Polls buttons and triggers handlers"""

    DEBOUNCE_INTERVAL_MS = 10
    LONG_PRESS_THRESH_MS = 1000

    BS_UP = 0
    BS_DOWN = 1
    BS_LONG_DOWN = 2

    def __init__(self, pins):
        self.handlers = []
        self.state = [(pin, Buttons.BS_UP, 0) for pin in pins] # pin, last state, timestamp

    def update(self):
        for i in range(len(self.state)):
            (pin, last_state, last_timestamp) = self.state[i]
            self.state[i] = self.updatePin(pin, last_state, last_timestamp)
    
    def updatePin(self, pin, last_state, last_timestamp):
        current_value = pin.value()
        current_timestamp = time.ticks_ms()
        timestamps_diff = time.ticks_diff(current_timestamp, last_timestamp)

        if timestamps_diff < Buttons.DEBOUNCE_INTERVAL_MS: # bounce
            return (pin, last_state, last_timestamp)
        
        if last_state == Buttons.BS_DOWN and not current_value: # keep down
            if timestamps_diff >= Buttons.LONG_PRESS_THRESH_MS:
                self.onButtonAction(pin, 'longpress')
                return (pin, Buttons.BS_LONG_DOWN, last_timestamp)
            return (pin, Buttons.BS_DOWN, last_timestamp)
        
        if last_state == Buttons.BS_LONG_DOWN and not current_value: # long down
            return (pin, Buttons.BS_LONG_DOWN, last_timestamp)
        
        if last_state in [Buttons.BS_DOWN, Buttons.BS_LONG_DOWN] and current_value: # release
            if last_state == Buttons.BS_DOWN:
                self.onButtonAction(pin, 'click')
            return (pin, Buttons.BS_UP, current_timestamp)

        if last_state == Buttons.BS_UP and not current_value: # push
            return (pin, Buttons.BS_DOWN, current_timestamp)

        if last_state == Buttons.BS_UP and current_value: # keep up
            return (pin, Buttons.BS_UP, last_timestamp)
    
    # def subscribeHandler(self, pin, action_id, handler_func):
    #     handler = lambda btnid, actid : handler_func() if (btnid == button_id and actid == action_id) else None
    #     self.handlers.add(handler)
    #     return handler

    def subscribeHandler(self, handler):
        self.handlers.append(handler)
    
    def removeHandler(self, handler):
        if handler in self.handlers:
            self.handlers.remove(handler)
    
    def onButtonAction(self, pin, action_id):
        for handler in self.handlers:
            handler(pin, action_id)


class ICTime:
    """Internet controlled time"""

    last_update_time = -999999

    def __init__(self, update_interval_s=60, retry_interval_s=5):
        self.update_interval_s = update_interval_s
        self.retry_interval_s = retry_interval_s
    
    def localtime(self):
        # TODO: auto timezone, daylight savings -> use datetime.py from micropython-lib
        if network.WLAN().isconnected() and (time.time() - ICTime.last_update_time) >= self.update_interval_s:
            try:
                ntptime.settime()
            except OSError as e:
                print('Error synchronizing NTP:', e, 'Retry in %d s' % self.retry_interval_s)
                ICTime.last_update_time += self.retry_interval_s
            else:
                ICTime.last_update_time = time.time()
        
        utc_datetime = time.localtime()
        local_datetime = time.localtime(time.mktime(utc_datetime) + 2*60*60)

        return local_datetime


class Alarm:

    def __init__(self, ident, datetime, handler, repeating=False):
        self.ident = ident
        self.datetime = Alarm.convertDatetime(datetime)
        self.updateDatetime()
        self.handler = handler
        self.repeating = repeating
    
    def convertDatetime(datetime):
        if len(datetime) == 8:
            return datetime
        elif len(datetime) == 3:
            return Alarm.time2Datetime(datetime)
        else:
            raise ValueError("'alarm_datetime' must be datetime 8-tuple or 3-tuple (hr, min, sec)")
    
    def time2Datetime(alarm_time):
        local_datetime = ICTime().localtime()
        alarm_datetime = (
            local_datetime[0], # year
            local_datetime[1], # month
            local_datetime[2], # month day
            alarm_time[0],     # hour
            alarm_time[1],     # minute
            alarm_time[2],     # second
            local_datetime[6], # weekday
            local_datetime[7], # yearday
        )
        return alarm_datetime

    def updateDatetime(self):
        while self.shouldRing():
            self.datetime = time.localtime(time.mktime(self.datetime) + 24*60*60)
    
    def shouldRing(self):
        # TODO: use datetime.py
        local_datetime = ICTime().localtime()
        return time.mktime(local_datetime) >= time.mktime(self.datetime)
    
    def ring(self):
        self.handler(self.ident, self.datetime)
    
    def __repr__(self):
        return "Alarm({}, {}, repeat={})".format(self.ident, self.datetime, self.repeating)


class AlarmManager:

    def __init__(self):
        self.alarms = []
    
    def add(self, alarm):
        self.cancel(alarm.ident)
        self.alarms.append(alarm)
        print(self.alarms)
    
    def cancel(self, ident):
        self.alarms = list(filter(lambda a: a.ident != ident, self.alarms))
        print("Alarm", ident, "cancelled")

    def update(self):
        updated_alarms = []

        while self.alarms:
            alarm = self.alarms.pop()
            
            if not alarm.shouldRing():
                updated_alarms.append(alarm)
                continue
            
            alarm.ring()

            if alarm.repeating:
                alarm.updateDatetime()
                updated_alarms.append(alarm)
            
        self.alarms = updated_alarms


class Audio:

    DURATION_MS = 30000

    def __init__(self, pin):
        self.pulse_pin = pin
        self.started = -999999
        self.stopped = True
        self.went_out = False

    def play(self):
        self.stop()
        self._pulse()
        self.started = time.ticks_ms()
        self.stopped = False
        self.went_out = False
    
    def stop(self):
        if self.isPlaying():
            self._pulse()
        self.stopped = True

    def wentOut(self):
        # ticks_diff wraps around, so cache
        self.went_out = self.went_out or time.ticks_diff(time.ticks_ms(), self.started) >= Audio.DURATION_MS
        return self.went_out

    def isPlaying(self):
        return not (self.wentOut() or self.stopped)
    
    def _pulse(self):
        self.pulse_pin.value(0)
        time.sleep_ms(50)
        self.pulse_pin.value(1)
        time.sleep_ms(50)
        self.pulse_pin.value(0)
