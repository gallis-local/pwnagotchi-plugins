import logging
import time

import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.hw.base import DisplayImpl

log = logging.getLogger(__name__)

LCD_WIDTH     = 240
LCD_HEIGHT    = 280
CORNER_RADIUS = 30   # physical screen has rounded corners; pixels outside are not visible


class WhisplayHat(DisplayImpl):
    def __init__(self, config):
        super().__init__(config, 'whisplay')
        self._spi = None
        self._gpio = None
        self._mask = None   # rounded-corner compositing mask, built lazily
        self._dc_pin  = int(self.config.get('pin_dc',  27))
        self._rst_pin = int(self.config.get('pin_rst',  4))
        self._led_pin = int(self.config.get('pin_led', 22))

    def layout(self):
        fonts.setup(10, 9, 10, 35, 25, 9)
        self._layout['width']       = LCD_WIDTH
        self._layout['height']      = LCD_HEIGHT
        self._layout['face']        = (0,   50)
        self._layout['name']        = (5,   20)
        # Top-bar elements shifted inward to stay clear of rounded corners
        self._layout['channel']     = (8,    3)
        self._layout['aps']         = (36,   3)
        self._layout['uptime']      = (155,  3)
        self._layout['line1']       = [0, 14, LCD_WIDTH, 14]
        self._layout['line2']       = [0, LCD_HEIGHT - 20, LCD_WIDTH, LCD_HEIGHT - 20]
        self._layout['friend_face'] = (0,  130)
        self._layout['friend_name'] = (40, 132)
        # Bottom-bar elements inset from lower corners
        self._layout['shakes']      = (8,  LCD_HEIGHT - 18)
        self._layout['mode']        = (205, LCD_HEIGHT - 18)
        self._layout['status'] = {
            'pos':  (125, 20),
            'font': fonts.status_font(fonts.Medium),
            'max':  20,
        }
        return self._layout

    def initialize(self):
        log.info("[whisplay] initializing 240x280 ST7789 (direct spidev)")
        import RPi.GPIO as GPIO
        import spidev

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([self._dc_pin, self._rst_pin, self._led_pin], GPIO.OUT)
        GPIO.output(self._led_pin, GPIO.LOW)   # active LOW — backlight on
        self._gpio = GPIO

        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 40_000_000
        spi.mode = 0b00
        self._spi = spi

        self._reset()
        self._init_regs()
        self._fill(0x0000)

    def _out(self, pin, val):
        self._gpio.output(pin, self._gpio.HIGH if val else self._gpio.LOW)

    def _cmd(self, cmd, *args):
        self._out(self._dc_pin, 0)
        self._spi.xfer2([cmd])
        if args:
            self._out(self._dc_pin, 1)
            data = list(args)
            for i in range(0, len(data), 4096):
                self._spi.writebytes2(data[i:i + 4096])

    def _reset(self):
        self._out(self._rst_pin, 1); time.sleep(0.1)
        self._out(self._rst_pin, 0); time.sleep(0.1)
        self._out(self._rst_pin, 1); time.sleep(0.12)

    def _init_regs(self):
        self._cmd(0x11); time.sleep(0.12)
        self._cmd(0x36, 0xC0)
        self._cmd(0x3A, 0x05)
        self._cmd(0xB2, 0x0C, 0x0C, 0x00, 0x33, 0x33)
        self._cmd(0xB7, 0x35)
        self._cmd(0xBB, 0x32)
        self._cmd(0xC2, 0x01)
        self._cmd(0xC3, 0x15)
        self._cmd(0xC4, 0x20)
        self._cmd(0xC6, 0x0F)
        self._cmd(0xD0, 0xA4, 0xA1)
        self._cmd(0xE0, 0xD0,0x08,0x0E,0x09,0x09,0x05,0x31,0x33,0x48,0x17,0x14,0x15,0x31,0x34)
        self._cmd(0xE1, 0xD0,0x08,0x0E,0x09,0x09,0x15,0x31,0x33,0x48,0x17,0x14,0x15,0x31,0x34)
        self._cmd(0x21)
        self._cmd(0x29)

    def _window(self, x0, y0, x1, y1):
        # +20 Y offset for this panel's controller RAM layout
        self._cmd(0x2A, x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF)
        self._cmd(0x2B, (y0+20)>>8,(y0+20)&0xFF,(y1+20)>>8,(y1+20)&0xFF)
        self._cmd(0x2C)

    def _push(self, data):
        self._out(self._dc_pin, 1)
        for i in range(0, len(data), 4096):
            self._spi.writebytes2(data[i:i + 4096])

    def _fill(self, color565):
        hi, lo = (color565 >> 8) & 0xFF, color565 & 0xFF
        self._window(0, 0, LCD_WIDTH - 1, LCD_HEIGHT - 1)
        self._push([hi, lo] * (LCD_WIDTH * LCD_HEIGHT))

    def _get_mask(self):
        """Return a grayscale PIL mask for the rounded-corner screen shape.
        255 = inside visible area, 0 = corner region (out of view).
        Built once and cached.
        """
        if self._mask is None:
            from PIL import Image, ImageDraw
            mask = Image.new("L", (LCD_WIDTH, LCD_HEIGHT), 0)
            d = ImageDraw.Draw(mask)
            r = CORNER_RADIUS
            # Fill the cross-shaped interior
            d.rectangle([r, 0, LCD_WIDTH - r, LCD_HEIGHT], fill=255)
            d.rectangle([0, r, LCD_WIDTH, LCD_HEIGHT - r], fill=255)
            # Fill each rounded corner quarter-circle
            d.ellipse([0,                 0,                 r * 2,     r * 2    ], fill=255)
            d.ellipse([LCD_WIDTH - r * 2, 0,                 LCD_WIDTH, r * 2    ], fill=255)
            d.ellipse([0,                 LCD_HEIGHT - r * 2, r * 2,    LCD_HEIGHT], fill=255)
            d.ellipse([LCD_WIDTH - r * 2, LCD_HEIGHT - r * 2, LCD_WIDTH, LCD_HEIGHT], fill=255)
            self._mask = mask
        return self._mask

    def render(self, canvas):
        img = canvas.convert('RGB')
        # Mask out the rounded corners — those pixels are physically off-screen
        black = Image.new("RGB", img.size, (0, 0, 0))
        black.paste(img, mask=self._get_mask())
        img = black
        bands = img.split()
        raw_r = bands[0].tobytes()
        raw_g = bands[1].tobytes()
        raw_b = bands[2].tobytes()
        n = LCD_WIDTH * LCD_HEIGHT
        buf = bytearray(n * 2)
        for i in range(n):
            c = ((raw_r[i] & 0xF8) << 8) | ((raw_g[i] & 0xFC) << 3) | (raw_b[i] >> 3)
            buf[i * 2]     = c >> 8
            buf[i * 2 + 1] = c & 0xFF
        self._window(0, 0, LCD_WIDTH - 1, LCD_HEIGHT - 1)
        self._push(buf)

    def clear(self):
        self._fill(0x0000)
