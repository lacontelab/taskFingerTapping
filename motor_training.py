#!/usr/bin/env python

#############################
# Flags and defines         #
#############################

TCPIP         = 0     # Set 1 to receive data over TCP/IP
TCPIP_PORT    = 8000  # Port receiving TCP/IP data
TCPIP_GUI     = 0     # Open GUI to initialize TCP/IP 
TCPIP_SIM     = 0     # Simulate TCPIP data by using data from LABEL_FILE

TR_DUR        = 2     # TR duration in seconds
IMAGE_SIZE    = (800,600)  # resolution of stimulus images
SCREEN_SIZE   = (1024,768) # screen size 
LABEL_FILE    = 'labels_train.dat' # label file controlling presentation

AFNI_PLUGOUT  = 1     # Set 1 to enable afni plugout plots

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
from    numpy import polyfit
import  pygame
import  OpenGL.GL as gl
from    string import *
import  Image, ImageDraw # Python Imaging Library (PIL)
import  os, sys
import afni

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
time_str = time.strftime ('%m-%d-%Y_%Hh-%Mm');
prog_name = split (os.path.basename (sys.argv[0]), '.')
log_file_name = 'logfile_' + prog_name[0] + '_' + time_str + '.log'

# open label and log file
label_file=open(LABEL_FILE, 'r')
log_file=open(log_file_name,'w')

# initialize log file
log_file.write("# time;currBlock;currShow;dist;dist_detrend;fbScore;fbScale;l_count;r_count\n")

# some variable definitions     
TR_n = int(label_file.readline())
sec_n = TR_n*TR_DUR

# define arrays read from label file
block_array     = []
show_array      = []
block_lengths   = []
block_len_array = []
stimImg_names   = []
fb_array        = []

# read label file
for line in label_file:
    b, s, i, fb, xxx = line.split(";", 4)
    block_array = block_array + [b]
    show_array = show_array + [s]
    stimImg_names = stimImg_names + [i]
    fb_array = fb_array + [fb]

label_file.close

#print '\nblock: %s' % (block_array)
#print 'show: %s' % (show_array)
#print 'img names: %s' % (stimImg_names),

txtr_posFb = Texture('right.png')
txtr_negFb = Texture('left.png')
txtr_frame = Texture('frame.png')

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

# try establishing connection to afni for plotting button presses

if AFNI_PLUGOUT:
  afni_plugout_connected=1
  try:
    afni_host_ip=afni.getAfniHostIP()
    plugout_command ='plugout_drive -port 8100 -host %s' % afni_host_ip
    ff=os.popen(plugout_command, 'w') 
  except:
    afni_plugout_connected=0

# initialize plot with button presses
if afni_plugout_connected:
  try:
    afni.closePlugPlot(ff, 'plot_0')
    afni.openPlugPlot(ff, 'plot_0', 'button presses', 2, 0, TR_n, 'TRs', 0, 20, 'presses per TR', "left right")
  except:
    afni_plugout_connected=0

 
#################################
#  Initialize the various bits  #
#################################

# Initialize OpenGL graphics screen.
#screen = VisionEgg.Core.Screen(size=SCREEN_SIZE, fullscreen=True)
screen = get_default_screen()

# Set the background color to white (RGBA).
screen.parameters.bgcolor = (0.0,0.0,0.0,0.0)

screen_half_x = screen.size[0]/2
screen_half_y = screen.size[1]/2

if TCPIP: 
  text_instruct3_str='WITH FEEDBACK'
else:
  text_instruct3_str=''

text_instruct_1 = Text(text='',
            color=(1.0,1.0,1.0),
            position=(screen_half_x,screen_half_y+120),
	        font_size=40,
	        anchor='center')

text_instruct_2 = Text(text='FINGER TAPPING',
            color=(1.0,1.0,1.0),
            position=(screen_half_x,screen_half_y+120),
	        font_size=80,
	        anchor='center')

text_instruct_3 = Text(text=text_instruct3_str,
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

img_name=str(stimImg_names[0])
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
bar_blend_time = 0.8
bar_step = 0
currBlockLen = 1

#################################
# Main state function           #
#################################

def getState(t):
    global next_TR_time, prev_TR_time, TRcount
    global first_loop, start_time, currStimTxtr 
    global bar_pos, bar_pos_max, bar_pos_min, prev_bar_pos, curr_bar_pos, next_bar_pos
    global bar_step, currBlockLen
    global posFbVis, negFbVis, barVis, frameVis 
    global negFbTxtr, posFbTxtr
    global prevBlock, fbScore, fbScale
    global tcp_listner, startDetrend, dist_array, time_array, dist, dist_detrend
    global afni_plugout_connected

    global l_count, r_count

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
      img_name=str(stimImg_names[TRcount])
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
      

      if afni_plugout_connected:
        try:
          afni.updatePlugPlot2(ff, 'plot_0', TRcount, l_count, r_count)
        except:
          afni_plugout_connected=0

      log_file.write("%5.3f;%d;%d;%5.3f;%5.3f;%5.3f;%d;%d;%d\n" % (t, int(currBlock), int(currShow), float(dist), float(dist_detrend), float(fbScore), int(fbScale), int(l_count), int(r_count)) )
      
      # rest counter for left and right button presses
      l_count = 0
      r_count = 0
      
    if not TCPIP and not TCPIP_SIM: 
      barVis = 0 
      frameVis = 1
 
    # get data from socket
    if TCPIP:
      tcp_buffer=str(tcp_listener.buffer)
      tcp_data=tcp_buffer.replace('\000', ''); # remove null byte
      #print "%s %s" %('tcp_data', tcp_data)

      if tcp_data != '\000' and tcp_data != "" and tcp_data.lower() != 'nan':
        dist=float(tcp_data)
        tcp_listener.buffer="" # reset buffer
        dist_array = dist_array + [dist]
        time_array = time_array + [t]

        if startDetrend:
          dist_detrend = detrendDist(time_array, dist_array)
        else:
          dist_detrend = dist;

        fbScale = discretizeDist(dist_detrend) 
    elif TCPIP_SIM: 
      # get dummy data from control file
      fbScale = int(fb_array[TRcount])
    else:
      fbScale=0.0;

    # update slider bar position dynamically 
    next_bar_pos = fbScore
    if curr_bar_pos < next_bar_pos:
      curr_bar_pos = prev_bar_pos + (next_bar_pos - prev_bar_pos)/bar_blend_time*(t - prev_TR_time)
      if curr_bar_pos > next_bar_pos:
        curr_bar_pos = next_bar_pos
    elif curr_bar_pos > next_bar_pos:
      curr_bar_pos = prev_bar_pos + (next_bar_pos - prev_bar_pos)/bar_blend_time*(t - prev_TR_time)
      if curr_bar_pos < next_bar_pos:
        curr_bar_pos = next_bar_pos
    else:
      prev_bar_pos = curr_bar_pos
    
    bar_pos = curr_bar_pos

    return 1

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

    # Record button presses 1,2,3,4 as left 
    if event.key == pygame.locals.K_1 or \
        event.key == pygame.locals.K_2 or \
        event.key == pygame.locals.K_3 or \
        event.key == pygame.locals.K_4:
      l_count += 1

    # Record button presses 6,7,8,9 as left 
    elif event.key == pygame.locals.K_6 or \
        event.key == pygame.locals.K_7 or \
        event.key == pygame.locals.K_8 or \
        event.key == pygame.locals.K_9:
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
