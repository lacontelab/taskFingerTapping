import sys
import socket

# use this default IP address if the IP address can not be determined using
#   hostnames
AFNI_DEFAULT_HOST_IP='127.0.0.1'

# Instead of using separate y-axis (subplots) for each plot UNIte them 
#   using only one y-axis (currently only supported by our version of AFNI, 
#   added by Jeff Zemla) 
AFNI_GRAPH_UNI=1

# set GEOMetry of AFNIi plots
AFNI_PLOT_GEOM='1100x400+850+680'

def getAfniHostIP():

  # get hostname of stimulus computer
  try: 
    hostname = socket.gethostname()
  except: 
    hostname = 'undefined'
 
  # map AFNI host (TABS) to stimulus computer 
  # R1082
  if 'd1l-0000j2n9nn1' in hostname.lower():
    try:
      afni_host_ip=socket.gethostbyname('tabs-mr1082')
    except:
      afni_host_ip=AFNI_DEFAULT_HOST_IP

  # R1081
  elif 'd1l-0000j2nbnn1' in hostname.lower():
    try:
      afni_host_ip=socket.gethostbyname('tabs-mr1081')
    except:
      afni_host_ip=AFNI_DEFAULT_HOST_IP

  # CRC
  elif 'crc-mri-byhzcp1' in hostname.lower():
    try:
      afni_host_ip=socket.gethostbyname('tabs-mr1052')
    except:
      afni_host_ip=AFNI_DEFAULT_HOST_IP
    
  else:
    afni_host_ip=AFNI_DEFAULT_HOST_IP
    
  return afni_host_ip

'''
Could someday write a general updatePlugPlot that takes arrays... But for now...
'''
def updatePlugPlot5 (ff, name, x, y1, y2, y3, y4, y5):
    try:
      print >> ff, "ADDTO_GRAPH_XY %s %f %f %f %f %f %f" %(str(name), 
          float(x), float(y1), float(y2), float(y3), float(y4), float(y5))
    except :
      print "Warning: Updating plugout plot failed!"
      raise

    ff.flush()

def updatePlugPlot4 (ff, name, x, y1, y2, y3, y4):
    try:
      print >> ff, "ADDTO_GRAPH_XY %s %f %f %f %f %f" %(str(name), 
          float(x), float(y1), float(y2), float(y3), float(y4))
    except :
      print "Warning: Updating plugout plot failed!"
      raise

    ff.flush()

def updatePlugPlot3 (ff, name, x, y1, y2, y3):
    try:
      print >> ff, "ADDTO_GRAPH_XY %s %f %f %f %f" %(str(name), 
          float(x), float(y1), float(y2), float(y3))
    except :
      print "Warning: Updating plugout plot failed!"
      raise

    ff.flush()

def updatePlugPlot2 (ff, name, x, y1, y2):
    try:
      print >> ff, "ADDTO_GRAPH_XY %s %f %f %f" %(str(name), 
          float(x), float(y1), float(y2))
    except :
      print "Warning: Updating plugout plot failed!"
      raise

    ff.flush()

def updatePlugPlot1 (ff, name, x, y1):
    try:
      print >> ff, "ADDTO_GRAPH_XY %s %f %f" %(str(name), 
          float(x), float(y1))
    except :
      print "Warning: Updating plugout plot failed!"
      raise

    ff.flush()

def closePlugPlot(ff, name):
    try:
      print >> ff, "CLOSE_GRAPH_XY %s" %str(name)
    except:
      print "Warning: closing plugout plot failed!"
      raise

    ff.flush()

def openPlugPlot(ff, name, title, y_num, x_min, x_max, x_label, y_min, y_max, y_label, y_names):
    try:
      print >>ff, "SETENV AFNI_graph_uni %d" %AFNI_GRAPH_UNI
      print >>ff, "OPEN_GRAPH_XY %s '%s' %f %f '%s' %f %f %f '%s' %s" %(str(name), \
      str(title), float(x_min), float(x_max), str(x_label), float(y_num), float(y_min), float(y_max), str(y_label), str(y_names) )
      print >>ff, "SET_GRAPH_GEOM %s geom=%s" %(name, AFNI_PLOT_GEOM)
    except:
      print "Warning: opening plugout plot failed!"
      raise
    
    ff.flush()

if __name__ == '__main__':
   print '** this is just a collection of afni utility functions and not a main module'
   sys.exit(1)

