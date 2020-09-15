import periph
import font
import base

def merge_styles(s1, s2):
    s = s1.copy()
    s.update(s2)
    return s

class DisplayDimmer:

    def __init__(self, child_view, adapt_speed, pwm_pin):
        self.child_view = child_view
        self.current_brightness = 0
        self.target_brightness = 0
        self.adapt_speed = adapt_speed
        self.pwm_pin = pwm_pin
    
    def update(self):
        #self.current_brightness += self.adapt_speed * (self.target_brightness - self.current_brightness)
        if self.current_brightness < self.target_brightness:
            self.current_brightness += self.adapt_speed
        elif self.current_brightness > self.target_brightness:
            self.current_brightness -= self.adapt_speed
        
        self.pwm_pin.duty(int(self.current_brightness * 1023))

        self.child_view.update()

    def displayOn(self):
        self.target_brightness = 1
    
    def displayOff(self):
        self.target_brightness = 0
    
    def isDisplayOn(self):
        return self.current_brightness > 0
    
    def onInput(self, pin, action):
        if self.isDisplayOn():
            self.child_view.onInput(pin)
        
        self.displayOn()


class App:
    
    def __init__(self, style, config):
        self.style = style
        self.config = config
        self.registerAlarm()
        self.child_view = ClockView(self.style) 

    def update(self):
        self.child_view.update()
    
    def onInput(self, pin, action):
        if periph.audio.isPlaying():
            periph.audio.stop()
            return

        if isinstance(self.child_view, ClockView):
            self.child_view = SetAlarmView(self.style, config=self.config['alarm1'], onAlarmConfigured=self.onAlarmConfigured, onAbort=self.onAlarmConfigured)
        elif isinstance(self.child_view, SetAlarmView):
            self.child_view.onInput(pin, action)
    
    def onAlarm(self, alarm_id, alarm_datetime):
        print("Alarm", alarm_id, alarm_datetime)
        periph.audio.play()
        self.child_view = ClockView(self.style)
    
    def onAlarmConfigured(self, set_alarm_view):
        self.config['alarm1'].update(set_alarm_view.config)
        self.registerAlarm()
        self.child_view = ClockView(self.style)
    
    def registerAlarm(self):
        if self.config['alarm1']['alarm-on']:
            periph.alarm_manager.add(base.Alarm('alarm1', (self.config['alarm1']['alarm-hour'], self.config['alarm1']['alarm-minute'], 0), self.onAlarm, repeating=True))
        else:
            periph.alarm_manager.cancel('alarm1')


class ClockView:
    
    def __init__(self, style):
        self.style = style
        self.text_view = TextView(merge_styles(self.style, { 'left': 10, 'top': 50, 'font-size': 4 }))
        self.container = Container(self.style, [self.text_view])

    def update(self):
        (_, _, _, hours, mins, _, _, _) = periph.ic_time.localtime()
        self.text_view.setText("%02d:%02d" % (hours, mins))
        self.container.update()


class SetAlarmView:
    
    def __init__(self, style, config, onAlarmConfigured=None, onAbort=None):
        self.style = style
        self.config = config

        self.onAlarmConfigured = onAlarmConfigured
        self.onAbort = onAbort

        self.title = TextView(merge_styles(self.style, { 'left': 10, 'top': 10, 'font-size': 1 }), text='Set Alarm 1')
        #self.alarm_time = TextView(merge_styles(self.style, { 'left': 10, 'top': 50, 'font-size': 4 }), text='08:40')

        self.alarm_hour_spinner = Spinner(
            merge_styles(self.style, { 'left': 10, 'top': 50, 'font-size': 4 }),
            [("%02d" % v, v) for v in range(0, 24)],
            initial_value=self.config['alarm-hour'],
            onChange=lambda e: self.config.update({ 'alarm-hour': e.selectedValue() })
        )
        self.alarm_hour_underline = Underline(self.style, self.alarm_hour_spinner, underline=False)

        self.alarm_colon = TextView(merge_styles(self.style, { 'left': 10 + self.alarm_hour_spinner.width(), 'top': 50, 'font-size': 4 }), text=':')

        self.alarm_minute_spinner = Spinner(
            merge_styles(self.style, { 'left': 10 + self.alarm_hour_spinner.width() + self.alarm_colon.width(), 'top': 50, 'font-size': 4 }),
            [("%02d" % v, v) for v in range(0, 60, 10)],
            initial_value=self.config['alarm-minute'],
            onChange=lambda e: self.config.update({ 'alarm-minute': e.selectedValue() })
        )
        self.alarm_minute_underline = Underline(self.style, self.alarm_minute_spinner, underline=False)

        self.on_off_switch = Spinner(
            merge_styles(self.style, { 'left': 10, 'top': 100, 'font-size': 1 }),
            [("On ", True), ("Off", False)],
            initial_value=self.config['alarm-on'],
            onChange=lambda e: self.config.update({ 'alarm-on': e.selectedValue() })
        )
        self.on_off_underline = Underline(self.style, self.on_off_switch, underline=False)

        self.container = Container(self.style, [self.title, self.alarm_hour_underline, self.alarm_colon, self.alarm_minute_underline, self.on_off_underline])

    def onInput(self, pin, action):
        if action == 'longpress':
            if self.alarm_hour_underline.is_underlined:
                self.alarm_hour_underline.setUnderline(False)
                self.alarm_minute_underline.setUnderline(True)
            elif self.alarm_minute_underline.is_underlined:
                self.alarm_minute_underline.setUnderline(False)
                self.on_off_underline.setUnderline(True)
            elif self.on_off_underline.is_underlined:
                self.on_off_underline.setUnderline(False)
                if self.onAlarmConfigured is not None:
                    self.onAlarmConfigured(self)
            else:
                self.alarm_hour_underline.setUnderline(True)
        elif action == 'click':
            if self.alarm_hour_underline.is_underlined:
                self.alarm_hour_spinner.onInput(pin, action)
            elif self.alarm_minute_underline.is_underlined:
                self.alarm_minute_spinner.onInput(pin, action)
            elif self.on_off_underline.is_underlined:
                self.on_off_switch.onInput(pin, action)
            else:
                if self.onAbort is not None:
                    self.onAbort(self)

    def update(self):
        self.container.update()


class Underline:

    def __init__(self, style, child, underline=True):
        self.style = style
        self.child = child
        self.is_underlined = False
        self.underline = underline
    
    def setUnderline(self, underline):
        self.underline = underline

    def onInput(self, pin, action):
        self.child.onInput(pin, action)

    def update(self):
        self.child.update()

        if self.is_underlined == self.underline:
            return
        
        line_color = periph.TFT.rgbcolor(*self.style['color']) if self.underline else periph.TFT.rgbcolor(*self.style['background-color'])
        periph.TFT.hline(self.child.left(), self.child.top() + self.child.height(), self.child.width(), line_color)
        self.is_underlined = self.underline
        

class Spinner:

    def __init__(self, style, key_value_pairs, initial_value=None, onChange=None):
        self.style = style
        self.text = TextView(self.style)
        self.key_value_pairs = key_value_pairs
        self.setSelectedIndex(next(i for i, (key, value) in enumerate(self.key_value_pairs) if value == initial_value) if initial_value is not None else 0)
        self.onChange = onChange
    
    def spin(self):
        self.setSelectedIndex((self.selected_index + 1) % len(self.key_value_pairs))
    
    def setSelectedIndex(self, index):
        self.selected_index = index
        self.text.setText(self.key_value_pairs[self.selected_index][0])

    def onInput(self, pin, action):
        self.spin()
        if self.onChange is not None:
            self.onChange(self)
    
    def update(self):
        self.text.update()
    
    def selectedValue(self):
        return self.key_value_pairs[self.selected_index][1]
    
    def left(self):
        return self.text.left()
    
    def top(self):
        return self.text.top()
    
    def width(self):
        return self.text.width()
    
    def height(self):
        return self.text.height()


# class NumericSpinner:

#     def __init__(self, style, minv, maxv, step, startv=None, onChange=None):
#         self.style = style
#         self.text = TextView(self.style)
#         self.min_value = minv
#         self.max_value = maxv
#         self.step = step
#         self.setValue(startv)
#         self.onChange = onChange
    
#     def setValue(self, val):
#         self.value = val
#         if self.value is not None:
#             self.text.setText("%02d" % self.value)
#         else:
#             self.text.setText("")
    
#     def onInput(self, pin, action):
#         if self.value is not None:
#             self.setValue(NumericSpinner.wrap(self.value + self.step, self.min_value, self.max_value))
#         else:
#             self.setValue(self.min_value)
        
#         if self.onChange is not None:
#             self.onChange(self)
    
#     def update(self):
#         self.text.update()
    
#     def left(self):
#         return self.text.left()
    
#     def top(self):
#         return self.text.top()
    
#     def width(self):
#         return self.text.width()
    
#     def height(self):
#         return self.text.height()

#     def wrap(val, minv, maxv):
#         return minv + val % (maxv - minv + 1)
    
#     def clamp(val, minv, maxv):
#         return max(minv, min(maxv, val))


class Container:

    def __init__(self, style, children):
        self.style = style
        self.should_update = True
        self.children = children
    
    def onInput(self, pin, action):
        for child in self.children:
            child.onInput(pin, action)
    
    def update(self):
        if self.should_update:
            periph.TFT.clear(periph.TFT.rgbcolor(*self.style['background-color']))
            self.should_update = False
        
        for child in self.children:
            child.update()


class TextView:

    def __init__(self, style, text=''):
        self.style = style
        self.current_text = ''
        self.text = text
    
    def setText(self, text):
        self.text = text
    
    def update(self):
        if self.current_text == self.text:
            return
        
        periph.TFT.text(self.style['left'], self.style['top'], self.current_text, font.terminalfont, periph.TFT.rgbcolor(*self.style['background-color']), self.style['font-size'])
        periph.TFT.text(self.style['left'], self.style['top'], self.text, font.terminalfont, periph.TFT.rgbcolor(*self.style['color']), self.style['font-size'])

        self.current_text = self.text
    
    def left(self):
        return self.style['left']
    
    def top(self):
        return self.style['top']

    def width(self):
        return font.terminalfont['width'] * self.style['font-size'] * len(self.text) # TODO: add font to style, get dimensions dynamically
    
    def height(self):
        return font.terminalfont['height'] * self.style['font-size'] # TODO: add font to style, get dimensions dynamically
