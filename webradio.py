#!/usr/bin/python2
#-------------------------------------------------------------------------------
# FileName:     radio.py
# Purpose:      This program controls a vintage radio based on RaspberryPi,
#               MPD, a Nokia 5110 LCD  display, two rotary encoders and a
#               DIY amp based on the IC TDA2002A.
#
#
#
# Note:         All dates are in European format DD-MM-YY[YY]
#               The rotary encoder code is based on Rotary_Encoder-1a.py,
#               by Paul Versteeg.
#
# Author:       Gean Marcos Geronymo
#
# Created:      17-Jun-2016
# Last modification: 06-Nov-2016
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#-------------------------------------------------------------------------------

import RPi.GPIO as GPIO
import subprocess
import datetime
import time
import Adafruit_Nokia_LCD as LCD
import Adafruit_GPIO.SPI as SPI

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from time import sleep

# Global constants & variables
Enc1_A = 14  # Encoder 1 input A: BCM 14 (physical pin 8)
Enc1_B = 15  # Encoder 1 input B: BCM 15 (physical pin 10)

Enc2_A = 21  # Encoder 1 input A: BCM 21 (physical pin 13 - rev. 1)
Enc2_B = 22  # Encoder 1 input B: BCM 22 (physical pin 15)

sw_pin = 17      # On/Off switch: BCM 17 (physical pin 11)
LCD_gnd = 18 # LCD GND Pin: BCM 18 (physical pin 12)

def LCD_init():
        '''
        Inializes the LCD display
        '''
        global disp
        global image
        global draw
        global font
        # Raspberry Pi hardware SPI config:
        DC = 23
        RST = 24
        SPI_PORT = 0
        SPI_DEVICE = 0

        # Hardware SPI usage:
        disp = LCD.PCD8544(DC, RST, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=4000000))

        # Initialize library.
        disp.begin(contrast=60)

        # Clear display.
        disp.clear()
        disp.display()

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        image = Image.new('1', (LCD.LCDWIDTH, LCD.LCDHEIGHT))
        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)
        # Draw a white filled box to clear the image.
        draw.rectangle((0,0,LCD.LCDWIDTH,LCD.LCDHEIGHT), outline=255, fill=255)

        # configuracao da fonte
        font = ImageFont.load_default()

        return
        
def gpio_init():
        '''
        Initializes the GPIO interface used to control
        the on/off switch and the rotary encoders
        '''
        GPIO.setmode(GPIO.BCM)  # use BCM pin numbering
        GPIO.setup(LCD_gnd, GPIO.OUT) # configure the lcd gnd pin as output
        GPIO.setup(sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # input on/off switch
        GPIO.output(18,1)  # starts with LCD off (high)
        GPIO.setup(Enc1_A, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
        GPIO.setup(Enc1_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(Enc2_A, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
        GPIO.setup(Enc2_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # setup an event detection thread for the A encoder1 switch
        GPIO.add_event_detect(Enc1_A, GPIO.FALLING, callback=rotation_decode, bouncetime=500) # bouncetime in mSec
        # setup an event detection thread for the A encoder2 switch
        GPIO.add_event_detect(Enc2_A, GPIO.FALLING, callback=rotation_decode, bouncetime=500) # bouncetime in mSec
        # setup an event detection thread for the on/off switch
        GPIO.add_event_detect(sw_pin, GPIO.BOTH, callback=on_off, bouncetime=200)
        return

def rotation_decode(encoder):
        '''
        Handler for the rotary encoders
        Simplified version
        Center encoder just skip to next radio
        Right encoder just skip to previous radio
        '''
        Switch1_A = GPIO.input(Enc1_A)
        Switch1_B = GPIO.input(Enc1_B)
        
        if GPIO.input(sw_pin) == 1: # if the radio is off, ignore the rotary encoder
                return
        else:
	        if encoder == Enc1_A: # center rotary encoder: station tuner
		        if subprocess.check_output(["mpc","current"]).rstrip() == "Nights with Alice Cooper":
			        return
		        else:
                                if(Switch1_A == 1) and (Switch1_B == 0): # ->
                	                station_LCD('>')
                	                subprocess.call(["mpc", "next"])
                	                station_LCD(subprocess.check_output(["mpc", "current"]).rstrip())
                                        while Switch1_B == 0:
                                                Switch1_B = GPIO.input(Enc1_B)
                                        while Switch1_B == 1:
                                                Switch1_B = GPIO.input(Enc1_B)
                                        return,
                                elif(Switch1_A == 1) and (Switch1_B == 1): # <-
                                        station_LCD('<')
                	                subprocess.call(["mpc", "prev"])
                	                station_LCD(subprocess.check_output(["mpc", "current"]).rstrip())
                                        while Switch1_A == 1:
                                                Switch1_A = GPIO.input(Enc1_A)
                                        return
                elif encoder == Enc2_A: # left rotary encoder: playlist selector
		        if subprocess.check_output(["mpc","current"]).rstrip() == "Band News FM (RJ)":
			        return
		        else:
                	        station_LCD('<')
                	        subprocess.call(["mpc", "prev"])
               	 	        station_LCD(subprocess.check_output(["mpc", "current"]).rstrip())
                	        return
                else:
                        return

def on_off(pin):
        '''
        Handler for the on-off switch
        '''
        sleep(0.1) # extra 100 ms delay
        if GPIO.input(sw_pin) == 0:
                print "[%s] The radio is on." %datetime.datetime.now()
                subprocess.call(["mpc", "load", "radios"])
                subprocess.call(["mpc", "single", "on"])
                subprocess.call(["mpc", "repeat", "on"])
 	        subprocess.call(["mpc", "play"])
 	        GPIO.output(LCD_gnd,0)  # turn on the LCD
                station_LCD(subprocess.check_output(["mpc", "current"]).rstrip())
        elif GPIO.input(sw_pin) == 1:
           	print "[%s] The radio is off." %datetime.datetime.now()
 	        subprocess.call(["mpc", "stop"])
 	        subprocess.call(["mpc", "clear"])
                draw.rectangle((0,0,LCD.LCDWIDTH,LCD.LCDHEIGHT), outline=255, fill=255)
                disp.image(image.rotate(180)) # clear the LCD display
                disp.display()
                
 	        GPIO.output(LCD_gnd,1)  # turn off the LCD
        return

def station_LCD(station):
        '''
        Write the current station's name to the LCD
        '''
        draw.rectangle((0,0,LCD.LCDWIDTH,LCD.LCDHEIGHT), outline=255, fill=255)
        if station == ">":
                draw.text((30,20), '>>>', font=font)
        elif station == "<":
                draw.text((30,20), '<<<', font=font)
        elif station == "Band News FM (RJ)":
                draw.text((30,10), 'BAND', font=font)
                draw.text((30,20), 'NEWS', font=font)
                draw.text((38,35), 'RJ', font=font)
        elif station == "Band News FM (SP)":
                draw.text((30,10), 'BAND', font=font)
                draw.text((30,20), 'NEWS', font=font)
                draw.text((38,35), 'SP', font=font)
        elif station == "Bradesco Esportes FM (SP)":
                draw.text((22,10), 'BRADESCO', font=font)
                draw.text((22,20), 'ESPORTES', font=font)
                draw.text((38,35), 'SP', font=font)
        elif station == "Bradesco Esportes FM (RJ)":
                draw.text((22,10), 'BRADESCO', font=font)
                draw.text((22,20), 'ESPORTES', font=font)
                draw.text((38,35), 'RJ', font=font)
        elif station == "1.FM - Classic Rock":
                draw.text((30,10), '1. FM', font=font)
                draw.text((25,20), 'Classic', font=font)
                draw.text((30,35), 'Rock', font=font)
        elif station == "The Drive 97.1 (Chicago)":
                draw.text((30,10), '97.1', font=font)
                draw.text((30,20), 'Drive', font=font)
                draw.text((25,35), 'Chicago', font=font)
        elif station == "Tribuna FM Soft (Londrina)":
                draw.text((22,10), 'Tribuna', font=font)
                draw.text((30,20), 'Soft', font=font)
                draw.text((25,35), 'Ldna', font=font)
        elif station == "Radio Cidade (RJ)":
                draw.text((30,10), 'Radio', font=font)
                draw.text((28,20), 'Cidade', font=font)
                draw.text((38,35), 'RJ', font=font)
        elif station == "Tribuna FM (Petropolis)":
                draw.text((22,10), 'Tribuna', font=font)
                draw.text((38,20), 'FM', font=font)
                draw.text((25,35), 'Petro', font=font)
        elif station == "Radio UEL (Londrina)":
                draw.text((30,10), 'Radio', font=font)
                draw.text((35,20), 'UEL', font=font)
                draw.text((25,35), 'Ldna', font=font)
	elif station == "Nights with Alice Cooper":
		draw.text((25,10), 'Nights', font=font)
		draw.text((18,20), 'w/ Alice', font=font)
		draw.text((25,30), 'Cooper', font=font)
        else:
                draw.text((30,10), 'Error!', font=font)
                # Display image.
        disp.image(image.rotate(180))
        disp.display()
        return

def main():
        try:
                LCD_init()      # call the LCD init function
                gpio_init()     # call the GPIO init function
                on_off(sw_pin)  # check the on_off switch position
                while True :
                        # wait for an encoder click
                        sleep(1)

        except KeyboardInterrupt: # Ctrl-C to terminate the program
                GPIO.cleanup()


if __name__ == '__main__':
    main()
