#! /usr/bin/env python

#
# LICENSE:
# Copyright (C) 2016  Neal Patwari
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Neal Patwari, neal.patwari@gmail.comimport lib.rti as rti
import matplotlib
matplotlib.use("TkAgg") # set tinker as GUI

import sys
import numpy as np
import matplotlib.pyplot as plt
import lib.rti as rti

# Parameters you may change:
#   plotSkip:  Refresh the plot after this many data lines are read
#   buffL:     buffer length, ie, how much recent data to save for each link.
#   startSkip: A serial port seems to have a "memory" of several lines,
#              which were saved from the previous experiment run.
#              ** Must be greater than 0.
plotSkip      = 5
startSkip     = 1
buffL         = 4
calLines      = 50
topChs        = 1  # How many channels to include in multichannel RTI
channels      = 1  # How many channels are measured on each TX,RX combination.
delta_p       = 0.2  # distance units from coordFileName
sigmax2       = 0.5  # image value^2
delta         = 1.0  # distance units from coordFileName
excessPathLen = 0.1 # distance units from coordFileName
units         = 'm' # distance units for plot label
interpolation = 'gaussian' # interpolation methods for imshow
show_plot     = False # if show rssi line diagramm
rss_history   = 15 # how many history records ar stored

# An image max value above this makes us believe someone is in the area.
personInAreaThreshold = 2.1

# Load the coordinate file, find the bottom left and top right
coordFileName = 'log/coords.txt'
sensorCoords  = np.loadtxt(coordFileName)
sensors       = len(sensorCoords)

# It looks nice to have the sensor coordinates plotted on top of any image.
plt.ion()

# initialize the RTI projection matrix, create a rectangular grid of pixels.
inversion, xVals, yVals = rti.initRTI(sensorCoords, delta_p, sigmax2, delta, excessPathLen)
imageExtent   = (0, sensorCoords[:,0].max(),
                 0, sensorCoords[:,1].max())  # the min, max for plot axes
xValsLen      = len(xVals)  # how many pixels along the x-axis.
yValsLen      = len(yVals)  # how many pixels along the y-axis.

# Open the file in argv[1]; if none, use stdin as the file
if len(sys.argv) == 1:
    infile = sys.stdin
    fromStdin = True
else:
    infile = open(sys.argv[1])
    fromStdin = False



# remove junk from start of file.
for i in range(startSkip):
    line = infile.readline()

# Use the most recent line to determine how many columns (streams) there are.
# The first line is used as the "prevRSS" when reading the following lines.
lineList = [int(i) for i in line.split()]
time_ms  = lineList.pop()  # takes time in ms from the last column.
prevRSS  = np.array(lineList)
numLinks = len(prevRSS)
numPairs = sensors*(sensors-1)
if numLinks != numPairs*channels:
    sys.exit('Error: numLinks = ' + str(numLinks) +
        '; sensors = ' + str(sensors) + '; channels = ' + str(channels))



# Initialize RSS Buffer, a list of buffers, one for each link.
# For VRTI.
buff = []
for i in range(numLinks):
    buff.append( rti.FixedLenBuffer([0]*buffL))

# Run forever, adding lines as they are available.
counter        = 0
actualCoord    = []
VRTI_err_list  = []
RTI_err_list   = []
sumRSS         = np.zeros(numLinks)
countCalLines  = np.zeros(numLinks)
keepReading    = True
y_data         = None

while keepReading:
    print "Counter = " + str(counter)
    line = infile.readline()
    # If at the "end of file", keep reading if reading from stdin.
    if not line or len(line) < (numPairs * 4 + 5):
        keepReading = fromStdin
        continue

    # Get the integers from the line string
    lineList    = [int(i) for i in line.split()]
    time_ms     = lineList.pop(-1)  # remove last element
    rss         = np.array(lineList)

    # data > -10 means no data measured. Replace with most recently measured value.
    for i in range(numLinks):
        if (rss[i] > -10):
            rss[i] = prevRSS[i]

        # Store current RSS vector for each link in its FixedLenBuffer
        # For variance-based RTI.
        buff[i].append(rss[i])

    # Use first "calLines" data vectors to find average RSS
    if counter < calLines:
        for i in range(numLinks):
            if rss[i] < -10:
                sumRSS[i] += rss[i]
                countCalLines[i] += 1

    # At the end of the calLines period, compute the average RSS for each link.
    elif counter == calLines:
        #meanRSS = sumRSS / countCalLines
        # If you have a divide-by-zero problem with the line above, use:
        meanRSS = np.array([s / max(1,countCalLines[i]) for i,s in enumerate(sumRSS)])
        # Sort the meanRSS to decide which channels have the highest average RSS.
        # Make each channel's RSS vector into a separate row
        meanRSS.shape = (channels, numPairs)
        maxInds = meanRSS.transpose().argsort()
        # Sum the highest topChs channels.
        calVec  = rti.sumTopRows(meanRSS, maxInds, topChs)

    # When the calibration period is over, calc & display RT images, and write
    # the current coordinate estimate to the output file.
    if counter >= calLines:

        print "RSS on link 1 = " + str(rss[0])

        if show_plot:
            plt.figure(2)
            if counter == calLines:

                for i in range(numPairs):
                    y_data = np.append([rss], [prevRSS], axis=0)
                    plot_lines, = plt.plot(y_data[:,i], linewidth=0.5)
            else:
                ax = plt.gca()
                ax.lines = []

                if len(y_data) > rss_history:
                    y_data = np.delete(y_data, -1, axis=0)

                y_data = np.append([rss], y_data, axis=0)

                x_data = np.arange(len(y_data))
                for i in range(numPairs):
                    plt.plot(x_data, y_data[:,i], linewidth=0.8)

            plt.xticks(np.arange(rss_history + 1))

        # Compute difference between calVec and current RSS measurement
        rss.shape    = (channels, numPairs)
        curVec       = rti.sumTopRows(rss, maxInds, topChs)
        rss.shape    = numLinks
        scoreVec     = calVec - curVec

        # Compute shadowing-based radio tomographic image
        image        = rti.callRTI(scoreVec, inversion, len(xVals), len(yVals))
        RTIMaxCoord  = rti.imageMaxCoord(image, xVals, yVals)


        # Plot the RTI image each plotSkip data lines.
        if counter % plotSkip == 0:
            rti.plotImage(image, 1, sensorCoords, imageExtent, 8.0, units, time_ms, interpolation=interpolation)
            # You must call colorbar() only once, otherwise you get multiple bars.
            if counter==calLines:
                plt.colorbar()

        # Pause to allow the GUI framework to redraw the screen (required for certain backends)
        # http://stackoverflow.com/a/12826273/2898712
        plt.pause(0.0001)

    # Save RSS in case next line has missing data.
    prevRSS = rss.copy()
    counter += 1
