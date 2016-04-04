#!/home/steven/anaconda2/bin/python

from skimage import io
import numpy as np
import os, string, datetime
from PIL import Image, ImageDraw
from subprocess import Popen
import json
from pprint import pprint
import sys
import numpy

#--------------------------------------------------------------------------------------#
# Constants
#--------------------------------------------------------------------------------------#

CUR_DIR = os.getcwd()
PARTICIPANT_DIR = os.path.join(CUR_DIR, 'results/participant_')
IMG_DIR = os.path.join(CUR_DIR, 'images')
ORIG_IMG_DIR = os.path.join(IMG_DIR, 'Original')
GT_IMG_DIR = os.path.join(IMG_DIR, 'Binary Ground Truth')

POINT_INPUT = 1
STROKE_INPUT = 2

# Foreground and background greyscale pixel instensities, when converte from blue and green
# Discovered by inspection
FG_GREYSCALE_INT = 29;
BG_GREYSCALE_INT = 149;

#--------------------------------------------------------------------------------------#
# Main program
#--------------------------------------------------------------------------------------#

# Make sure we are only getting the one JSON input file
if len(sys.argv) != 2:
    print "\nUsage: %s <JSON_input_file>\n" % sys.argv[0]
    exit()

# Grab the JSON input
JSON_FILE = sys.argv[1]

with open(JSON_FILE) as data_file:    
    trial_data = json.load(data_file)
    
# Get a list of participant IDs
id_list = []
for i in range(0, len(trial_data)):
    cur_id = trial_data[i]["participant"]
    if cur_id not in id_list:
        id_list.append(cur_id)
        
# Now make directories for each particpant's results
for i in range(0, len(id_list)):

    cur_participant_dir = PARTICIPANT_DIR + "%s" % id_list[i];
    
    cur_stroke_dir = os.path.join(cur_participant_dir, 'stroke')
    cur_point_dir = os.path.join(cur_participant_dir, 'point')

    if not os.path.exists(cur_stroke_dir):
        os.makedirs(cur_stroke_dir)
    if not os.path.exists(cur_point_dir):
        os.makedirs(cur_point_dir)
        
        
cur_id = 1

point_time = [];
stroke_time = [];
        
# Segment each trial
for i in range(0, len(trial_data)):
    
    # Make sure we know which participant ID we are currently on
    if cur_id < trial_data[i]["participant"]:
        cur_id += 1
        
    # Decide where we will be saving these results and get the elapsed time as well
    this_time = trial_data[i]["interactions"]["elapsed"] / 1000.0;
    cur_par_dir = PARTICIPANT_DIR + "%s" % cur_id
    if trial_data[i]["input_method"] == POINT_INPUT:
        cur_path = os.path.join(cur_par_dir, "point")
        point_time.append(this_time);
    else:
        cur_path = os.path.join(cur_par_dir, "stroke")
        stroke_time.append(this_time);
    
    # Load the original image
    cur_img = os.path.basename(trial_data[i]["interactions"]["filename"])
    image_name = os.path.splitext(cur_img)[0] 
    cur_img_path = os.path.join(ORIG_IMG_DIR, cur_img)
    im = Image.open(cur_img_path)
    
    #gt_img_path = os.path.join(GT_IMG_DIR, image_name + "-GT.png")
    
    greyscale = Image.new('L', im.size )
    for evt in trial_data[i]["interactions"]["events"]:
        if not evt['erased']:
            intensity = evt['colour']
            draw = ImageDraw.Draw(greyscale)
            # Grab all the points for the current event
            pts = evt['points']
            # If the input was a stroke, there will be many pts for a single event
            if len(pts) > 1:
                draw.line([(pt['x'], pt['y']) for pt in evt['points']], fill=intensity)
            # Otherwise if the input was a point, there will only be one pt
            else:
                draw.point([pts[0]['x'], pts[0]['y']], fill=intensity)
                
                #print "%d" % greyscale.getpixel((pts[0]['x'],pts[0]['y']))
                
    # Save the stroke image for use by the segmentation algorithm.
    gsimg = cur_img + '.strokes.tif'
    gsfile = os.path.join(cur_path, gsimg)
    io.imsave(gsfile, greyscale)
    
    # Execute the external segmentation algorithm.
    executable = os.path.join(CUR_DIR, 'boykovmaxflowgeneric')
    p = Popen([executable,'--minregionsize=500', '--outputdir={0}'.format(cur_path), '--strokefglabel={0}'.format(FG_GREYSCALE_INT), '--strokebglabel={0}'.format(BG_GREYSCALE_INT), cur_img_path, gsfile])
    p.wait()
    
    # Make .png copies of the .tif output images
    resultimage = os.path.join(cur_path, cur_img + '.segmentation.tif')
    im = Image.open(resultimage)
    resultimage = os.path.join(cur_path, cur_img + '.segmentation.png')
    io.imsave(resultimage, im)
    
    
print "Average point time: %0.3f  Std. Dev.: %0.3f\n" % (numpy.mean(point_time), numpy.std(point_time))
print "Average stroke time: %0.3f  Std. Dev.: %0.3f\n" % (numpy.mean(stroke_time), numpy.std(stroke_time))
