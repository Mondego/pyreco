__FILENAME__ = 01_1_new-project
# -*- coding: utf-8 -*-
import sys
import os
import os.path
import xml.etree.ElementTree as et
import cv

PROJECTS_DIR_NAME = "projects"


def main():
	movie_path, movie_file = os.path.split(sys.argv[1])
	os.chdir(os.path.split(sys.argv[0])[0])
	project_dir = os.path.splitext(movie_file)[0]
	try:
		os.mkdir(os.path.join(PROJECTS_DIR_NAME, project_dir))
	except:
		pass
	
	# generate project xml file:
	root = et.Element("movie")
	#root.set("title", project_dir)
	root.set("path", sys.argv[1])
	#root.set("frames", str(frame_count))
	#root.set("fps", str(fps))
	
	# wrap and save
	tree = et.ElementTree(root)
	os.chdir(os.path.join(PROJECTS_DIR_NAME, project_dir))
	tree.write("project.xml")
	
	print "don't forget to crop / remove any black borders!"
	
	raw_input("- done -")
	return


# #########################
if __name__ == "__main__":
	main()
# #########################
########NEW FILE########
__FILENAME__ = 02_1_shot-detection
# -*- coding: utf-8 -*-
import sys
import cv
import time
import winsound
import win32api, win32con
import os.path
import xml.etree.ElementTree as et


DEBUG = False
#DEBUG = True
DEBUG_INTERACTIVE = False

OUTPUT_DIR_NAME = "shot_snapshots"
soundfile = "ton.wav"


def main():
	BLACK_AND_WHITE = False
	THRESHOLD = 0.48
	BW_THRESHOLD = 0.4
	
	os.chdir(sys.argv[1])
	try:
		os.mkdir(OUTPUT_DIR_NAME)
	except:
		pass
	
	if len(sys.argv) > 2:
		if sys.argv[2] == "bw":
			BLACK_AND_WHITE = True
			THRESHOLD = BW_THRESHOLD
			print "##########"
			print " B/W MODE"
			print "##########"
	
	tree = et.parse("project.xml")
	movie = tree.getroot()
	file_path = movie.attrib["path"]
	cap = cv.CreateFileCapture(file_path)
	
	if DEBUG:
		cv.NamedWindow("win", cv.CV_WINDOW_AUTOSIZE)
		cv.MoveWindow("win", 200, 200)

	hist = None
	prev_hist = None
	prev_img = None

	pixel_count = None
	frame_counter = 0

	last_frame_black = False
	black_frame_start = -1

	t = time.time()

	while 1:
		img_orig = cv.QueryFrame(cap)
		
		if not img_orig: # eof
			cv.SaveImage(OUTPUT_DIR_NAME + "\\%06d.png" % (frame_counter-1), prev_img)
			"""movie.set("frames", str(frame_counter))
			tree.write("project.xml")"""
			break
		
		img = cv.CreateImage((int(img_orig.width/4), int(img_orig.height/4)), cv.IPL_DEPTH_8U, 3)
		cv.Resize(img_orig, img, cv.CV_INTER_AREA)
		
		if frame_counter == 0: # erster frame
			cv.SaveImage(OUTPUT_DIR_NAME + "\\%06d.png" % (0), img)
			pixel_count = img.width * img.height
			prev_img = cv.CreateImage(cv.GetSize(img), cv.IPL_DEPTH_8U, 3)
			cv.Zero(prev_img)
		
		if DEBUG and frame_counter % 2 == 1:
			cv.ShowImage("win", img)
		
		img_hsv = cv.CreateImage(cv.GetSize(img), cv.IPL_DEPTH_8U, 3)
		cv.CvtColor(img, img_hsv, cv.CV_BGR2HSV)
		
		# #####################
		# METHOD #1: find the number of pixels that have (significantly) changed since the last frame
		diff = cv.CreateImage(cv.GetSize(img), cv.IPL_DEPTH_8U, 3)
		cv.AbsDiff(img_hsv, prev_img, diff)
		cv.Threshold(diff, diff, 10, 255, cv.CV_THRESH_BINARY)
		d_color = 0
		for i in range(1, 4):
			cv.SetImageCOI(diff, i)
			d_color += float(cv.CountNonZero(diff)) / float(pixel_count)
		
		if not BLACK_AND_WHITE:
			d_color = float(d_color/3.0) # 0..1
		
		# #####################
		# METHOD #2: calculate the amount of change in the histograms
		h_plane = cv.CreateMat(img.height, img.width, cv.CV_8UC1)
		s_plane = cv.CreateMat(img.height, img.width, cv.CV_8UC1)
		v_plane = cv.CreateMat(img.height, img.width, cv.CV_8UC1)
		cv.Split(img_hsv, h_plane, s_plane, v_plane, None)
		planes = [h_plane, s_plane, v_plane]
		
		hist_size = [50, 50, 50]
		hist_range = [[0, 360], [0, 255], [0, 255]]
		if not hist:
			hist = cv.CreateHist(hist_size, cv.CV_HIST_ARRAY, hist_range, 1)
		cv.CalcHist([cv.GetImage(i) for i in planes], hist)
		cv.NormalizeHist(hist, 1.0)
		
		if not prev_hist:
			prev_hist = cv.CreateHist(hist_size, cv.CV_HIST_ARRAY, hist_range, 1)
			# wieso gibt es kein cv.CopyHist()?!
			cv.CalcHist([cv.GetImage(i) for i in planes], prev_hist)
			cv.NormalizeHist(prev_hist, 1.0)
			continue
		
		d_hist = cv.CompareHist(prev_hist, hist, cv.CV_COMP_INTERSECT)
		
		# combine both methods to make a decision
		if ((0.4*d_color + 0.6*(1-d_hist))) >= THRESHOLD:
			if DEBUG:
				if frame_counter % 2 == 0:
					cv.ShowImage("win", img)
				winsound.PlaySound(soundfile, winsound.SND_FILENAME|winsound.SND_ASYNC)
			print "%.3f" % ((0.4*d_color + 0.6*(1-d_hist))), "%.3f" % (d_color), "%.3f" % (1-d_hist), frame_counter
			if DEBUG and DEBUG_INTERACTIVE:
				if win32api.MessageBox(0, "cut?", "", win32con.MB_YESNO) == 6: #yes
					cv.SaveImage(OUTPUT_DIR_NAME + "\\%06d.png" % (frame_counter), img)
			else:
				cv.SaveImage(OUTPUT_DIR_NAME + "\\%06d.png" % (frame_counter), img)
		
		cv.CalcHist([cv.GetImage(i) for i in planes], prev_hist)
		cv.NormalizeHist(prev_hist, 1.0)
		
		# #####################
		# METHOD #3: detect series of (almost) black frames as an indicator for "fade to black"
		average = cv.Avg(v_plane)[0]
		if average <= 0.6:
			if not last_frame_black: # possible the start
				print "start", frame_counter
				black_frame_start = frame_counter
			last_frame_black = True
		else:
			if last_frame_black: # end of a series of black frames
				cut_at = black_frame_start + int( (frame_counter - black_frame_start) / 2 )
				print "end", frame_counter, "cut at", cut_at
				img_black = cv.CreateImage((img_orig.width/4, img_orig.height/4), cv.IPL_DEPTH_8U, 3)
				cv.Set(img_black, cv.RGB(0, 255, 0))
				cv.SaveImage(OUTPUT_DIR_NAME + "\\%06d.png" % (cut_at), img_black)
			last_frame_black = False
		
		cv.Copy(img_hsv, prev_img)
		frame_counter += 1
		
		if DEBUG:
			if cv.WaitKey(1) == 27:
				break
		

	if DEBUG:
		cv.DestroyWindow("win");
	
	print "%.2f min" % ((time.time()-t) / 60)
	#raw_input("- done -")
	return


# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 02_2_save-shots
# -*- coding: utf-8 -*-
import sys
import os
import os.path


OUTPUT_DIR_NAME = "shot_snapshots"


def main():
	os.chdir(sys.argv[1])
	
	#frames = [os.path.splitext(file)[0] for file in os.listdir(os.getcwd() + "\\" + OUTPUT_DIR_NAME) if not os.path.isdir(file)]
	import glob
	frames = [os.path.splitext( os.path.basename(file) )[0] for file in glob.glob(OUTPUT_DIR_NAME + "\\*.png")] #os.getcwd() + "\\" +
	frames = [int(frame) for frame in frames]
	
	import xml.etree.ElementTree as et
	tree = et.parse("project.xml")
	movie = tree.getroot()
	# frame count 
	movie.set("frames", str( frames[-1] - frames[0] ))
	movie.set("start_frame", str( frames[0] ))
	movie.set("end_frame", str( frames[-1] - 1 ))
	tree.write("project.xml")
	
	f = open(os.path.join(os.getcwd(), "shots.txt"), "w")
	
	for i, frame in enumerate(frames):
		if i == len(frames)-1:
			break
		
		f.write(str(frame) + "\t" + str(frames[i+1]-1) + "\t" + str(frames[i+1] - frame) + "\n")
		
		if i > 0:
			diff = frames[i] - frames[i-1]
			if abs(diff) <= 5:
				print "%d -> %d: %d" % (frames[i-1], frames[i], diff)
	
	f.close()
	print "don't forget to add FPS information!"
	raw_input("- done -")
	return


# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 02_3_shot-slitscan
# -*- coding: utf-8 -*-
import cv
import math
import os
import sys
import xml.etree.ElementTree as et
import time


OUTPUT_DIR_NAME = "shot_slitscans"


def main():
	os.chdir(sys.argv[1])
	try:
		os.mkdir(OUTPUT_DIR_NAME)
	except OSError:
		pass
	
	tree = et.parse("project.xml")
	
	movie = tree.getroot()
	file_path = movie.attrib["path"]
	
	cap = cv.CreateFileCapture(file_path)
	cv.QueryFrame(cap)
	
	# skip frames in the beginning, if neccessary
	start_frame = int( movie.attrib["start_frame"] )
	for i in range(start_frame):
		cv.QueryFrame(cap)
	
	f = open("shots.txt", "r")
	lines = [line for line in f if line]
	f.close()
	
	t = time.time()
	
	w = None
	h = None
	
	#for line in f:
	for nr, line in enumerate(lines):
		print (nr+1), "/", len(lines)
		
		#frame_from, frame_to, width, scene_nr = [int(i) for i in line.split("\t")]
		#width, scene_nr = [int(i) for i in line.split("\t")][2:]
		start_frame, end_frame, width = [int(splt) for splt in line.split("\t")]
		#width *= STRETCH_FAKTOR
		
		faktor = None
		output_img = None
		
		for frame_counter in range(width):
			#if frame_counter % STRETCH_FAKTOR == 0:
			#	img = cv.QueryFrame(cap)
			#	if not img:
			#		break
			
			img = cv.QueryFrame(cap)
			if not img:
				break
			
			if nr == 0:
				w = img.width
				h = img.height
				
			if frame_counter == 0:
				faktor = float(w) / float(width)
				output_img = cv.CreateImage((width, h), cv.IPL_DEPTH_8U, 3)
			
			col_nr = faktor * (frame_counter+0.5)
			col_nr = int( math.floor(col_nr) )
			#print frame_counter, width, col_nr, w
			col = cv.GetCol(img, col_nr)
			
			for i in range(h):
				cv.Set2D(output_img, i, frame_counter, cv.Get1D(col, i))
			
		#return
			
		cv.SaveImage(OUTPUT_DIR_NAME + "\\shot_slitscan_%03d_%d.png" % (nr+1, start_frame), output_img)
	
	print "%.2f min" % ((time.time()-t) / 60)
	#raw_input("- done -")
	return
	

# #########################
if __name__ == "__main__":
	#STRETCH_FAKTOR = 1
	main()
# #########################

########NEW FILE########
__FILENAME__ = 02_4_final-cut
# -*- coding: utf-8 -*-
import sys
import os
import glob
import cv


startframe = 0


def main():
	global startframe
	os.chdir(sys.argv[1])
	os.chdir("shot_slitscans")
	
	'''cv.NamedWindow("win", cv.CV_WINDOW_AUTOSIZE)
	cv.MoveWindow("win", 500, 200)
	cv.SetMouseCallback("win", mouse_callback)'''
	
	bg_img = cv.CreateImage((576, 576), cv.IPL_DEPTH_8U, 1)
	#cv.Set(bg_img, (180))
	
	files = sorted( glob.glob("*.png") )
	i = 0
	while i < len(files):
		file = files[i]
		startframe = int( file.split("_")[3].split(".")[0] )
		print startframe
		
		cap = cv.CreateFileCapture(file)
		img = cv.QueryFrame(cap)
		
		win_name = "%d" % (int(float(i+1)*100.0/len(files))) + "% - " + file
		cv.NamedWindow(win_name, cv.CV_WINDOW_AUTOSIZE)
		cv.MoveWindow(win_name, 500, 200)
		cv.SetMouseCallback(win_name, mouse_callback)
		
		cv.ShowImage(win_name, bg_img)
		cv.ShowImage(win_name, img)
		
		key = cv.WaitKey(0)
		if key == 2555904: # right arrow
			i += 1
		elif key == 2424832: # left arrow
			i -= 1
			if i < 0:
				i = 0
		elif key == 27: # ESC
			break
		
		cv.DestroyWindow(win_name)
	
	os.chdir("../../..")
	os.system("python 02_2_save-shots.py \"" + sys.argv[1] + "\"")


def mouse_callback(event, x, y, flags, param):	
	if event == 1: # left mouse down
		# draw line?
		pass
	elif event == 4: # left mouse up
		f = open("../shot_snapshots/%06d.png" % (startframe + x), "w")
		print "cut added at %06d" % (startframe + x)
		f.close()


# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 02_5_100-stills
# -*- coding: utf-8 -*-
import cv
import math
import os
import sys
import xml.etree.ElementTree as et


OUTPUT_DIR = "100_stills"
WIDTH = 240


def main():
	os.chdir(sys.argv[1])
	try:
		os.mkdir(OUTPUT_DIR)
	except OSError:
		pass
	
	tree = et.parse("project.xml")
	
	movie = tree.getroot()
	file_path = movie.attrib["path"]
	#fps = float( movie.attrib["fps"] )
	
	cap = cv.CreateFileCapture(file_path)
	cv.QueryFrame(cap)
	
	# skip frames in the beginning, if neccessary
	start_frame = int( movie.attrib["start_frame"] )
	for i in range(start_frame):
		cv.QueryFrame(cap)
	
	end_frame = int( movie.attrib["end_frame"] )
	every_nth_frame = int( (end_frame - start_frame) / 100 )
	print "every", every_nth_frame, "frames"
	#print "=", every_nth_frame / fps, "sec"
	frame = start_frame
	counter = 1
	
	while 1:
		print counter
		img = cv.QueryFrame(cap)
		if not img or frame > end_frame:
			break
		
		img_small = cv.CreateImage((WIDTH, int( img.height * float(WIDTH)/img.width )), cv.IPL_DEPTH_8U, 3)
		cv.Resize(img, img_small, cv.CV_INTER_CUBIC)
		
		cv.SaveImage(OUTPUT_DIR + "\\still_%07d.jpg" % (frame), img_small)
		
		for i in range(every_nth_frame-1):
			cv.GrabFrame(cap)
		
		frame += every_nth_frame
		counter += 1
	
	#raw_input("- done -")
	return


# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 03_1_shot-colors
# -*- coding: utf-8 -*-
import cv
import numpy
import scipy.cluster
import os
import sys
import xml.etree.ElementTree as et
import time
import math

from lib import hls_sort2


def unique(seq, idfun=None): 
	if idfun is None:
		def idfun(x): return x
	seen = {}
	result = []
	for item in seq:
		marker = idfun(item)
		if marker in seen: continue
		seen[marker] = 1
		result.append(item)
	return result


def unique2(seq):
	checked = []
	for e in seq:
		if e not in checked:
			checked.append(e)
	return checked


DEBUG = False

NUM_CLUSTERS = 5
PIXELS_PER_COLOR = 20
EVERY_NTH_FRAME = 5
OUTPUT_DIR_NAME = "shot_colors"


def main():
	os.chdir(sys.argv[1])
	try:
		os.mkdir(OUTPUT_DIR_NAME)
	except:
		pass
	
	tree = et.parse("project.xml")
	movie = tree.getroot()
	file_path = movie.attrib["path"]
	cap = cv.CreateFileCapture(file_path)
	cv.QueryFrame(cap)
	
	# skip frames in the beginning, if neccessary
	start_frame = int( movie.attrib["start_frame"] )
	for i in range(start_frame):
		cv.QueryFrame(cap)
	
	if DEBUG:
		cv.NamedWindow("win", cv.CV_WINDOW_AUTOSIZE)
		cv.MoveWindow("win", 200, 200)

	t = time.time()
	
	f = open("shots.txt", "r")
	scene_durations = [int(values[2]) for values in [line.split("\t") for line in f if line]]
	f.close()
	
	for scene_nr, duration in enumerate(scene_durations):
		print "shot #%d" % scene_nr, "/", len(scene_durations)-1
		
		h = int( math.ceil( float(duration) / EVERY_NTH_FRAME ) )
		output_img = cv.CreateImage((PIXELS_PER_COLOR*NUM_CLUSTERS, h), cv.IPL_DEPTH_8U, 3)
		frame_counter = 0
		
		for i in range(duration):
			img_orig = cv.QueryFrame(cap)
			if not img_orig: # eof
				break
			
			if i % EVERY_NTH_FRAME != 0:
				continue
			
			new_width = int(img_orig.width/4.0)
			new_height = int(img_orig.height/4.0)
			
			img_small = cv.CreateImage((new_width, new_height), cv.IPL_DEPTH_8U, 3)
			cv.Resize(img_orig, img_small, cv.CV_INTER_AREA)
			
			if DEBUG:
				cv.ShowImage("win", img_small)
			
			img = cv.CreateImage((new_width, new_height), cv.IPL_DEPTH_8U, 3)
			cv.CvtColor(img_small, img, cv.CV_BGR2HLS)
			
			# convert to numpy array
			a = numpy.asarray(cv.GetMat(img))
			a = a.reshape(a.shape[0] * a.shape[1], a.shape[2]) # make it 1-dimensional
			
			# set initial centroids
			init_cluster = []
			for y in [int(new_height/4.0), int(new_height*3/4.0)]:
				for x in [int(new_width*f) for f in [0.25, 0.75]]:
					init_cluster.append(a[y * new_width + x])
			init_cluster.insert(2, a[int(new_height/2.0) * new_width + int(new_width/2.0)])
			
			centroids, labels = scipy.cluster.vq.kmeans2(a, numpy.array(init_cluster))
			
			vecs, dist = scipy.cluster.vq.vq(a, centroids) # assign codes
			counts, bins = scipy.histogram(vecs, len(centroids)) # count occurrences
			centroid_count = []
			for i, count in enumerate(counts):
				#print centroids[i], count
				if count > 0:
					centroid_count.append((centroids[i].tolist(), count))
			
			#centroids = centroids.tolist()
			#centroids.sort(hls_sort)
			
			centroid_count.sort(hls_sort2)
			
			px_count = new_width * new_height
			x = 0
			for item in centroid_count:
				count = item[1] * (PIXELS_PER_COLOR*NUM_CLUSTERS)
				count = int(math.ceil(count / float(px_count)))
				centroid = item[0]
				for l in range(count):
					if x+l >= PIXELS_PER_COLOR*NUM_CLUSTERS:
						break
					cv.Set2D(output_img, frame_counter, x+l, (centroid[0], centroid[1], centroid[2]))
				x += count
			
			if DEBUG:
				if cv.WaitKey(1) == 27:
					cv.DestroyWindow("win");
					return
			
			frame_counter += 1
		
		output_img_rgb = cv.CreateImage(cv.GetSize(output_img), cv.IPL_DEPTH_8U, 3)
		cv.CvtColor(output_img, output_img_rgb, cv.CV_HLS2BGR)
		cv.SaveImage(OUTPUT_DIR_NAME + "\\shot_colors_%04d.png" % (scene_nr), output_img_rgb)
	
	if DEBUG:
		cv.DestroyWindow("win");
	print "%.2f min" % ((time.time()-t) / 60)
	#raw_input("- done -")
	return



# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 03_2_shot-colors_avg
# -*- coding: utf-8 -*-
import cv
import numpy
import scipy.cluster
import os
import os.path
import sys
import math

from lib import hls_sort2


DEBUG = False

NUM_CLUSTERS = 5
PIXELS_PER_COLOR = 40
OUTPUT_DIR_NAME = "shot_colors"


def main():
	os.chdir(sys.argv[1])
	output_dir = os.path.join(OUTPUT_DIR_NAME, OUTPUT_DIR_NAME)
	try:
		os.mkdir(output_dir)
	except:
		pass
	
	os.chdir(OUTPUT_DIR_NAME)
	for file in os.listdir(os.getcwd()):
		if os.path.isdir(file):
			continue
		
		img_orig = cv.LoadImageM(file)
		w, h = img_orig.cols, img_orig.rows
		
		img_hls = cv.CreateImage((w, h), cv.IPL_DEPTH_8U, 3)
		cv.CvtColor(img_orig, img_hls, cv.CV_BGR2HLS)
		
		output_img = cv.CreateImage((PIXELS_PER_COLOR*NUM_CLUSTERS, h), cv.IPL_DEPTH_8U, 3)
		
		# convert to numpy array
		a = numpy.asarray(cv.GetMat(img_hls))
		a = a.reshape(a.shape[0] * a.shape[1], a.shape[2]) # make it 1-dimensional
		
		# set initial centroids
		init_cluster = []
		step = w / NUM_CLUSTERS
		for x, y in [(0*step, h*0.1), (1*step, h*0.3), (2*step, h*0.5), (3*step, h*0.7), (4*step, h*0.9)]:
			x = int(x)
			y = int(y)
			init_cluster.append(a[y*w + x])
		
		centroids, labels = scipy.cluster.vq.kmeans2(a, numpy.array(init_cluster))
		
		vecs, dist = scipy.cluster.vq.vq(a, centroids) # assign codes
		counts, bins = scipy.histogram(vecs, len(centroids)) # count occurrences
		centroid_count = []
		for i, count in enumerate(counts):
			if count > 0:
				centroid_count.append((centroids[i].tolist(), count))
		
		#centroids = centroids.tolist()
		#centroids.sort(hls_sort)
		
		centroid_count.sort(hls_sort2)
		
		px_count = w * h
		x = 0
		for item in centroid_count:
			count = item[1] * (PIXELS_PER_COLOR*NUM_CLUSTERS)
			count = int(math.ceil(count / float(px_count)))
			centroid = item[0]
			for l in range(count):
				if x+l >= PIXELS_PER_COLOR*NUM_CLUSTERS:
					break
				for y in range(h):
					cv.Set2D(output_img, y, x+l, (centroid[0], centroid[1], centroid[2]))
			x += count
		
		#for centroid_nr, centroid in enumerate(centroids):
		#	for j in range(PIXELS_PER_COLOR):
		#		x = centroid_nr*PIXELS_PER_COLOR + j
		#		for y in range(h):
		#			cv.Set2D(output_img, y, x, (centroid[0], centroid[1], centroid[2]))
		
		output_img_rgb = cv.CreateImage(cv.GetSize(output_img), cv.IPL_DEPTH_8U, 3)
		cv.CvtColor(output_img, output_img_rgb, cv.CV_HLS2BGR)
		cv.SaveImage(os.path.join(OUTPUT_DIR_NAME, file), output_img_rgb)
	
	print "appending..."
	os.chdir(OUTPUT_DIR_NAME)
	os.system("convert shot_colors_*.png -append result.png")
	
	#raw_input("- done -")
	return


# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 03_3_movie-colors
# -*- coding: utf-8 -*-
import cv
import os
import os.path
import sys
import numpy
import scipy
import scipy.cluster
import math

#from lib import hls_sort


from colormath.color_objects import HSLColor, RGBColor
def difference(a, b): # HLS
	print a, b
	#c1 = HSLColor(hsl_h = a[0], hsl_s = a[2]/100.0, hsl_l = a[1]/100.0)
	#c2 = HSLColor(hsl_h = b[0], hsl_s = a[2]/100.0, hsl_l = a[1]/100.0)
	c1 = RGBColor(a[0], a[1], a[2])
	c2 = RGBColor(b[0], b[1], b[2])
	#c1.convert_to('lab')
	#c2.convert_to('lab')
	print c1.delta_e(c2)
	return c1.delta_e(c2)


#import grapefruit
#def difference(a, b):
#	c1 = grapefruit.Color.NewFromHsl(a[0], a[2], a[1])
#	c2 = grapefruit.Color.NewFromHsl(b[0], b[2], b[1])
#	return 1


def sort_by_distance(colors):
	# Find the darkest color in the list.
	root = colors[0]
	for color in colors[1:]:
		if color[1] < root[1]: # l
			root = color
	
	# Remove the darkest color from the stack,
	# put it in the sorted list as starting element.
	stack = [color for color in colors]
	stack.remove(root)
	sorted = [root]
	
	# Now find the color in the stack closest to that color.
	# Take this color from the stack and add it to the sorted list.
	# Now find the color closest to that color, etc.
	while len(stack) > 1:
		closest, distance = stack[0], difference(stack[0], sorted[-1])
		for clr in stack[1:]:
			d = difference(clr, sorted[-1])
			if d < distance:
				closest, distance = clr, d
		stack.remove(closest)
		sorted.append(closest)
	sorted.append(stack[0])
	
	return sorted


WIDTH = 1000
OUTPUT_DIR_NAME = "shot_colors"


def main():
	project_root_dir = sys.argv[1]
	os.chdir(project_root_dir)
	os.chdir(os.path.join(OUTPUT_DIR_NAME, OUTPUT_DIR_NAME))
	
	output_img = cv.CreateImage((WIDTH, WIDTH), cv.IPL_DEPTH_8U, 3)
	
	print os.system("identify -format \"%k\" result.png")
	print "reducing colors to 10"
	os.system("convert result.png +dither -colors 10 result_quant.png")
	
	img_orig = cv.LoadImageM("result_quant.png")
	output_img = cv.CreateImage((WIDTH, WIDTH), cv.IPL_DEPTH_8U, 3)
	
	img_hls = cv.CreateImage(cv.GetSize(img_orig), cv.IPL_DEPTH_8U, 3)
	cv.CvtColor(img_orig, img_hls, cv.CV_BGR2HLS)
	
	pixels = numpy.asarray(cv.GetMat(img_hls))
	d = {}
	
	print "counting..."
	for line in pixels:
		for px in line:
			if tuple(px) in d:
				d[tuple(px)] += 1
			else:
				d[tuple(px)] = 1
	
	colors = d.keys()
	#print "%d pixels, %d colors" % (img_orig.width*img_orig.height, len(colors))
	
	print "sorting..."
	#colors.sort(hls_sort)
	colors = sort_by_distance(colors)
	
	px_count = img_orig.width * img_orig.height
	x_pos = 0
	
	print "building image..."
	for color in colors:
		l = d[color] / float(px_count)
		l = int(math.ceil( l*WIDTH ))
		
		for x in range(l):
			if x_pos+x >= WIDTH:
					break
			for y in range(WIDTH):
				cv.Set2D(output_img, y, x_pos+x, (int(color[0]), int(color[1]), int(color[2])))
		x_pos += l
	
	print "saving..."
	output_img_rgb = cv.CreateImage(cv.GetSize(output_img), cv.IPL_DEPTH_8U, 3)
	cv.CvtColor(output_img, output_img_rgb, cv.CV_HLS2BGR)
	cv.SaveImage("_RESULT.png", output_img_rgb)
	
	os.chdir( r"..\.." )
	f = open("colors.txt", "w")
	row = cv.GetRow(output_img_rgb, 0)
	
	counter = 0
	last_px = cv.Get1D(row, 0)
	for i in range(WIDTH):
		px = cv.Get1D(row, i)
		if px == last_px:
			counter += 1
			if i == WIDTH-1:
				f.write("%d, %d, %d, %d\n" % (int(last_px[2]), int(last_px[1]), int(last_px[0]), counter))
			continue
		else:
			f.write("%d, %d, %d, %d\n" % (int(last_px[2]), int(last_px[1]), int(last_px[0]), counter))
			counter = 1
			last_px = px
	f.close()
	
	return


# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 03_4_adjust-chapters
# -*- coding: utf-8 -*-
import os
import sys
import xml.etree.ElementTree as et


def main():
	os.chdir(sys.argv[1])
	
	tree = et.parse("project.xml")
	
	movie = tree.getroot()
	duration = int( movie.attrib["frames"] )
	start_frame = int( movie.attrib["start_frame"] )
	end_frame = int( movie.attrib["end_frame"] )
	
	f = open("chapters.txt~", "r")
	chapters = [int(frame) for frame in f if frame]
	f.close()
	
	chapters = [ch for ch in chapters if ch < end_frame and ch > start_frame] # get rid of things that are outside of the bounds
	chapters = [start_frame] + chapters
	#chapters[0] = start_frame  # in case we removed some credits from the beginning
	chapters.append(end_frame) # so that we know how long the last chapter is
	
	dur_counter = 0
	for i in range( len(chapters) - 1 ):
		dur_counter += chapters[i+1] - chapters[i]
	
	print duration
	print dur_counter
	
	f_out = open("chapters.txt", "w")
	for ch in chapters:
		f_out.write("%d\n" % (ch))
	f_out.close()
	
	return


# #########################
if __name__ == "__main__":
	main()
# #########################
########NEW FILE########
__FILENAME__ = 03_5_chapter-colors
# -*- coding: utf-8 -*-
import sys
import os
import os.path
import glob
import cv
import math
import numpy
import scipy.cluster
import xml.etree.ElementTree as et

from lib import hls_sort2


OUTPUT_DIR_NAME = "chapters"

NUM_CLUSTERS = 10
PIXELS_PER_COLOR = 40


def main():
	os.chdir(sys.argv[1])
	
	#print "DELETE ALL FILES FIRST!"
	
	#tree = et.parse("project.xml")
	#movie = tree.getroot()
	#start_frame = int( movie.attrib["start_frame"] )
	#end_frame = int( movie.attrib["end_frame"] )
	
	f_shots = open("shots.txt")
	shots = [(int(start), int(end)) for start, end in [line.split("\t")[0:2] for line in f_shots if line]]
	f_shots.close()
	
	f_chapters = open("chapters.txt")
	chapters = [int(line) for line in f_chapters if line]
	f_chapters.close()
	'''# fix first and add last frame
	chapters[0] = start_frame
	chapters.append(end_frame)'''
	
	os.chdir("shot_colors")
	try:
		os.mkdir(OUTPUT_DIR_NAME)
	except:
		pass
	
	filenames = glob.glob("shot_colors_*.png")
	
	last_shot_nr = 0
	ch = 1
	for i, shot in enumerate(shots):
		start_frame, end_frame = shot
		if ch == len(chapters): # will this ever happen, freder?
			print "den rest noch"
			#print " ".join(filenames[last_shot_nr:])
			os.system("convert %s -append chapters\\chapter_%02d.png" % (" ".join(filenames[last_shot_nr:]), ch))
			break
		elif end_frame >= chapters[ch]:
		#if end_frame >= chapters[ch]:
			print ch, ":", last_shot_nr, "->", i-1
			print " ".join(filenames[last_shot_nr:i])
			os.system("convert %s -append chapters\\chapter_%02d.png" % (" ".join(filenames[last_shot_nr:i]), ch))
			last_shot_nr = i
			ch += 1
			
	
	os.chdir(OUTPUT_DIR_NAME)
	
	for file_nr, file in enumerate( os.listdir(os.getcwd()) ):
		if os.path.isdir(file):
			continue
		
		img_orig = cv.LoadImageM(file)
		w, h = img_orig.cols, img_orig.rows
		
		img_hls = cv.CreateImage((w, h), cv.IPL_DEPTH_8U, 3)
		cv.CvtColor(img_orig, img_hls, cv.CV_BGR2HLS)
		
		output_img = cv.CreateImage((PIXELS_PER_COLOR*NUM_CLUSTERS, h), cv.IPL_DEPTH_8U, 3)
		
		# convert to numpy array
		a = numpy.asarray(cv.GetMat(img_hls))
		a = a.reshape(a.shape[0] * a.shape[1], a.shape[2]) # make it 1-dimensional
		
		# set initial centroids
		init_cluster = []
		step = w / NUM_CLUSTERS
		#for x, y in [(0*step, h*0.1), (1*step, h*0.3), (2*step, h*0.5), (3*step, h*0.7), (4*step, h*0.9)]:
		for x, y in [(0*step, h*0.1), (1*step, h*0.1), (2*step, h*0.3), (3*step, h*0.3), (4*step, h*0.5), (5*step, h*0.5), (6*step, h*0.7), (7*step, h*0.7), (8*step, h*0.9), (9*step, h*0.9)]:
			x = int(x)
			y = int(y)
			init_cluster.append(a[y*w + x])
		
		centroids, labels = scipy.cluster.vq.kmeans2(a, numpy.array(init_cluster))
		
		vecs, dist = scipy.cluster.vq.vq(a, centroids) # assign codes
		counts, bins = scipy.histogram(vecs, len(centroids)) # count occurrences
		centroid_count = []
		for i, count in enumerate(counts):
			if count > 0:
				centroid_count.append((centroids[i].tolist(), count))
		
		centroid_count.sort(hls_sort2)
		
		px_count = w * h
		x = 0
		for item in centroid_count:
			count = item[1] * (PIXELS_PER_COLOR*NUM_CLUSTERS)
			count = int(math.ceil(count / float(px_count)))
			centroid = item[0]
			for l in range(count):
				if x+l >= PIXELS_PER_COLOR*NUM_CLUSTERS:
					break
				for y in range(h):
					cv.Set2D(output_img, y, x+l, (centroid[0], centroid[1], centroid[2]))
			x += count
		
		output_img_rgb = cv.CreateImage(cv.GetSize(output_img), cv.IPL_DEPTH_8U, 3)
		cv.CvtColor(output_img, output_img_rgb, cv.CV_HLS2BGR)
		cv.SaveImage(file, output_img_rgb)
		
		# save to text-file
		if file_nr == 0:
			f_out = open("..\\..\\chapter_colors.txt", "w")
			f_out.write("") # reset
			f_out.close()
		
		f_out = open("..\\..\\chapter_colors.txt", "a")
		row = cv.GetRow(output_img_rgb, 0)
		WIDTH = row.cols
		#print WIDTH
		
		data_items = []
		counter = 0
		last_px = cv.Get1D(row, 0)
		for i in range(WIDTH):
			px = cv.Get1D(row, i)
			if px == last_px:
				counter += 1
				if i == WIDTH-1:
					#f_out.write("%d, %d, %d, %d _ " % (int(last_px[2]), int(last_px[1]), int(last_px[0]), counter))
					data_items.append( "%d, %d, %d, %d" % (int(last_px[2]), int(last_px[1]), int(last_px[0]), counter) )
				continue
			else:
				#f_out.write("%d, %d, %d, %d _ " % (int(last_px[2]), int(last_px[1]), int(last_px[0]), counter))
				data_items.append( "%d, %d, %d, %d" % (int(last_px[2]), int(last_px[1]), int(last_px[0]), counter) )
				counter = 1
				last_px = px
		
		print NUM_CLUSTERS - len(data_items), "colors missing"
		for j in range( NUM_CLUSTERS - len(data_items) ): # sometimes there are fewer colors
			data_items.append("0, 0, 0, 0")
		f_out.write( " _ ".join(data_items) )
		f_out.write("\n")
		f_out.close()
	
	os.system("convert chapter_*.png -append _CHAPTERS.png")
	return


# #########################
if __name__ == "__main__":
	main()
# #########################
########NEW FILE########
__FILENAME__ = 04_1_motion
# -*- coding: utf-8 -*-
import cv
import math
import os
import sys
import xml.etree.ElementTree as et
import time

from lib import skip_frames


# TODO
# - last 499


DEBUG = False
MAX_FRAMES = 5000
WIDTH = 500

OUTPUT_DIR_NAME = "motion"


def main():
	os.chdir(sys.argv[1])
	try:
		os.mkdir(OUTPUT_DIR_NAME)
	except OSError:
		pass
	
	tree = et.parse("project.xml")
	
	movie = tree.getroot()
	file_path = movie.attrib["path"]
	
	if DEBUG:
		cv.NamedWindow("win", cv.CV_WINDOW_AUTOSIZE)
		cv.MoveWindow("win", 200, 200)
	
	cap = cv.CreateFileCapture(file_path)
	skip_frames(cap, movie)
	
	pixel_count = None
	prev_img = None
	
	global_frame_counter = 0
	file_counter = 0
	
	w = None
	h = None
	
	output_img = cv.CreateImage((WIDTH, MAX_FRAMES), cv.IPL_DEPTH_8U, 3)
	
	f = open("shots.txt", "r")
	lines = [line for line in f if line] # (start_frame, end_frame, duration)
	f.close()
	
	f_frm = open("motion.txt", "w")
	f_avg = open("motion_shot-avg.txt", "w")
	motion = []
	
	t = time.time()
	
	for nr, line in enumerate(lines):
		print (nr+1), "/", len(lines)
		
		duration = int( line.split("\t")[2] )
		
		for frame_counter in range(duration):
			img = cv.QueryFrame(cap)
			if not img:
				print "error?"
				print nr, frame_counter
				#break
				return
			
			if DEBUG:
				cv.ShowImage("win", img)
			
			global_frame_counter += 1
			
			if nr == 0 and frame_counter == 0: # first shot, first frame
				w = img.width
				h = img.height
				pixel_count = float( img.width * img.height )
				prev_img = cv.CreateImage(cv.GetSize(img), cv.IPL_DEPTH_8U, 3)
				cv.Zero(prev_img)
			
			diff = cv.CreateImage(cv.GetSize(img), cv.IPL_DEPTH_8U, 3)
			cv.AbsDiff(img, prev_img, diff)
			cv.Threshold(diff, diff, 10, 255, cv.CV_THRESH_BINARY)
			d_color = 0
			for i in range(1, 4):
				cv.SetImageCOI(diff, i)
				d_color += cv.CountNonZero(diff) / pixel_count
			d_color = d_color / 3 # 0..1
			#print "%.1f" % (d_color*100), "%"
			
			motion.append(d_color)
			cv.Copy(img, prev_img)
			
			# WRITE TEXT FILE
			f_frm.write("%f\n" % (d_color))
			if frame_counter == duration-1: # last frame of current shot
				motion_value = sum(motion) / len(motion)
				print "average motion:", motion_value
				f_avg.write("%f\t%d\n" % (motion_value, duration))
				motion = []
			
			# WRITE IMAGE
			if frame_counter == 0: # ignore each first frame -- the diff after a hard cut is meaningless
				global_frame_counter -= 1
				continue
			else:
				for i in range(WIDTH):
					value = d_color * 255
					cv.Set2D(output_img, (global_frame_counter-1) % MAX_FRAMES, i, cv.RGB(value, value, value))
			
			if global_frame_counter % MAX_FRAMES == 0:
				cv.SaveImage(OUTPUT_DIR_NAME + "\\motion_%03d.png" % (file_counter), output_img)
				file_counter += 1
			
			if DEBUG:
				if cv.WaitKey(1) == 27:
					break
	
	if global_frame_counter % MAX_FRAMES != 0:
		#cv.SetImageROI(output_img, (0, 0, WIDTH-1, (global_frame_counter % MAX_FRAMES)-1))
		cv.SetImageROI(output_img, (0, 0, WIDTH-1, (global_frame_counter-1) % MAX_FRAMES))
		cv.SaveImage(OUTPUT_DIR_NAME + "\\motion_%03d.png" % (file_counter), output_img)
	
	f_frm.close()
	f_avg.close()
	
	if DEBUG:
		cv.DestroyWindow("win");
	
	print "%.2f min" % ((time.time()-t) / 60)
	#raw_input("- done -")
	return



# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 04_2_sort_motion_spectrum
# -*- coding: utf-8 -*-
import cv
import os
import os.path
import sys


OUTPUT_DIR_NAME = "downsampled"


def main():
	os.chdir(os.path.join(sys.argv[1], "motion"))
	try:
		os.mkdir(OUTPUT_DIR_NAME)
	except OSError:
		pass
	
	#os.system("del klein\\*.png")
	os.system("convert motion_*.png -adaptive-resize 500x500! " + OUTPUT_DIR_NAME + "\\motion_%02d.png")
	
	os.chdir(OUTPUT_DIR_NAME)
	os.system("convert motion_*.png -append result.png")
	
	img = cv.LoadImageM("result.png")
	values = []
	
	for y in range(img.rows):
		value = cv.Get1D( cv.GetRow(img, y), 0)[0]
		values.append(value)
	
	values.sort(reverse=True)
	
	output_img = cv.CreateImage(cv.GetSize(img), cv.IPL_DEPTH_8U, 3)
	for y in range(img.rows):
		for x in range(img.cols):
			cv.Set2D(output_img, y, x, cv.RGB(values[y], values[y], values[y]))
	
	cv.SaveImage("result_sorted.png", output_img)
	
	raw_input("- done -")
	return


# #########################
if __name__ == "__main__":
	main()
# #########################
########NEW FILE########
__FILENAME__ = 05_1_trim-audio
# -*- coding: utf-8 -*-
import sys
import scipy.io.wavfile
import xml.etree.ElementTree as et
import os
import os.path


def main():
	os.chdir(sys.argv[1])
	
	tree = et.parse("project.xml")
	movie = tree.getroot()
	path = movie.attrib["path"]
	path = os.path.dirname(path)
	fps = float( movie.attrib["fps"] )
	start_frame = int( movie.attrib["start_frame"] )
	end_frame = int( movie.attrib["end_frame"] )
	
	os.chdir(path)
	file = os.path.join(path, "audio.wav")
	rate = scipy.io.wavfile.read(file)[0]
	print rate, "hz"
	
	trim_from = int( (start_frame / fps) * rate )
	trim_to   = int( (end_frame / fps) * rate )
	os.system("sox audio.wav audio_trimmed.wav trim %ds %ds" % (trim_from, trim_to))
	#print start_frame, end_frame
	#print trim_from, trim_to


# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 05_2_audio
# -*- coding: utf-8 -*-
import sys
import matplotlib.pyplot as plt
import wave
import scipy.io.wavfile
import numpy
import numpy.fft
import math
import xml.etree.ElementTree as et
import os
import os.path

from lib import smooth


# http://onlamp.com/pub/a/python/2001/01/31/numerically.html?page=1
# http://xoomer.virgilio.it/sam_psy/psych/sound_proc/sound_proc_python.html
# dB:  http://www.dsprelated.com/showmessage/29246/1.php
# RMS: http://www.opamp-electronics.com/tutorials/measurements_of_ac_magnitude_2_01_03.htm
# http://www.audioforums.com/forums/showthread.php?11942-extract-volume-out-of-wave-file&p=54594#post54594


def main():
	os.chdir(sys.argv[1])
	f_out = open("smooth_audio.txt", "w")
	
	tree = et.parse("project.xml")
	movie = tree.getroot()
	path = movie.attrib["path"]
	path = os.path.dirname(path)
	fps = float( movie.attrib["fps"] )
	
	os.chdir(path)
	file = os.path.join(path, "audio_trimmed.wav")
	print file

	f = wave.open(file, "rb")
	bit = f.getsampwidth() * 8
	print bit, "bit" # usually: signed 16 bit [-32768, 32767]
	f.close()

	rate, data = scipy.io.wavfile.read(file)
	print rate, "hz"
	# http://en.wikipedia.org/wiki/Sound_level_meter#Exponentially_averaging_sound_level_meter
	chunk = rate / 8 #25

	#print max(data)
	#print min(data)

	max = numpy.max( numpy.absolute(data) )

	"""fft = numpy.fft.rfft(data, chunk)
	fft = numpy.absolute(fft)
	print fft
	plt.plot(fft)
	plt.show()"""

	data_db = numpy.array([])
	data_rms = numpy.array([])
	for i in range(len(data) / chunk):
		values = numpy.array( data[i*chunk : (i+1)*chunk] )
		
		# normalize [0, 1]
		#values = values / 2**(bit-1)
		values = values / float(max)
		
		#values = values * float(1) # why do I need that?
		
		# root mean square
		values = numpy.power(values, 2)
		rms = numpy.sqrt( numpy.mean(values) )
		data_rms = numpy.append(data_rms, rms)
		
		# decibel
		db = 20 * numpy.log10( (1e-20+rms) ) #/ float(max)
		data_db = numpy.append(data_db, db)

	#plt.ylim(-60, 0)
	
	#plt.plot( smooth(data_rms/numpy.max(data_rms), window_len=rate/(fps*2)), "k-" )
	#plt.plot(smooth(data_db, window_len=rate/fps), "g-")
	
	smooth_db = 1 + smooth(data_db, window_len=rate/(fps*3)) / (60.0) # [0..1]
	plt.ylim(0, 1)
	plt.plot(smooth_db, "g-")
	
	for item in smooth_db:
		if item < 0:
			item = 0
		f_out.write("%f\n" % float(item))
	f_out.close()
	
	
	#plt.plot(data_db)
	
	plt.show()



#for i in range(len(data) / (rate*250)):
#	plt.specgram(data[i*rate*250 : (i+1)*rate*250], Fs = rate, scale_by_freq=True, sides='default')
#	plt.show()
	





"""def show_wave_n_spec(speech):
	spf = wave.open(speech, "r")
	#sound_info = spf.readframes(-1)
	sound_info = spf.readframes(1000000)
	sound_info = numpy.fromstring(sound_info, 'Int16')
	
	f = spf.getframerate()
	
	plt.subplot(211)
	plt.plot(sound_info)
	plt.title('Wave from and spectrogram of %s' % sys.argv[1])
	
	plt.subplot(212)
	spectrogram = plt.specgram(sound_info, Fs = f, scale_by_freq=True, sides='default')
	
	plt.show()
	spf.close()

show_wave_n_spec(fil)"""




"""
f = wave.open(file, "rb")
wav_params = f.getparams()
print wav_params
#sample_rate = wav_params[2]
sample_rate = f.getframerate()

volumes = []
chunk_size = 10 #sample_rate / 25

while True:
	data_string = f.readframes(chunk_size)
	unpacked = struct.unpack("%dB" % len(data_string), data_string)
	
	if not unpacked:
		break
	
	chunk = numpy.array(unpacked)
	#print chunk
	chunk = pow(abs(chunk), 2)
	rms = math.sqrt(chunk.mean())
	#print rms
	#db = 10 * math.log10(1e-20 + rms)
	#print db
	
	volumes.append(rms)

#plt.plot(volumes)
plt.specgram(volumes)
plt.show()
f.close()"""




"""
values = []
for i in range(len(data) / chunk):
	x = 
	db = 20 * numpy.log10(1e-20 + numpy.absolute(x))
	mean = numpy.mean(db)
	values.append(mean)

values = numpy.array(values)
smooth_values = smooth(values, window_len=rate/5)
smooth_values2 = smooth(values, window_len=rate/10)

plt.ylim(-100, 100)
plt.plot(smooth_values)
plt.plot(smooth_values2, "r-")
plt.show()
"""





"""import numpy.fft
spectrum = numpy.fft.fft(data[:10000])
frequencies = numpy.fft.fftfreq(len(data[:10000]))
plt.plot(frequencies,spectrum)
plt.show()"""


# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 06_1_plot_statistics
# -*- coding: utf-8 -*-
import sys
import os
import xml.etree.ElementTree as et
import matplotlib.pyplot as plt
import math
import numpy

from lib import smooth


OUTPUT_DIR_NAME = "plots"


def main():
	os.chdir(sys.argv[1])
	try:
		os.mkdir(OUTPUT_DIR_NAME)
	except OSError:
		pass
	
	tree = et.parse("project.xml")
	
	movie = tree.getroot()
	fps = float( movie.attrib["fps"] )
	frames = float( movie.attrib["frames"] )
	
	os.chdir(OUTPUT_DIR_NAME)
	
	s = frames / fps
	m = s / 60.0
	print s, "seconds"
	h = s / float(60*60)
	print "%.2f hours" % h
	percent = h / 2.0
	print "%.2f %%" % percent
	print "%d:%02d" % (math.floor(h), (h-math.floor(h))*60)
	
	# ===== DURATION ==================================================================================================
	plt.axis(ymin=0, ymax=10, xmin=0, xmax=3*60)
	plt.xlabel("%d mins, %.2f %% of 2 hours" % (s / 60, percent))
	
	lw = 20
	plt.plot([0, 2*60], [1, 1], "k-", linewidth=lw, solid_capstyle="butt")
	plt.plot([0, h*60], [2, 2], "b-", linewidth=lw, solid_capstyle="butt")
	
	r = 200 / 2
	r2 = math.sqrt( percent * r*r )
	plt.plot([100], [6], "o", markeredgewidth=0, markersize=2*r2, markerfacecolor="b")
	plt.plot([100], [6], "o", markeredgewidth=1, markersize=2*r, markerfacecolor="none")
	
	plt.axis("off")
	plt.show()
	#plt.savefig(os.path.join(OUTPUT_DIR_NAME, "duration.ps"))
	
	# ===== SHOTS ==================================================================================================
	f = open("..\\shots.txt", "r")
	values = [[int(values[0]), int(values[1]), int(values[2])] for values in [line.split("\t") for line in f if line]]
	f.close()
	
	fig = plt.figure()
	ax = fig.add_subplot(111)
	plt.ylim(ymin=5, ymax=15.5)
	#ax.set_yscale("log")
	for i, item in enumerate(values):
		#print item
		frame_start, frame_end, length = item
		y = 10
		if i % 2 == 0:
			color = (0, 0, 0)
		else:
			color = (0.5, 0.5, 0.5)
			y = 10.5
		#ax.hlines(length/100.0, frame_start, frame_end, color=color, lw=100)
		ax.hlines(y, frame_start, frame_end, color=color, lw=30)
	
	ax.axis("off")
	plt.show()
	
	# ===== TRENDLINES ==================================================================================================
	f = open("..\\motion_shot-avg.txt", "r")
	values = [[float(values[0]), int(values[1])] for values in [line.split("\t") for line in f if line]]
	f.close()
	
	motions, durations = ([a for a, b in values], [b for a, b in values])
	durations_sec = [float(d/fps) for d in durations]
	
	print len(durations), "shots"
	print "%.1f cuts per minute" % (len(durations)/m)
	print "min:", min(durations_sec), "s"
	print "max:", max(durations_sec), "s"
	print "range:", max(durations_sec)-min(durations_sec), "s"
	print "asl:", numpy.mean(durations_sec), "s"
	print "std:", numpy.std(durations_sec), "s"
	print "var:", numpy.var(durations_sec), "s"
	
	file = open("..\\subtitles.txt")
	s = file.read()
	file.close()
	word_count = len( s.split() )
	words_per_minute = word_count / m
	print words_per_minute, "words / minute"
	
	WINDOW_LEN = 20
	TREND_DEGREE = 1 # polynom 1ten grades
	
	data = numpy.array(WINDOW_LEN*[durations_sec[0]] + durations_sec + WINDOW_LEN*[0])
	trend_duration = numpy.polyfit(range(len(data)), data, TREND_DEGREE)
	trend_duration = numpy.poly1d(trend_duration)
	smooth_data = smooth( data, window_len=WINDOW_LEN, window='hanning' )
	plt.axis(ymin=0, ymax=60.0, xmin=0, xmax=len(durations_sec)-1)
	plt.plot(smooth_data[WINDOW_LEN:-WINDOW_LEN], "r-", label="shot length (in seconds)")
	plt.plot(trend_duration(numpy.arange(len(data))), "m-", label="shot length trend")
	plt.legend(loc="upper left")
	
	data = numpy.array(WINDOW_LEN*[motions[0]] + motions + WINDOW_LEN*[0])
	trend_motion = numpy.polyfit(range(len(data)), data, TREND_DEGREE)
	trend_motion = numpy.poly1d(trend_motion)
	smooth_data = smooth(data, window_len=WINDOW_LEN, window='hanning')
	plt.xlabel("shot / %d" % (len(durations)))
	plt.twinx()
	plt.axis(ymin=0, ymax=1.0)
	plt.plot(smooth_data[WINDOW_LEN:-WINDOW_LEN], "b-", label="motion (0..1)")
	plt.plot(trend_motion(numpy.arange(len(data))), "c-", label="motion trend")
	plt.legend(loc="upper right")
	
	plt.show()
	
	# ===== TEST ==================================================================================================
	if False:
		smooth_duration = 0.5 * smooth_data / numpy.max(smooth_data)
		smooth_deriv = 100 * smooth( numpy.diff( smooth_data ), window_len=10*WINDOW_LEN )[WINDOW_LEN:-WINDOW_LEN]
		smooth_motion = smooth_data[WINDOW_LEN:-WINDOW_LEN]
		
		'''for x, y in enumerate(smooth_deriv):
			m = smooth_motion[x]
			if x % 2 == 0:
				plt.vlines(x, y-m, y+m, lw=m*2)
		
		plt.plot(smooth_deriv, "w-", lw=1)
		mini = min(len(smooth_deriv), len(smooth_motion))
		plt.fill_between(range(mini), smooth_deriv[:mini], smooth_deriv[:mini]+smooth_motion[mini], color="y")
		plt.axis(ymin=-1, ymax=1, xmin=0, xmax=len(durations_sec)-1)
		plt.show()'''
		
		
		# audio
		f = open("..\\smooth_audio.txt", "r")
		values = [float(line) for line in f if line]
		f.close()
		audio_step = float(len(values)) / float(len(smooth_deriv))
		audio_counter = 0
		
		
		fig = plt.figure()
		ax = fig.add_subplot(111, polar=True)
		
		STEP = math.ceil(0.01* len(smooth_deriv) / float(2*math.pi) )
		
		for x, y in enumerate(smooth_deriv):
			if x % STEP == 0:
				x = 2*math.pi * float(x) / len(smooth_deriv)
				y += 2
				audio_value = 0.75 * values[int( audio_counter * audio_step )]
				ax.vlines(x, y+0.01, y+0.01+audio_value, lw=audio_value*2, color="y")
				audio_counter += 1
		
		for x, y in enumerate(smooth_deriv):
			m = smooth_motion[x]
			#d = smooth_duration[x]
			if x % STEP == 0:
				x = 2*math.pi * float(x) / len(smooth_deriv)
				y += 2
				ax.vlines(x, y+0.01, y+0.01+m, lw=m*2)
				
				"""audio_value = 0.75 * values[int( audio_counter * audio_step )]
				ax.vlines(x, y-0.01, y-0.01-audio_value, lw=audio_value*2)
				audio_counter += 1"""
		
		plt.show()
	
	# ===== RADAR ==================================================================================================
	asl = numpy.mean(durations)
	std = numpy.std(durations)
	avg_motion = numpy.mean(motions)
	
	properties = {}
	properties["duration"] = percent
	#properties["average shot length"] = 0.1 * asl / float(fps)
	properties["cuts / minute"] = (len(durations) / m) / 20.0
	properties["average motion"] = avg_motion / 0.25
	properties["words / minute"] = words_per_minute / 60.0
	properties["average loudness"] = 0.5

	angle_step = 360.0 / len(properties)
	angles = []
	for i in range(len(properties)):
		angles.append(math.radians(i*angle_step))
		
	fig = plt.figure()
	ax = fig.add_subplot(111, polar=True)
	ax.set_rmax(5.0)
	ax.set_xticks([i*2*math.pi/len(properties) for i in range(len(properties))])
	ax.set_xticklabels(properties.keys())
	ax.plot(angles, properties.values())
	for i in range(len(properties)):
		ax.vlines(angles[i], 0, properties[properties.keys()[i]], lw=15)
	#ax.axis("off")
	plt.show()
	
	"""
	# ===== COLOR ==================================================================================================
	f = open("colors.txt", "r")
	colors = [[int(values[0]), int(values[1]), int(values[2]), int(values[3])] for values in [line.split(", ") for line in f if line]]
	f.close()
	
	#print colors
	x = numpy.arange(0, 2*math.pi, 2*math.pi/len(colors))
	#print x
	
	y = [values[3] for values in [color for color in colors]]
	#print y
	total = sum(y)
	for i, yps in enumerate(y):
		faktor = float(yps) / total
		y[i] = math.sqrt(faktor * total*total)
	
	fig = plt.figure()
	ax = fig.add_subplot(111, polar=True)
	for i, color in enumerate(colors):
		ax.bar(x[i], y[i], width=0.2*math.pi, edgecolor="none", color=(color[0]/255.0, color[1]/255.0, color[2]/255.0))
	ax.axis("off")
	plt.show()
	"""
	
	#raw_input("- done -")
	return



# #########################
if __name__ == "__main__":
	main()
# #########################

########NEW FILE########
__FILENAME__ = 06_2_subtitle_sentiment
﻿# -*- coding: utf-8 -*-
import nltk.classify.util
from nltk.classify import NaiveBayesClassifier
from nltk.corpus import movie_reviews, stopwords

from nltk.corpus.reader.plaintext import PlaintextCorpusReader
#from nltk.tokenize.regexp import WordTokenizer, WhitespaceTokenizer
#from nltk.tokenize.treebank import TreebankWordTokenizer
import os
import re
import string
import sys
import math


#file = "shining_text-only.txt"
#print file

os.chdir(sys.argv[1])
file = "subtitles.txt"

corpus = PlaintextCorpusReader(os.getcwd(), file) # word_tokenizer=TreebankWordTokenizer()


def evaluate_classifier(featx):
	negids = movie_reviews.fileids('neg')
	posids = movie_reviews.fileids('pos')
	 
	negfeats = [(featx(movie_reviews.words(fileids=[f])), 'neg') for f in negids]
	posfeats = [(featx(movie_reviews.words(fileids=[f])), 'pos') for f in posids]
	 
	trainfeats = negfeats + posfeats
	classifier = NaiveBayesClassifier.train(trainfeats)

	p = 0
	n = 0
	x = 0

	for s in corpus.sents():
		s = [w for w in s] # if w not in stopwords.words("english")
		
		prob = classifier.prob_classify(featx(s))
		
		if prob.prob("pos") > 0.65:
			p += 1
		elif prob.prob("neg") > 0.65:
			n += 1
		else:
			# ignore almost "neutral" ones
			x += 1
			pass

	print "pos:", p, "-- neg:", n, "-- ignored:", x
	if n > p:
		print "1 :", n/float(p)
		print math.degrees( math.atan( 0.5 * n/float(p) ) ), "°" # steigungswinkel
		                                                   # negativ fällt, positiv steigt
	if p > n:
		print p/float(n), ": 1"
		print "-", math.degrees( math.atan( 0.5 * p/float(p) ) ), "°"


def word_feats(words):
	return dict([(word, True) for word in words])

#evaluate_classifier(word_feats)


import itertools
from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures
 
def bigram_word_feats(words, score_fn=BigramAssocMeasures.chi_sq, n=200):
	bigram_finder = BigramCollocationFinder.from_words(words)
	bigrams = bigram_finder.nbest(score_fn, n)
	return dict([(ngram, True) for ngram in itertools.chain(words, bigrams)])
 
#evaluate_classifier(bigram_word_feats)

# #################################################################
from nltk.probability import FreqDist, ConditionalFreqDist

word_fd = FreqDist()
label_word_fd = ConditionalFreqDist()

for word in movie_reviews.words(categories=['pos']):
	word_fd.inc(word.lower())
	label_word_fd['pos'].inc(word.lower())

for word in movie_reviews.words(categories=['neg']):
	word_fd.inc(word.lower())
	label_word_fd['neg'].inc(word.lower())

# n_ii = label_word_fd[label][word]
# n_ix = word_fd[word]
# n_xi = label_word_fd[label].N()
# n_xx = label_word_fd.N()

pos_word_count = label_word_fd['pos'].N()
neg_word_count = label_word_fd['neg'].N()
total_word_count = pos_word_count + neg_word_count

word_scores = {}

for word, freq in word_fd.iteritems():
	pos_score = BigramAssocMeasures.chi_sq(label_word_fd['pos'][word], (freq, pos_word_count), total_word_count)
	neg_score = BigramAssocMeasures.chi_sq(label_word_fd['neg'][word], (freq, neg_word_count), total_word_count)
	word_scores[word] = pos_score + neg_score

best = sorted(word_scores.iteritems(), key=lambda (w,s): s, reverse=True)[:10000]
bestwords = set([w for w, s in best])

def best_word_feats(words):
	return dict([(word, True) for word in words if word in bestwords])

#evaluate_classifier(best_word_feats)


def best_bigram_word_feats(words, score_fn=BigramAssocMeasures.chi_sq, n=200):
	bigram_finder = BigramCollocationFinder.from_words(words)
	bigrams = bigram_finder.nbest(score_fn, n)
	d = dict([(bigram, True) for bigram in bigrams])
	d.update(best_word_feats(words))
	return d

#print 'evaluating best words + bigram chi_sq word features'
evaluate_classifier(best_bigram_word_feats)
########NEW FILE########
__FILENAME__ = lib
import cv
def skip_frames(cap, movie):
	cv.QueryFrame(cap) # why exactly do I need to skip the first one?
	
	# skip frames in the beginning (credits, etc), if neccessary
	start_frame = int( movie.attrib["start_frame"] )
	start_frame -= 1
	print "skipping", start_frame, "frames"
	for i in range(start_frame):
		cv.QueryFrame(cap)


import numpy
def smooth(x, window_len=11, window='hanning'):
	"""smooth the data using a window with requested size.

	This method is based on the convolution of a scaled window with the signal.
	The signal is prepared by introducing reflected copies of the signal 
	(with the window size) in both ends so that transient parts are minimized
	in the begining and end part of the output signal.
	
	input:
		x: the input signal 
		window_len: the dimension of the smoothing window; should be an odd integer
		window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
			flat window will produce a moving average smoothing.
	
	output:
		the smoothed signal
	
	example:
	
	t=linspace(-2,2,0.1)
	x=sin(t)+randn(len(t))*0.1
	y=smooth(x)
	
	see also: 
	
	numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
	scipy.signal.lfilter
	
	TODO: the window parameter could be the window itself if an array instead of a string   
	"""
	
	if x.ndim != 1:
		raise ValueError, "smooth only accepts 1 dimension arrays."
	
	if x.size < window_len:
		raise ValueError, "Input vector needs to be bigger than window size."
	
	if window_len < 3:
		return x
	
	if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
		raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"
	
	s = numpy.r_[2*x[0]-x[window_len-1::-1],x,2*x[-1]-x[-1:-window_len:-1]]
	
	if window == 'flat': #moving average
		w = numpy.ones(window_len,'d')
	else:
		w = eval('numpy.'+window+'(window_len)')
	
	y = numpy.convolve(w/w.sum(), s, mode='same')
	return y[window_len:-window_len+1]


def hls_sort2(a, b):
	a = a[0]
	b = b[0]
	
	if a[1] > b[1]: # L
		return 1
	elif a[1] < b[1]:
		return -1
	else:
		if a[0] > b[0]: # H
			return 1
		elif a[0] < b[0]:
			return -1
		else:
			if a[2] > b[2]: # S
				return 1
			elif a[2] < b[2]:
				return -1
			else:
				return 0
	



"""def hls_sort(a, b): # HLS
	if a[1] > b[1]: # L
		return 1
	elif a[1] < b[1]:
		return -1
	else:
		if a[0] > b[0]: # H
			return 1
		elif a[0] < b[0]:
			return -1
		else:
			if a[2] > b[2]: # S
				return 1
			elif a[2] < b[2]:
				return -1
			else:
				return 0


def hsv_sort(a, b): # HSV
	if a[2] > b[2]: # V
		return 1
	elif a[2] < b[2]:
		return -1
	else:
		if a[0] > b[0]: # H
			return 1
		elif a[0] < b[0]:
			return -1
		else:
			if a[1] > b[1]: # S
				return 1
			elif a[1] < b[1]:
				return -1
			else:
				return 0"""

import math
def timecode_to_seconds(tc):
	# 00:12:34,567
	h = int(tc[0:2])
	m = int(tc[3:5])
	s = int(tc[6:8])
	milli = int(tc[-3:])
	return (milli/1000.0) + s + (m*60) + (h*60*60)


def seconds_to_timecode(s):
	h = int(math.floor(float(s) / (60*60)))
	m = int(math.floor(float(s) % (60*60)) / 60)	
	s = s - (m*60) - (h*60*60)
	
	if h > 10:
		h = str(h)
	else:
		h = "0" + str(h)
	
	if m > 10:
		m = str(m)
	else:
		m = "0" + str(m)
	
	if s > 10:
		s = str(s)
	else:
		s = "0" + str(s)
		
	s = s.replace('.', ',')[:6]
	s = s + (6 - len(s)) * "0"
	
	return h + ":" + m + ":" + s
########NEW FILE########
