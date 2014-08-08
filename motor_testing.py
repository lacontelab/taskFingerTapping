#!/usr/bin/env python

#############################
# Flags and defines         #
#############################

DBG           = 1    # Set 1 to print info/debugging statements
TRN           = 0    # Set 1 for training and 0 for testing
WINDOWS       = 0    # Set 1 on Windows and 0 on Linux/Mac

TCPIP         = 1    # Set 1 to receive data over TCP/IP
TCPIP_PORT    = 8000 # Port receiving TCP/IP data
TCPIP_GUI     = 1   # Open GUI to initialize TCP/IP 

AFNI_PLUGOUT  = 0   #Set 1 to enable afni plugout plots
AFNI_HOST_IP  = 'localhost' # host running AFNI receiving plugout_drive commands

SERIAL        = 0   #Set 1 to receive data over serial port
BOUT_RATE     = 300 #Set bout rate for serial communication 

TR_DUR        = 2 # TR duration in seconds, number of TRs read from first line in LABEL_FILE
LABEL_FILE    = 'lbls_vegg_motor_tst_afniDemo.dat' # label file controlling presentation
IMAGE_DIR     = 'images'   # name of directory in ../. containing images for presentation 
IMAGE_SIZE    = (800,600)  # resolution of images in IMAGE_DIR
SCREEN_SIZE   = (1024,768) # screen size 
LOG_PREFIX    = 'log_motor_tst_afniDemo_' # prefix for log file


############################
#  Import various modules  #
############################

import  VisionEgg
from    VisionEgg.Core import *
from    VisionEgg.FlowControl import Presentation, Controller, FunctionController
from    VisionEgg.MoreStimuli import *
from    VisionEgg.Textures import *
from    VisionEgg.DaqKeyboard import *
from    VisionEgg.Text import *
from    VisionEgg.Textures import *
from    VisionEgg.ResponseControl import *
from    math import *
from    scipy import polyfit
import  pygame
import  OpenGL.GL as gl
from    string import *
import  Image, ImageDraw # Python Imaging Library (PIL)
import  os, sys

if SERIAL:
  import serial

if TCPIP:
  from VisionEgg.TCPController import *
  tcp_server = TCPServer(hostname='', 
               port=TCPIP_PORT, 
               single_socket_but_reconnect_ok=1, 
               confirm_address_with_gui=TCPIP_GUI) 
  
  if tcp_server.server_socket is None: # User wants to quit 
    sys.exit() 

  tcp_listener = tcp_server.create_listener_once_connected()

  
############################
# Initialization           #
############################

# start logging 
VisionEgg.start_default_logging(); 
VisionEgg.watch_exceptions();

### read files, directories, etc. 
base_dir = os.getcwd()
log_file_name = time.strftime ('%m-%d-%Y_%Hh-%Mm.txt');
prog_name = split (os.path.basename (sys.argv[0]), '.')
log_file_name = str (LOG_PREFIX) + log_file_name

if WINDOWS:
  tmp_dir = base_dir + str ('\..')
  img_dir = '\\'.join([tmp_dir, IMAGE_DIR,'']);
else: 
  tmp_dir = base_dir + str ('/..')
  img_dir ='/'.join([tmp_dir, IMAGE_DIR, ''])

if DBG:
  print '\n============================ Initialization ==========================' 
  print ' Label file:            %s' % (LABEL_FILE)
  print ' Log file:              %s' % (log_file_name)
  print ' Current directory :    %s' % (base_dir)
  print ' Directory with images: %s' % (IMAGE_DIR )
  print '========================================================================\n'

# open label and log file
if DBG: print 'Opening files  ',
label_file=open(LABEL_FILE, 'r')
log_file=open(log_file_name,'w')
if DBG: print '...done.'

# initialize log file
if TRN:
  log_file.write("# LOGFILE: %s, %s (TRAINING)\n" %(prog_name[0], time.strftime ('%m-%d-%Y %H:%M')))
else:
  log_file.write("# LOGFILE: %s, %s (TESTING)\n" %(prog_name[0], time.strftime ('%m-%d-%Y %H:%M')))

log_file.write("# time;currBlock;currShow;dist;dist_detrend;fbScore;fbScale;l_count;r_count\n")

# some variable definitions     
TR_n = int(label_file.readline())
sec_n = TR_n*TR_DUR
current_block = 0

# define arrays read from label file
block_array     = []
show_array      = []
block_lengths   = []
block_len_array = []
stimImg_names   = []
fb_array        = []

# read label file
if DBG: print 'Reading label file ',

for line in label_file:
    b, s, i, fb, xxx = line.split(";", 4)
    block_array = block_array + [b]
    show_array = show_array + [s]
    stimImg_names = stimImg_names + [i]
    fb_array = fb_array + [fb]

label_file.close
if DBG: print '...done.'

#print '\nblock: %s' % (block_array)
#print 'show: %s' % (show_array)
#print 'img names: %s' % (stimImg_names),

if DBG: print 'Loading images ',
img_name='%sright.png' %(img_dir)
txtr_posFb = Texture(img_name)
img_name='%sleft.png' %(img_dir)
txtr_negFb = Texture(img_name)
img_name='%sframe2.png' %(img_dir)
txtr_frame = Texture(img_name)
if DBG: print '...done.\n'

# Determine block lengths 
nbl=0
current_block = block_array[0]
for ntr in range(TR_n-1):
  #print '%d %s' %(ntr+1, block_array[ntr])

  if block_array[ntr] == current_block:
    if (show_array[ntr] == "1") or (show_array[ntr] == "1111"):
      nbl = nbl + 1
  else:
    current_block = block_array[ntr]
    block_lengths.append(nbl)
    nbl = 0  
block_lengths.append(nbl)

nbl=0
current_block = block_array[0]

for ntr in range(TR_n):
  if block_array[ntr] == current_block:
    b = block_lengths[nbl]
    block_len_array.append(b)
  else:
    current_block = block_array[ntr]
    nbl = nbl + 1
    b = block_lengths[nbl]
    block_len_array.append(b)

if SERIAL:
  try:
    ser = serial.Serial(0,BOUT_RATE,timeout=0,parity=serial.PARITY_NONE,rtscts=1)
    #ser = serial.Serial(0,9600,timeout=0,parity=serial.PARITY_EVEN,rtscts=1)
  except:
    sys.stderr.write("ERROR: Could not open serial port\n\n")
    sys.exit()

# Initialize plots of button presses using AFNIs plugout_drive
if AFNI_PLUGOUT:
  # AFNI plugout functions
  def updatePlugPlot (name, x_pos, n_left, n_right): 
    global ff
    print >> ff, "ADDTO_GRAPH_XY %s %5.2f %d %d" % (name, float(x_pos), int(n_left), int(n_right))

  def closePlugPlot(name):
    print >> ff, "CLOSE_GRAPH_XY %s" %name

  def openPlugPlot(name, title, x_max, y_max):
    global ff

    print >>ff, "OPEN_GRAPH_XY %s '%s' 0 %d 'measurements (TRs)' 2 0 %d presses left right " %(name, title, x_max, y_max) 
    print >>ff, "SET_GRAPH_GEOM %s geom=1000x400+920+775" %name


  plugout_command ='plugout_drive -port 8100 -host %s' % AFNI_HOST_IP
  ff=os.popen(plugout_command, 'w')
  # close if already open 
  closePlugPlot('buttons')
  openPlugPlot('buttons', 'button presses', TR_n, 20)

#################################
#  Initialize the various bits  #
#################################

# Initialize OpenGL graphics screen.
screen = VisionEgg.Core.Screen(size=SCREEN_SIZE)
#screen = get_default_screen()

# Set the background color to white (RGBA).
screen.parameters.bgcolor = (0.0,0.0,0.0,0.0)

screen_half_x = screen.size[0]/2
screen_half_y = screen.size[1]/2

text_instruct_1 = Text(text='',
            color=(1.0,1.0,1.0),
            position=(screen_half_x,screen_half_y+120),
	        font_size=40,
	        anchor='center')

text_instruct_2 = Text(text='FEEDBACK',
            color=(1.0,1.0,1.0),
            position=(screen_half_x,screen_half_y+120),
	        font_size=80,
	        anchor='center')

text_instruct_3 = Text(text='FINGER TAPPING',
            color=(1.0,1.0,1.0),
            position=(screen_half_x,screen_half_y+30),
	        font_size=80,
	        anchor='center')

bar_length = 20; bar_width = 40
bar = Target2D(
    on 		= 0,
    anchor      = 'center',
    position    = (screen_half_x, screen_half_y),
    size        = (bar_length, bar_width),
    color       = (1.0, 1.0, 1.0, 0.8), # Draw it in white (RGBA)
    orientation = 0)

barFrame = TextureStimulus(texture=txtr_frame,  
            internal_format = gl.GL_RGBA,
            max_alpha = 0.5,
            size = (800,60),
            position = (screen_half_x,screen_half_y),
            anchor='center')

taskStimulusImage = TextureStimulus(texture=txtr_posFb,
            size = IMAGE_SIZE,
            internal_format = gl.GL_RGBA,
            max_alpha = 1.0,
            position = (screen_half_x,screen_half_y+76),
            anchor='center')

posFbStimulusImage = TextureStimulus(texture=txtr_posFb,  
            internal_format = gl.GL_RGBA,
            max_alpha = 1.0,
            size = (100,60),
            position = (screen_half_x+353,screen_half_y),
            anchor='center')

negFbStimulusImage = TextureStimulus(texture=txtr_negFb,  
            internal_format = gl.GL_RGBA,
            max_alpha = 1.0,
            size = (100,60),
            position = (screen_half_x-350,screen_half_y),
            anchor='center')

##############################################
# Create a Viewport instance and Presentation 
###############################################
viewport = Viewport(screen=screen, stimuli=[text_instruct_1, 
	text_instruct_2, 
	text_instruct_3, 
	taskStimulusImage, 
	barFrame, 
	posFbStimulusImage, 
	negFbStimulusImage, 
	bar])

p = Presentation(
    go_duration=(sec_n,'seconds'),
    trigger_go_if_armed=0, #wait for trigger
    viewports=[viewport])


# set and calculate variables for main state function 
next_TR_time = 0
prev_TR_time = 0
first_loop = 1
start_time = 0
TRcount = -1

bar_pos_max = 286
bar_pos_min = bar_width/2
bar_pos = bar_pos_min
prev_bar_pos = bar_pos_min
next_bar_pos = bar_pos_min
curr_bar_pos = bar_pos_min

img_name='%s%s' %(img_dir,stimImg_names[0])
currStimTxtr = Texture(img_name)
posFbVis = 0
posFbTxtr = txtr_posFb
negFbVis = 0
negFbTxtr = txtr_negFb
barVis = 0
frameVis = 0
alpha_min = 0.2
alpha_max = 1.0
fbScore = 0
fbScale = 5 
currBlock = 0
prevBlock = block_array[0]
currShow = 0
l_count = 0
r_count = 0
dist_array = [];
time_array = [];
startDetrend = 0
dist=0;
dist_detrend=0;

#################################
# Main state function           #
#################################

def getState(t):
    global TR_DUR, next_TR_time, prev_TR_time, currBlock,currShow 
    global first_loop, start_time, TRcount, currStimTxtr 
    global bar_pos, bar_pos_max, bar_pos_min, prev_bar_pos, curr_bar_pos, next_bar_pos
    global posFbVis, negFbVis, barVis, frameVis 
    global negFbTxtr, posFbTxtr
    global prevBlock, fbScore, fbScale
    global l_count, r_count
    global tcp_listner, startDetrend, dist_array, time_array, dist, dist_detrend

    bar_step = 0
    currBlockLen = 1
    blend_time = 0.8
    
    if (first_loop == 1) & (p.parameters.trigger_go_if_armed) :
      first_loop = 0
      start_time = VisionEgg.time_func()

      if TCPIP: 
        tcp_listener.buffer="" # reset buffer 
    
    if t > next_TR_time:
      TRcount = TRcount + 1
      
      prev_TR_time = next_TR_time
      next_TR_time = next_TR_time + TR_DUR

      currBlock = int(block_array[TRcount])
      currShow = int(show_array[TRcount])
      img_name='%s%s' %(img_dir,stimImg_names[TRcount])
      currStimTxtr = Texture(img_name)
      currBlockLen = int(block_len_array[TRcount])
      bar_step = (bar_pos_max)/float(currBlockLen)

      # reset various variables if block type changes
      if currBlock != prevBlock:
        prevBlock = currBlock
        prev_bar_pos = bar_pos_min
        curr_bar_pos = bar_pos_min
        next_bar_pos = bar_pos_min
        bar_pos = bar_pos_min
        posFbVis = 1
        negFbVis = 1
        barVis = 0
        frameVis = 1
        fbScore = 0

      # control visibility of fb symbols 
      if currBlock == -1:
        negFbVis = 2
        posFbVis = 1
        negFbTxtr = txtr_negFb
        posFbTxtr = txtr_posFb
      elif currBlock == 1:
        negFbVis = 1
        posFbVis = 2
        negFbTxtr = txtr_negFb
        posFbTxtr = txtr_posFb
      else: #currBlock == 0 
        barVis = 0
        frameVis = 1
        negFbVis = 1
        posFbVis = 1

      if currShow == 9999:
        barVis = 0
        frameVis = 1
      elif currShow == 8888:
        barVis = 0
        frameVis = 0
        negFbVis = 0
        posFbVis = 0
      elif ((currShow == 1111) & (currBlock == -1)):
        negFbVis = 2
        posFbVis = 1
        negFbTxtr = txtr_negFb
        posFbTxtr = txtr_posFb
        barVis = 0
        frameVis = 1
      elif ((currShow == 1111) & (currBlock == 1)):
        negFbVis = 1
        posFbVis = 2
        negFbTxtr = txtr_negFb
        posFbTxtr = txtr_posFb
        barVis = 0
        frameVis = 1
      elif ((currShow == 1) & (currBlock != 0)):
        barVis = 2
        frameVis = 2
        startDetrend = 1
    
      if (currBlock != 0) and ((currShow == 1) or (currShow == 1111)):
        fbScore = fbScore + (int(fbScale) - 5)/4.0*bar_step
      
      log_file.write("%5.3f;%d;%d;%5.3f;%5.3f;%5.3f;%d;%d;%d\n" % (t, int(currBlock), int(currShow), float(dist), float(dist_detrend), float(fbScore), int(fbScale), int(l_count), int(r_count)) )
      
      if AFNI_PLUGOUT == 1:
        updatePlugPlot('buttons', TRcount, l_count, r_count)

      l_count = 0
      r_count = 0
      
    if TRN:
        barVis = 0
        frameVis = 1
 

# get data from socket
    if TCPIP:
      tcp_buffer=str(tcp_listener.buffer)
      tcp_data=tcp_buffer.replace('\000', ''); # remove null byte
      #print "%s %s" %('tcp_data', tcp_data)

      if tcp_data != '\000' and tcp_data != "":
        dist=float(tcp_data)
        tcp_listener.buffer="" # reset buffer
        dist_array = dist_array + [dist]
        time_array = time_array + [t]
        if startDetrend:
          dist_detrend = detrendDist(time_array, dist_array)
        else:
          dist_detrend = dist;

        fbScale = discretizeDist(dist_detrend) 
        print 'time = %5.3f, dist = %5.3f, dist_detrend = %5.3f, fbScale = %d' % (t, dist, dist_detrend, fbScale)

    # this part of the code is executed constantly to dynamically update the sliding bar
    next_bar_pos = fbScore
    if curr_bar_pos < next_bar_pos:
      curr_bar_pos = prev_bar_pos + (next_bar_pos - prev_bar_pos)/blend_time*(t - prev_TR_time)
      if curr_bar_pos > next_bar_pos:
        curr_bar_pos = next_bar_pos
    elif curr_bar_pos > next_bar_pos:
      curr_bar_pos = prev_bar_pos + (next_bar_pos - prev_bar_pos)/blend_time*(t - prev_TR_time)
      if curr_bar_pos < next_bar_pos:
        curr_bar_pos = next_bar_pos
    else:
      prev_bar_pos = curr_bar_pos
    
    bar_pos = curr_bar_pos

    #print 'time = %5.3f, currBlock = %d, curr_bar_pos = %5.3f, next_bar_pos = %5.3f, bar_step = %5.3f, currBlockLen = %5.3f,fbScale = %d, ' % (t, currBlock, curr_bar_pos, next_bar_pos, bar_step, currBlockLen, fbScale) 
    
    return currBlock

#############################################
# state functions controlling presentation 
# based on globals set in getState
############################################
def myStimImage1(t):
	global currStimTxtr
	return currStimTxtr

def getBarPosition(t):
  global bar_pos, barVis, screen_half_x, screen_half_y
  if barVis == 0:
    bar_x = screen_half_x
    bar_y = screen_half_y
  else:
    bar_x = screen_half_x + bar_pos
    bar_y = screen_half_y
  return (bar_x, bar_y)

def getBarColor(t):
  global barVis, alpha_min, alpha_max
  r = 1; g = 1; b = 1; a = 0
  if barVis == 1:
    a = alpha_min
  elif barVis == 2:
    a = alpha_max 
  return (r,g,b,a)

def getFrameAlpha(t):
  global frameVis, alpha_min
  alpha = 0
  if frameVis == 1:
    alpha = alpha_min
  elif frameVis == 2:
    alpha = alpha_max - 0.5
  return alpha

def getNegFbTexture(t):
  global negFbTxtr;
  return negFbTxtr;

def getPosFbTexture(t):
  global posFbTxtr;
  return posFbTxtr;

def getPosFbAlpha(t):
  global posFbVis, alpha_min, alpha_max
  alpha = 0
  if posFbVis == 1:
    alpha = alpha_min
  elif posFbVis == 2:
    alpha = alpha_max
  return alpha

def getNegFbAlpha(t):
  global negFbVis, alpha_min, alpha_max
  alpha = 0
  if negFbVis == 1:

    alpha = alpha_min
  elif negFbVis == 2:
    alpha = alpha_max
  return alpha

def discretizeDist(dist):
  d = 0 
  if abs(dist) < 0.2:
    d = 0
  elif abs(dist) < 0.4:
    d = 1
  elif abs(dist) < 0.6:
    d = 2
  elif abs(dist) < 0.8:
    d = 3
  elif abs(dist) >= 0.8:
    d = 4

  return cmp(dist, 0)*d + 5

def detrendDist(time,dist):
  (slope,offset)=polyfit(time,dist,1)
  curr_dist = dist[-1]
  curr_time = time[-1]

  return curr_dist-(slope*curr_time+offset)

# Key presses 
def keydown(event):
    global  l_count, r_count 

    # Quit presentation 'p' with esc press
    if event.key == pygame.locals.K_ESCAPE: 
        p.parameters.go_duration = (0, 'frames')

    # Record button presses (1234)
    if event.key == pygame.locals.K_1 or event.key == pygame.locals.K_2 or pygame.locals.K_3 or event.key == pygame.locals.K_4:
            l_count += 1
    elif event.key == pygame.locals.K_6 or event.key == pygame.locals.K_7 or event.key == pygame.locals.K_8 or event.key == pygame.locals.K_9:
            r_count += 1



#######################
#  Define controllers #
#######################
###### Create an instance of the Controller class
trigger_in_controller = KeyboardTriggerInController(pygame.locals.K_5)
stimulus_on_controller = ConstantController(during_go_value=1,between_go_value=0)
stimulus_off_controller = ConstantController(during_go_value=0,between_go_value=1)

state_controller = FunctionController(during_go_func=getState)
taskImage1_controller = FunctionController(during_go_func=myStimImage1)

bar_position_controller = FunctionController(during_go_func=getBarPosition)
bar_color_controller = FunctionController(during_go_func=getBarColor)

posFbAlpha_controller = FunctionController(during_go_func=getPosFbAlpha)
posFbTexture_controller = FunctionController(during_go_func=getPosFbTexture)

negFbAlpha_controller = FunctionController(during_go_func=getNegFbAlpha)
negFbTexture_controller = FunctionController(during_go_func=getNegFbTexture)

frame_alpha_controller = FunctionController(during_go_func=getFrameAlpha)


#############################################################
#  Connect the controllers with the variables they control  #
#############################################################
if TCPIP: p.add_controller(None, None, tcp_listener) # Actually listens to the TCP socket
p.add_controller(p,'trigger_go_if_armed',trigger_in_controller)

p.add_controller(text_instruct_1,'on', stimulus_off_controller)
p.add_controller(text_instruct_2,'on', stimulus_off_controller)
p.add_controller(text_instruct_3,'on', stimulus_off_controller)

p.add_controller(taskStimulusImage,'on', stimulus_on_controller)
p.add_controller(taskStimulusImage,'texture', taskImage1_controller)

p.add_controller(posFbStimulusImage,'on', stimulus_on_controller)
p.add_controller(posFbStimulusImage,'max_alpha', posFbAlpha_controller)
p.add_controller(posFbStimulusImage,'texture', posFbTexture_controller)

p.add_controller(negFbStimulusImage,'on', stimulus_on_controller)
p.add_controller(negFbStimulusImage,'max_alpha', negFbAlpha_controller)
p.add_controller(negFbStimulusImage,'texture', negFbTexture_controller)


p.add_controller(barFrame,'on', stimulus_on_controller)
p.add_controller(barFrame,'max_alpha', frame_alpha_controller)
p.add_controller(bar,'on', stimulus_on_controller)
p.add_controller(bar,'position', bar_position_controller)
p.add_controller(bar,'color', bar_color_controller)

p.add_controller(p, 'trigger_go_if_armed', state_controller)

p.parameters.handle_event_callbacks = [(pygame.locals.KEYDOWN, keydown)]


#######################
#  Run the stimulus!  #
#######################
p.go()
#p.export_movie_go(frames_per_sec=2.0,filename_base='movie/faces')
log_file.close
