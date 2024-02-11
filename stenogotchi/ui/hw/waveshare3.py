import logging
import threading
import _thread
import time

import stenogotchi.ui.fonts as fonts
from stenogotchi.ui.hw.base import DisplayImpl
from stenogotchi import plugins
import stenogotchi


class WaveshareV3(DisplayImpl):
    def __init__(self, config):
        super(WaveshareV3, self).__init__(config, 'waveshare_3')
        self._display = None
        if self.is_touch():
            self._flag_t = 1

    def layout(self):
        if self.config['color'] == 'black':
            fonts.setup(10, 9, 10, 35, 25, 9)
            self._layout['width'] = 250
            self._layout['height'] = 122
            self._layout['face'] = (0, 40)
            self._layout['name'] = (5, 20)
            self._layout['ups'] = (0, 0)
            self._layout['wpm'] = {
                'pos': (50, 0),
                'max': 9
            }
            self._layout['strokes'] = {
                'pos': (128, 0),
                'max': 5
            }
            self._layout['uptime'] = (185, 0)
            self._layout['line1'] = [0, 14, 250, 14]
            self._layout['line2'] = [0, 108, 250, 108]
            self._layout['friend_face'] = (0, 92)
            self._layout['friend_name'] = (40, 94)
            self._layout['bthost'] = {
                'pos': (0, 109),
                'max': 15
            }
            self._layout['wifi'] = {
                'pos': (113, 109),
                'max': 12
            }
            self._layout['mode'] = (210, 109)
            self._layout['status'] = {
                'pos': (125, 20),
                'font': fonts.status_font(fonts.Medium),
                'max': 20
            }
        else:    # these are not correctly configured based on different width and height of color display
            fonts.setup(10, 9, 10, 35, 25, 9)
            self._layout['width'] = 212
            self._layout['height'] = 104
            self._layout['face'] = (0, 26)
            self._layout['name'] = (5, 15)
            self._layout['ups'] = (0, 0)
            self._layout['wpm'] = {
                'pos': (50, 0),
                'max': 9
            }
            self._layout['strokes'] = {
                'pos': (128, 0),
                'max': 5
            }
            self._layout['status'] = (91, 15)
            self._layout['uptime'] = (147, 0)
            self._layout['line1'] = [0, 12, 212, 12]
            self._layout['line2'] = [0, 92, 212, 92]
            self._layout['friend_face'] = (0, 76)
            self._layout['friend_name'] = (40, 78)
            self._layout['bthost'] = {
                'pos': (0, 93),
                'max': 15
            }
            self._layout['wifi'] = {
                'pos': (113, 109),
                'max': 12
            }
            self._layout['mode'] = (187, 93)
            self._layout['status'] = {
                'pos': (125, 20),
                'font': fonts.status_font(fonts.Medium),
                'max': 14
            }
        return self._layout

    def initialize(self, touch = False):
        logging.info("initializing waveshare v3 display")
        from stenogotchi.ui.hw.libs.waveshare.v3.epd2in13_V3 import EPD
        self._display = EPD()
        self._display.init(self._display.FULL_UPDATE)
        self._display.Clear(0xff)
        self._display.init(self._display.PART_UPDATE)

        if self.is_touch():
            logging.info("intializing waveshare v3 touch display")
            from stenogotchi.ui.hw.libs.waveshare.v3.gt1151 import GT_Development, GT1151
            self._gt = GT1151()
            self._GT_Dev = GT_Development()
            self._GT_Old = GT_Development()
            self._gt.GT_Init()

            t = threading.Thread(target = self.pthread_irq)
            t.daemon = True
            t.start()

            t = threading.Thread(target = self.pthread_touch)
            t.daemon = True
            t.start()

    def render(self, canvas):
        buf = self._display.getbuffer(canvas)
        self._display.displayPartial(buf)

    def clear(self):
        self._flag_t = 0
        self._display.Clear(0xff)
    
    def pthread_irq(self) :
        logging.info("touch irq thread running")
        while self._flag_t == 1 :
            if(self._gt.digital_read(self._gt.INT) == 0) :
                self._GT_Dev.Touch = 1
            else :
                self._GT_Dev.Touch = 0
        logging.info("touch irq thread stopping")
    
    def pthread_touch(self):
        logging.info("touch thread running")
        while self._flag_t == 1 :
            # Read the touch input
            self._gt.GT_Scan(self._GT_Dev, self._GT_Old)
            if (self._GT_Old.X[0] == self._GT_Dev.X[0] and self._GT_Old.Y[0] == self._GT_Dev.Y[0] and self._GT_Old.S[0] == self._GT_Dev.S[0]):
                continue
        
            if (self._GT_Dev.TouchpointFlag):
                self._GT_Dev.TouchpointFlag = 0

                #if 3 points, shutdown
                if self._GT_Dev.TouchCount > 2:
                    logging.info(f"[waveshare3 touch] Initiated clean shutdown")
                    _thread.start_new_thread(stenogotchi.shutdown, ())
                    break

                #change to same scale as display
                x = self._layout['width'] - self._GT_Dev.Y[0]
                y = self._GT_Dev.X[0]

                #touch keyboard layout
                if x > 210 and x < 250 and y > 109 and y < 122 :
                    logging.info("touch keyboard layout switch")
                    if 'buttonshim' in plugins.loaded:
                        _thread.start_new_thread(plugins.loaded['buttonshim'].toggle_qwerty_steno, ())
                    else:
                        logging.info("Please enable the buttonshim plugin first.")
                    continue
                
                #touch wifi
                if x > 113 and x < 200 and y > 109 and y < 122 :
                    logging.info("touch wifi switch")
                    # Toggle wifi on/off
                    stenogotchi.set_wifi_onoff()
                    # Check for changes in wifi status over a short while
                    if 'buttonshim' in plugins.loaded:
                        for i in range(10):
                            plugins.loaded['buttonshim']._agent._update_wifi()
                            time.sleep(2)
                    else:
                        logging.info("Please enable the buttonshim plugin for better update display on wifi.")
                    continue
