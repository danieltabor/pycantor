#!/usr/bin/env python3
## Copyright (c) 2022 Daniel Tabor
##
## Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions
## are met:
## 1. Redistributions of source code must retain the above copyright
##    notice, this list of conditions and the following disclaimer.
## 2. Redistributions in binary form must reproduce the above copyright
##    notice, this list of conditions and the following disclaimer in the
##    documentation and/or other materials provided with the distribution.
##
## THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS "AS IS" AND
## ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
## IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
## ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
## FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
## DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
## OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
## HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
## LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
## OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
## SUCH DAMAGE.
##
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import sys
import os
import time

CACHE_THRESH = 1024*1024*10

class Cantor(QWidget):
	def __init__(self,fp,max_rgb=(0,255,0),cache=CACHE_THRESH,*args,**kwargs):
		QWidget.__init__(self,*args,**kwargs)
		self.setMinimumSize(QSize(256,256))
		self._fp = fp
		self._scale_rgb = [ float(max_c)/float(255) for max_c in max_rgb ]
		self._max_rgb   = [ max( int(max_c), 255 )  for max_c in max_rgb ]
		self._data = None
		self._fp.seek(0,2)
		self._fpsize = self._fp.tell()
		self._fp.seek(0,0)
		
		if cache == True or self._fpsize < CACHE_THRESH:
			self._data = fp.read()
			self._fp.seek(0,0)
		else:
			self._data = None
		
		self._offset = 0
		self._brightness = 10
		self._plotsize = min(self.maxPlotSize(),25*1024)
			
	def setOffset(self,offset):
		max_offset = self.maxOffset()
		if offset > max_offset:
			offset = max_offset
		if offset != self._offset:
			self._offset = offset
			self.update()
		
	def offset(self):
		return self._offset
	
	def maxOffset(self):
		return self._fpsize-self._plotsize-1
		
	def setPlotSize(self,plotsize):
		if plotsize < 1:
			plotsize = 1
		max_plotsize = self.maxPlotSize()
		if plotsize > max_plotsize:
			plotsize = max_plotsize
		if plotsize != self._plotsize:
			self._plotsize = plotsize
			max_offset = self.maxOffset()
			if self._offset > max_offset:
				self._offset = max_offset
			self.update()
			
	def plotSize(self):
		return self._plotsize

	def maxPlotSize(self):
		return self._fpsize-1
	
	def setBrightness(self,brightness):
		if brightness < 1:
			brightness = 1
		if brightness > self.maxBrightness():
			brightness = self.maxBrightness()
		if brightness != self._brightness:
			self._brightness = brightness
			self.update()

	def brightness(self):
		return self._brightness

	def maxBrightness(self):
		return 256
	
	def _get_img(self):
		if self._data == None: #File wasn't precached
			self._fp.seek(self._offset,0)
			data = self._fp.read(self._plotsize+1)
			offset = 0
		else: #File is completely in self._data
			data = self._data
			offset = self._offset
			
		imgdata = [0 for i in range(256*256)]	
		for i in range(self._plotsize):
			coord = data[offset+i]*256+data[offset+i+1]
			imgdata[coord] = imgdata[coord] + 1
			
		qimgdata = []
		for d in imgdata:
			r = min( self._max_rgb[0], int(self._scale_rgb[0] * d*self._brightness) )
			g = min( self._max_rgb[1], int(self._scale_rgb[1] * d*self._brightness) )
			b = min( self._max_rgb[2], int(self._scale_rgb[2] * d*self._brightness) )
			qimgdata.extend( [b,g,r,0xFF] ) #This order is incorrect, but somethign is wrong with QImage
		img = QImage(bytes(qimgdata),256,256,4*256,QImage.Format_RGB32)
		return img

	def paintEvent(self,*args,**kwargs):
		img = self._get_img()
		painter = QPainter(self)
		painter.drawImage(QRect(0,0,self.width(),self.height()),img)
		painter.end()


	def snapshot(self,path):
		img = self._get_img()
		img.save(path)

			

class CantorControls(QWidget):
	def __init__(self,fp,max_rgb=(0,255,0),*args,**kwargs):
		QWidget.__init__(self,*args,**kwargs)
		
		self.cantor = Cantor(fp,max_rgb,self)
		
		layout = QGridLayout(self)
		self.setLayout(layout)
		
		snapshot = QPushButton("Snapshot")
		snapshot.clicked.connect(self.onSnapshot)
		layout.addWidget(snapshot,0,0)
		layout.addWidget(QLabel("off"),0,1)
		layout.addWidget(QLabel("len"),0,2)
		layout.addWidget(QLabel("bri"),0,3)
		
		self.scale = 1
		while self.cantor.maxPlotSize()*self.scale > 2147483647:
			self.scale = self.scale - 0.001
			
		self.offset = QScrollBar(self)
		self.offset.setOrientation(Qt.Vertical)
		self.offset.setMinimum(0)
		self.offset.setMaximum(int(self.cantor.maxOffset()*self.scale))
		self.offset.setValue(int(self.cantor.offset()*self.scale))
		self.offset.valueChanged.connect(self.onChangeOffset)

		self.plotsize = QScrollBar(self)
		self.plotsize.setOrientation(Qt.Vertical)
		self.plotsize.setMinimum(1)
		self.plotsize.setMaximum(int(self.cantor.maxPlotSize()*self.scale))
		self.plotsize.setInvertedAppearance(True) 
		self.plotsize.setValue(int(self.cantor.plotSize()*self.scale))
		self.plotsize.valueChanged.connect(self.onChangePlotSize)

		self.brightness = QScrollBar(self)
		self.brightness.setOrientation(Qt.Vertical)
		self.brightness.setMinimum(1)
		self.brightness.setMaximum(self.cantor.maxBrightness())
		self.brightness.setInvertedAppearance(True)
		self.brightness.setValue(int(self.cantor.brightness()))
		self.brightness.valueChanged.connect(self.onChangeBrightness)
		
		layout.addWidget(self.cantor,1,0)
		layout.addWidget(self.offset,1,1)
		layout.addWidget(self.plotsize,1,2)
		layout.addWidget(self.brightness,1,3)

		self.setWindowTitle(os.path.basename(fp.name))
		
	def onChangeOffset(self,evt):
		self.cantor.setOffset(int(self.offset.value()/self.scale))
		
	def onChangePlotSize(self,evt):
		self.cantor.setPlotSize(int(self.plotsize.value()/self.scale))
		
		self.offset.setMaximum(int(self.cantor.maxOffset()*self.scale))
		self.offset.setValue(int(self.cantor.offset()*self.scale))
			
	def onChangeBrightness(self,evt):
		self.cantor.setBrightness(self.brightness.value())
			
	def onSnapshot(self):
		path,ext = QFileDialog.getSaveFileName(self,"Select Image to Save",".","PNG Files (*.png)")
		if len(path):
			self.cantor.snapshot(path)
		
		
def usage():
	print("Usage:")
	print("%s [-h] [-cRRGGBB] [-r[#]] bin_path" % sys.argv[0])
	print("")
	print(" -c : Set color with red, green, and blue hex values (default 00FF00)")
	print(" -r : Control read cache.  If file is less than # bytes it is cached.")
	print("      If no # is given, then cache is forced. (default is %d)" % CACHE_THRESH)
	print("")
	sys.exit(1)
		
def main():
	path = None
	max_rgb = [0x00,0xFF,0x00]
	cache = CACHE_THRESH
	for arg in sys.argv[1:]:
		if arg == "-h":
			usage()
		elif arg[:2] == "-c":
			if len(arg) != 8:
				usage()
			try:
				max_rgb = [int(arg[2:4],16), int(arg[4:6],16), int(arg[6:8],16)]
			except ValueError:
				usage()
		elif arg[:2] == "-r":
			if len(arg) > 2:
				try:
					cache = int(arg[2:])
				except ValueError:
					usage()
			else:
				cache = True
		else:
			if not os.path.exists(arg):
				usage()
			path = arg
	if path == None:
		usage()
		
	fp = open(path,"rb")
	app = QApplication([sys.argv[0]] + sys.argv[2:])
	main = CantorControls(fp,max_rgb)
	main.show()
	app.exec_()
	
if __name__ == "__main__":
	main()
