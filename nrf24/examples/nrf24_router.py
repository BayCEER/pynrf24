#!/usr/bin/python -u
# -*- coding: utf-8 -*-
#
#
from nrf24 import NRF24
import time
import re
from time import gmtime, strftime
from bayeosgatewayclient import BayEOSWriter, BayEOSSender, BayEOSFrame
from struct import pack, unpack
import ConfigParser
import RPi.GPIO as GPIO
from thread import start_new_thread


cp = ConfigParser.ConfigParser({'name':'RF24-Router',
                                'ce_pin':'18',
                                'irq_pin':'22',
                                'channel':'0x71',
                                'only_with_valid_checksum':'False',
                                'poll_sleep_time':'0.005',
                                'path':'/tmp/nrf24-router',
                                'max_time':'60',
                                'max_chunk':'2500',
                                'sender_sleep_time':'5',
                                'bayeosgateway_user':'import',
                                'bayeosgateway_pw':'import',
                                'absolute_time':'True',
                                'remove':'True',
                                'backup_path':'none',
                                'rx_led_pins':''})

cp.read("/etc/nrf24-router.conf")

OriginTemplate=cp.get("nrf24","OriginTemplate")
PATH = cp.get("Overall","path")
BACKUPPATH = cp.get('Sender','backup_path')
if(BACKUPPATH=='none'):
    BACKUPPATH=None;
writer = BayEOSWriter(PATH,cp.getint('Writer','max_chunk'),cp.getint('Writer','max_time'))


sender = BayEOSSender(PATH,cp.get('Overall','name'),cp.get('Sender','url'),
                      cp.get('Sender','bayeosgateway_pw'),cp.get('Sender','bayeosgateway_user'),
                      cp.getboolean('Sender','absolute_time'),cp.getboolean('Sender','remove'),
                      BACKUPPATH)
sender.start()

pipes=[]
for p in re.split(' *, *',cp.get('nrf24','pipes')):
    l=[]
    for i in range(1,6):
        l.append(int(p[i*2:(i+1)*2],16))
    pipes.append(l)


# led RX idicator
def blink(pin,times=1):
    while(times>0):
        GPIO.output(pin,1)
        time.sleep(0.2)
        GPIO.output(pin,0)
        times=times-1
        if(times):
            time.sleep(0.3)
    
led_pins=[]

for p in re.split(' *, *',cp.get('nrf24','rx_led_pins')):
    try:
        led_pins.append(int(p))
    except:
        pass

if(len(led_pins)):
    GPIO.setwarnings(False)    
    GPIO.setmode(GPIO.BOARD) #Layout nach PINS

for p in led_pins:
     GPIO.setup(p, GPIO.OUT)
     start_new_thread(blink,(p,2,))  
     time.sleep(0.8)

radio = NRF24()

def initNRF24(sendMessage=True):
    radio.begin(0, 0,cp.getint('nrf24','ce_pin'),cp.getint('nrf24','irq_pin')) #set gpio 25 as CE pin
    radio.setRetries(15,15)
    radio.setPayloadSize(32)
    radio.enableDynamicPayloads()
    radio.setChannel(int(cp.get('nrf24','channel'),16))
    radio.setDataRate(NRF24.BR_250KBPS)
    radio.setPALevel(NRF24.PA_MAX)
    radio.setAutoAck(1)
    radio.openWritingPipe(pipes[0])
    for i in range(0,len(pipes)):
        radio.openReadingPipe(i, pipes[i])
    
    radio.setCRCLength(NRF24.CRC_16 ) 
    radio.startListening()
    radio.stopListening()
    
    radio.printDetails()
    if(sendMessage):
        writer.save_msg(radio.getDetails())
    radio.startListening()

initNRF24()
count=0
bcount=0
last_stat=time.time()

validate_cs=cp.getboolean('nrf24','only_with_valid_checksum')

save = True

while True:
    pipe = [-1]
    recv_buffer = []
    if radio.available(pipe):
       radio.read(recv_buffer) 
    if(pipe[0]>=0):
#        bcount+=recv_buffer.length
        count+=1
        frame= ''.join(chr(i) for i in recv_buffer)
        if(validate_cs):
            res=BayEOSFrame.parse_frame(frame)
            try:
                save=res['validChecksum']
            except:
                save=False
        if(save):
            writer.save_frame(frame,origin=OriginTemplate % pipe[0])
        
        if(len(led_pins)):
            start_new_thread(blink, (led_pins[0] if(pipe[0]>=len(led_pins)) else led_pins[pipe[0]],))
    
    if((time.time()-last_stat)>60):
        writer.save([count,bcount])
        last_stat=time.time()
        if(count==0):
            initNRF24(False) #Restart radio, when there was no frame the last minute!
        count=0
        bcount=0    
    
    time.sleep(cp.getfloat('nrf24', 'poll_sleep_time'))