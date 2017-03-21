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
# Author: Neal Patwari, neal.patwari@gmail.com
#
# Version History:
#
# Version 1.0:  Initial Release.  27 Oct 2014.
#

import sys
import matplotlib
import numpy as np
import scipy.spatial.distance as dist
import numpy.linalg as linalg
import matplotlib.pyplot as plt
import matplotlib.style  as style

matplotlib.rc('xtick', labelsize=10) 
matplotlib.rc('ytick', labelsize=10) 

style.use('ggplot') # fancy style

# ########################################
# Code to provide a fixed-length buffer data type
class FixedLenBuffer:
    def __init__(self, initlist):
        self.frontInd = 0
        self.data     = initlist
        self.len      = len(initlist)

    def list(self):
        oldest = self.frontInd+1
        return self.data[oldest:] + self.data[:oldest]

    # Append also deletes the oldest item
    def append(self, newItem):
        self.frontInd += 1
        if self.frontInd >= self.len:
            self.frontInd = 0
        self.data[self.frontInd] = newItem

    # Returns the "front" item
    def mostRecent(self):
        return self.data[self.frontInd]
 
    # Returns the N items most recently appended
    def mostRecentN(self,N):
        return [self.data[(self.frontInd-i)%self.len] for i in range(N-1,-1,-1)]
    
    # Returns the variance of the data
    def var(self):
        return np.var(self.data)    
# ########################################

# Convert link number to Tx and Rx numbers
def txRxForLinkNum(linknum, nodes):
    tx    = linknum / (nodes-1)
    rx    = linknum % (nodes-1)
    if (rx >= tx): 
        rx+=1
    if (tx >= nodes):
        sys.exit("Error in txRxForLinkNum: linknum too high for nodes value")
    return (tx, rx)

def calcGridPixelCoords(personLL, personUR, delta_p):

    xVals  = np.arange(personLL[0], personUR[0], delta_p)
    yVals  = np.arange(personLL[1], personUR[1], delta_p)
    cols   = len(xVals)
    pixels = cols * len(yVals)  # len(yVals) is the number of rows of pixels

    # fill the first row, then the 2nd row, etc.
    pixelCoords = np.array([[xVals[i%cols], yVals[i/cols]] for i in range(pixels)])

    return pixelCoords, xVals, yVals

# Plot the node/sensor locations with their node numbers
def plotLocs(nodeLocs):

    plt.plot(nodeLocs[:,0], nodeLocs[:,1], '.', markersize=14.0)

    #Increase the axes to show full map.
    xmin, xmax, ymin, ymax = plt.axis()
    deltay          = ymax-ymin
    epsy            = deltay*0.1
    deltax          = xmax-xmin
    epsx            = deltax*0.1
    plt.axis((xmin-epsx, xmax+epsx, ymin-epsy, ymax+epsy))
    for number, coord in enumerate(nodeLocs):
        plt.text(coord[0], coord[1]+ epsy*0.2, str(number+1), # +1 to start node numbers at 1 instead of 0
             horizontalalignment='center', verticalalignment='bottom', fontsize=12)
    plt.xlabel('X Coordinate (m)', fontsize=12)
    plt.ylabel('Y Coordinate (m)', fontsize=12)
    plt.grid()

# Plot the estimated image.  Label the X axis with the actual time (ms), and
# mark the true coordinate with an X if it is known, and mark the sensor coordinates.
def plotImage(image, figNumber, sensorCoords, imageExtent, vmaxval, units, time_ms=None, actualCoord=None, interpolation='none'):
    
    # Replace the image already in Figure figNumber
    plt.figure(figNumber)
    plt.cla()
    plotLocs(sensorCoords)
    imhandle = plt.imshow(image, interpolation=interpolation, origin='lower', extent=imageExtent, vmin=0, vmax=vmaxval)
    plt.ylabel('Y Coordinate (' + units + ')')
    if time_ms == None:
        plt.xlabel('X Coordinate (' + units + ')')
    else:
        plt.xlabel('X Coordinate (' + units + ') at time ' + str(time_ms))
    if (actualCoord != None):
        if (len(actualCoord) > 0):
            plt.text(actualCoord[0], actualCoord[1],'X', horizontalalignment='center', verticalalignment='center')
    # plt.draw()



#  Do initial calculations to compute the RTI projection matrix
#
#  Inputs: nodeLocs:   Sensor node locations (nodes x 2)
#      delta_p:        distance between pixel centers (meters)
#      sigmax2:        variance of any pixel's image value (units^2)
#      delta:          correlation distance (distance at which correlation coefficient is e^-1, meters)
#      excessPathLen:  the size of the ellipse (meters)
#
#  Outputs:
#      inversion:     a pixels x links projection matrix
#      xVals, yVals:  x and y coordinates of pixel grid.
#
#  Author: Neal Patwari, 12 July 2012
#
def initRTI(nodeLocs, delta_p, sigmax2, delta, excessPathLen):

    # Set up pixel locations as a grid.
    personLL        = nodeLocs.min(axis=0)
    personUR        = nodeLocs.max(axis=0)
    pixelCoords, xVals, yVals = calcGridPixelCoords(personLL, personUR, delta_p)
    pixels          = pixelCoords.shape[0]
    #plt.figure(3)
    #plotLocs(pixelCoords)
    

    # Find distances between pixels and transceivers
    DistPixels  = dist.squareform(dist.pdist(pixelCoords))
    DistPixelAndNode = dist.cdist(pixelCoords, nodeLocs)
    DistNodes   = dist.squareform(dist.pdist(nodeLocs))

    # Find the (inverse of) the Covariance matrix between pixels
    CovPixelsInv       = linalg.inv(sigmax2*np.exp(-DistPixels/delta))

    # Calculate weight matrix for each link.
    nodes = len(nodeLocs)
    links = nodes*(nodes-1)
    W = np.zeros((links, pixels))
    for ln in range(links):
        txNum, rxNum  = txRxForLinkNum(ln, nodes)
        ePL           = DistPixelAndNode[:,txNum] + DistPixelAndNode[:,rxNum] - DistNodes[txNum,rxNum]  
        inEllipseInd  = np.argwhere(ePL < excessPathLen)
        pixelsIn      = len(inEllipseInd)
        if pixelsIn > 0:
            W[ln, inEllipseInd] = 1.0 / float(pixelsIn)

    # Compute the projection matrix
    inversion       = np.dot(linalg.inv(np.dot(W.T, W) + CovPixelsInv), W.T)

    return (inversion, xVals, yVals)

def callRTI(linkMeas, inversion, xValsLen, yValsLen):

    temp = np.dot(inversion, linkMeas)
    temp.resize(yValsLen, xValsLen)
    return temp

def imageMaxCoord(imageMat, xVals, yVals):
    
    rowMaxInd, colMaxInd = np.unravel_index(imageMat.argmax(), imageMat.shape)
    return (xVals[colMaxInd], yVals[rowMaxInd])

# Sum the numbers in each column of the matrix data which have the highest values.
# Assume that, in row i, the last column of maxInds contains the index of the row in data 
# which has the highest value in column i.  The 2nd last column in maxInds contains the index of the row in data 
# which has the 2nd highest value in column i.  Etc.
# Assume that topChs <= channels.
def sumTopRows(data, maxInds, topChs):
    
    channels, cols = data.shape
    outVec = np.zeros(cols)
    for i in range(cols):
        for j in range(topChs):
            outVec[i] += data[maxInds[i,channels-1-j],i]
    return outVec


