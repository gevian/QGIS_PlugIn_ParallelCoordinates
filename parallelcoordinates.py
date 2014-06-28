

from PyQt4 import QtCore  
from PyQt4 import QtGui
import math

class PCFeature(object):
    """This structure is used to hold simple feature information"""
    def __init__(self, id_, isSelected, isVisible, attributeValues, normalizedAttributeValues = None):
        self.id = id_
        self.isSelected = isSelected
        self.isVisible = isVisible
        self.attributeValues = attributeValues                                      # Dictionary holding for each attributeIndex an value
        if normalizedAttributeValues is None: normalizedAttributeValues = dict()     
        

class PCAttribute(object):
    """This absrtact structure is used to hold simple attribute information"""
    def __init__(self, id_, name, isVisible):
        self.id_ = id_
        self.name = name
        self.isVisible = isVisible

class PCNumericalAttribute(PCAttribute):
    """This structure is used to hold simple numerical attribute information"""
    def __init__(self, id_, name, isVisible, minimum = 0.0, maximum = 0.0, unit = "none"):
        PCAttribute.__init__(self, id_, name, isVisible)
        
        self.scale = "numerical"
        self.unit = unit
        self.minimum = minimum
        self.maximum = maximum
        
class PCCategoricalAttribute(PCAttribute):
    """This structure is used to hold simple categorical attribute information"""
    def __init__(self, id_, name, isVisible, uniqueValues = None):
        PCAttribute.__init__(self, id_, name, isVisible)
                
        self.scale = "categorical"
        if uniqueValues is None: uniqueValues = list()
        self.uniqueValues = uniqueValues
        self.numberUniqueValues = len(uniqueValues)
             
class PCDataInterface(object):
    """This abstract class should be subclassed to provide data access to an external data provider"""
    def nextAttribute(self, attribute):
        pass
    
    def nextFeature(self, feature):
        pass
    
    def finished(self):
        pass
    
    def setSelectedFeatureIds(self, idList):
        pass
    
class PCData(object):
    """This struct-like class holds the data used for the creation of the parallel coordinates technique"""
    def __init__(self, dataInterface, pcManager):
        self.pcManager = pcManager
        self.dataInterface = dataInterface
        self.attributeDict = dict()             # holds dictionary of PCAttribute objects with the id as key
        self.featureDict = dict()               # holds dictionary of PCFeature objects with the id as key
        
        self.attributeToPosition = dict()       # Dictionary of attributes and their corresponding positions
        self.positionToAttribute = dict()       # Dictionary of positions and their corresponding attributes
        
    def fetchAllData(self, setProgress):
        self.attributeDict.clear()
        self.featureDict.clear()
        self.attributeToPosition.clear()
        self.positionToAttribute.clear()
        
        if self.dataInterface is None:
            #print "Data interface not set. Aborting."
            return

        setProgress(0)

        # get attribute information
        attribute = PCAttribute(None, None, None)
        while self.dataInterface.nextAttribute(attribute):
            self.attributeDict[attribute.id] = attribute            
            #print "Fetched information on attribute: " + attribute.name
            attribute = PCAttribute(None, None, None) # We need a new attribute for each attribute or else they are all bound to the same object
        #print "Fetched " + str(len(self.attributeDict)) + " attributes."

        setProgress(33)

        #TODO: calculate min and max if not given
        #TODO: determine unique values if not given

        # get feature information
        feature = PCFeature(None, None, None, None, None)
        while self.dataInterface.nextFeature(feature):
            self.featureDict[feature.id] = feature
            feature = PCFeature(None, None, None, None, None)  # Same here as in the attributes loop

        setProgress(66)

        # normalize feature values
        for attributeId, attribute in self.attributeDict.items():
            #print "Normalizing Attribute: " + str(attribute.name)
            #print "Scale of Attribute: " + attribute.scale
            if attribute.scale == "numerical":
                maxValue = attribute.maximum
                minValue = attribute.minimum
                #print self.featureDict.items()
                for id_, feat in self.featureDict.items():
                    #print (feat.attributeValues[attributeId] is None) == False
                    #print str(maxValue != minValue and ((feat.attributeValues[attributeId] is None) == False))
                    normalizedValue = 0.5
                    if maxValue != minValue and ((feat.attributeValues[attributeId] is None) == False): # Prevents division by zero and use of NULL values
                        rawValue = float(feat.attributeValues[attributeId])
                        normalizedValue = (rawValue - minValue) / (maxValue - minValue)
                        #print normalizedValue

                    feat.normalizedAttributeValues[attributeId] = normalizedValue
            elif attribute.scale == "categorical":
                for id_, feat in self.featureDict.items():
                    normalizedValue = 0.5
                    if (feat.attributeValues[attributeId] is None) == False: # TODO: Switched from feat.attributeValues[attributeId].isNull() == False to the present version... revise
                        #print (feat.attributeValues[attributeId] is None) == False
                        #print feat.attributeValues[attributeId]
                        #print attribute.uniqueValues
                        rawValue = str(feat.attributeValues[attributeId])
                        position = attribute.uniqueValues.index(rawValue)
                        normalizedValue = position / float(attribute.numberUniqueValues -1)
                        
                    feat.normalizedAttributeValues[attributeId] = normalizedValue

        setProgress(100)

        # tell the provider that we have finished our actions to give it the opportunity to clean up
        self.dataInterface.finished()
      
    def moveAxes(self, firstPosition, secondPosition):
        if firstPosition == secondPosition: # nothing to change
            return
        
        if (secondPosition % 1) > 0.0: # e.g. is a position between two axes
            # in this case one axis will be moved inbetween to other axes
            # therefore only the axispositions between these two positions need to be readjusted, and, of course, of the axis which changes the position
            newPosition = int(math.ceil(secondPosition)) # e.g. 2.5 becomes 3
            
            if (newPosition < firstPosition):
                # adjust positions of axes between firstPosition and newPosition
                changingAttribute = self.positionToAttribute[firstPosition]
                
                for i in range(firstPosition-1, newPosition-1, -1): # decrease from firstPosition to newPosition with step -1
                    tempAttributeIndex = self.positionToAttribute[i]
                    self.positionToAttribute[i+1] = tempAttributeIndex
                    
                self.positionToAttribute[newPosition] = changingAttribute
                
            elif (newPosition > firstPosition):
                changingAttribute = self.positionToAttribute[firstPosition]
            
                for i in range(firstPosition+1, newPosition, 1): # increase from firstPosition to newPosition with step -1
                    tempAttributeIndex = self.positionToAttribute[i]
                    self.positionToAttribute[i-1] = tempAttributeIndex
                
                self.positionToAttribute[newPosition-1] = changingAttribute
    
            
            
        else: # on both positions are axes that need to be swapped
            attributeFirstPosition = self.positionToAttribute[firstPosition]
            attributeSecondPosition = self.positionToAttribute[secondPosition]
            self.positionToAttribute[firstPosition] = attributeSecondPosition
            self.positionToAttribute[secondPosition] = attributeFirstPosition
            
            
            # Update attributeToPosition
            self.attributeToPosition.clear()
        
        for position, attribute in self.positionToAttribute.items():
            self.attributeToPosition[attribute] = position
    
        # something changed
        self.pcManager.drawParallelCoordinates()
    pass

    def evaluateAttributeVisibility(self):
        #TODO ON MONDAY FUNCTION NOT WORKING PROPERLY
        #TODO function maybe inefficient
        for id_, attribute in self.attributeDict.items():
            if not attribute.isVisible and id_ in self.attributeToPosition:
                del self.attributeToPosition[id_]
            elif attribute.isVisible and id_ not in self.attributeToPosition:                 
                self.attributeToPosition[id_] = len(self.attributeToPosition)
        
        #print "eAV self.attributeToPosition"
        #print self.attributeToPosition
        self.positionToAttribute.clear()
         
        for attribute, position in self.attributeToPosition.items():
            self.positionToAttribute[position] = attribute
        
        #print "eAV self.positionToAttribute"
        #print self.positionToAttribute 
        
        # fill holes
        elementCount = len(self.positionToAttribute)
        newPosition = 0
        for position, attribute in self.positionToAttribute.items():
            #print position
            #print attribute
            del self.positionToAttribute[position]
            self.positionToAttribute[newPosition] = attribute
            newPosition += 1
        
        
        
        #print "eAV self.positionToAttribute"
        #print self.positionToAttribute
        
        #TODO maybe not the pythonic way, have to check this out
        for position, attribute in self.positionToAttribute.items():
            self.attributeToPosition[attribute] = position

        #print "eAV self.attributeToPosition"
        #print self.attributeToPosition
        
        self.pcManager.drawParallelCoordinates()
        pass

class PCManager(object):    
    """This class constructs the Parallel Coordinates technique inside a QGraphicsScene using an instance of PCDataInterface"""
    def __init__(self, parent):
        # Member variables
        self.graphicsScene = QtGui.QGraphicsScene()                             # Holds the graphics scene on which is drawn @UndefinedVariable
        self.graphicsView = PCGraphicsView(self.graphicsScene, parent, self)    # Holds the graphics view in which the grapics scene ist going to be drawn
        self.graphicsView.setVerticalScrollBarPolicy ( QtCore.Qt.ScrollBarAlwaysOff );
        self.data = PCData(None, self)                                          # Instance of class PCDataInterface
        self.axes = list()                                                      # Axes to be drawn
        self.pixmapItem = QtGui.QPixmap()                                       # Pixmap to be created when everything is drawn to speed up things a little bit @UndefinedVariable
        
        self.initialized = False
        
        # Draw settings
        self.threshold_x_begin_px = 100
        self.threshold_y_begin_px = 40
        self.bar_distance_px = 150
        self.thickness_px = 3
        self.axisHeight = 250
        #self.axisHeight = self.graphicsView.height() - 2 * self.threshold_y_begin_px 
        self.y_pos_start_px = self.threshold_y_begin_px
        self.y_pos_end_px = self.axisHeight - self.threshold_y_begin_px
    
        # Selection settings
        self.mouseIsMoving = False
        self.selectionStartX = 0
        self.selectionStartY = 0
        self.mouseCurrentPosX = 0
        self.mouseCurrentPosY = 0
        
    def setDataInterface(self, dataInterface):
        self.data.dataInterface = dataInterface    # Instance of class derived from PCDataInterface
        
    def updateData(self, setProgress):
        self.data.fetchAllData(setProgress)
        
    def removeData(self): # Clean up
        self.data.attributeDict = dict()
        self.data.attributeToPosition = dict()
        self.data.positionToAttribute = dict()
        self.data.featureDict = dict()
        self.graphicsScene.clear()
        pass
        
    def setSelectedFeatures(self, idList):
        for id_, feature in self.data.featureDict.items():
                if (id_ in idList):
                    feature.isSelected = True
                else:
                    feature.isSelected = False
                
        self.drawParallelCoordinates()
    
    def setVisibleFeatures(self, idList):
        for id_, feature in self.data.featureDict.items():
                if (id_ in idList):
                    feature.isVisible = True
                else:
                    feature.isVisible = False
                
        self.drawParallelCoordinates()
    
    def setVisibleAttributes(self, idList): 
        #print idList
        for id_ in self.data.attributeDict:
            isVisible = id_ in idList
            self.data.attributeDict[id_].isVisible = isVisible
                
        self.data.evaluateAttributeVisibility()
    
    def drawParallelCoordinates(self):
        #print "drawing"

        # Recalculate axis height
        #self.axisHeight = self.graphicsView.height() - 2 * self.threshold_y_begin_px
        #self.y_pos_end_px = self.axisHeight - self.threshold_y_begin_px
        
        # Counter number of axes to be drawn
        numberVisibleAttributes = 0         
        for id_ in self.data.attributeDict:
            #print id_
            #print self.data.attributeDict[id_].isVisible
            if self.data.attributeDict[id_].isVisible:
                numberVisibleAttributes += 1
        
        self.graphicsView.matrix().reset()
        self.graphicsScene.clear()
        
        if numberVisibleAttributes < 2:
            #print "Too few attributes to be displayed. Aborting."
            return    
    

        self.createAxes()
        self.createLines()
    
        # This fixes a bug which leads to an image which is too small
        if self.initialized == False:
            self.initialized = True
            pen = QtGui.QPen(QtCore.Qt.white)
            self.graphicsScene.addEllipse(0, 0, 1, 1, pen)    
           
           
        # Approach do draw everything into an image
        image = QtGui.QImage(self.graphicsScene.sceneRect().size().toSize(), QtGui.QImage.Format_ARGB32)
        #print image.width()
        #print image.height()
        image.fill(QtCore.Qt.transparent) # Seems to be needed or else artifacts occur (https://github.com/ariya/phantomjs/issues/11366)
        snapshotPainter = QtGui.QPainter(image)
        snapshotPainter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.graphicsScene.render(snapshotPainter)
        snapshotPainter.end() # I need this for (local?) variables of QImage or else qgis will break
           
        self.graphicsScene.clear()
        #print self.graphicsScene.sceneRect()
           
        snapshot = QtGui.QPixmap.fromImage(image)
           
        self.pixmapItem = self.graphicsScene.addPixmap(snapshot)
    
        
        
        #print self.pixmapItem.boundingRect()
        #pen = QtGui.QPen(QtCore.Qt.red)
        # First Axis
        #self.graphicsScene.addEllipse(self.threshold_x_begin_px, self.y_pos_start_px, 10, 10, pen)
        #self.graphicsScene.addEllipse(self.threshold_x_begin_px, self.y_pos_end_px, 10, 10, pen)
        
        # Second Axis
        #self.graphicsScene.addEllipse(self.threshold_x_begin_px + self.bar_distance_px, self.y_pos_start_px, 10, 10, pen)
        #self.graphicsScene.addEllipse(self.threshold_x_begin_px + self.bar_distance_px, self.y_pos_end_px, 10, 10, pen)
        #image.save("/home/heitzler/_Junk/pixmap.png", "PNG") # For testing
    
    def createAxes(self):
        for attributeId in self.data.attributeToPosition:
            # Calculate axis position
            x_pos_px = self.threshold_x_begin_px + self.bar_distance_px*self.data.attributeToPosition[attributeId]
            
            attribute = self.data.attributeDict[attributeId]
            
            pen = QtGui.QPen(QtCore.Qt.black, self.thickness_px)
            
            # Construct axis and add to graphicsScene          
            axisLine = QtGui.QGraphicsLineItem(x_pos_px, self.y_pos_start_px, x_pos_px, self.y_pos_end_px)
            axisLine.setPen(pen)
            self.graphicsScene.addItem(axisLine);
            
            # Name label
            nameLabel = QtGui.QGraphicsTextItem()
            attributeName = attribute.name
            nameLabel.setPlainText(attributeName)
            nameLabel.setPos(x_pos_px-20, self.y_pos_start_px-32)
            self.graphicsScene.addItem(nameLabel);
    
            if attribute.scale == "numerical": # min and max labels only for numerical data
    
                # Min label
                minLabel = QtGui.QGraphicsTextItem()
                attributeMin = attribute.minimum
                minLabel.setPlainText(str(attributeMin))
                minLabel.setPos(x_pos_px+10, self.y_pos_end_px)
                self.graphicsScene.addItem(minLabel);
                
                # Max label
                maxLabel = QtGui.QGraphicsTextItem()
                attributeMax = attribute.maximum
                maxLabel.setPlainText(str(attributeMax))
                maxLabel.setPos(x_pos_px+10, self.y_pos_start_px-18)
                self.graphicsScene.addItem(maxLabel);
            
            # print "axis: " + str(attributeId)
        pass
    

    def createLines(self):        
        for id_, feature in self.data.featureDict.items():
            #print "id: " + str(id_)
            #print self.data.featureDict[id_].isSelected
            
            # Does not need to be processed
            if feature.isVisible == False:
                continue
            # Default z value is 0.0 and 1.0 if selected
            z = 0.0
            #print "Selection"
            pen = QtGui.QPen(QtCore.Qt.black)
            if feature.isSelected == True:
                z = 1.0
                #print "isSelected"
                pen.setBrush(QtCore.Qt.red)
        
            # List to store the points on the axes in
            pointList = []
            for position,attribute in self.data.positionToAttribute.items():
                # Calculate position on axis
                x_pos_px = self.threshold_x_begin_px + self.bar_distance_px*position
                y_pos_px = self.y_pos_start_px + (self.y_pos_end_px - self.y_pos_start_px)*(1-feature.normalizedAttributeValues[attribute])
             
                pointList.append(QtCore.QPointF(x_pos_px, y_pos_px))
            
            lineList = []
            for index in range(0,len(pointList)-1):
                line = QtCore.QLineF(pointList[index], pointList[index+1])
                graphicsLine = QtGui.QGraphicsLineItem(line)
                graphicsLine.setZValue(z)
                graphicsLine.setPen(pen)
                lineList.append(graphicsLine)
                self.graphicsScene.addItem(graphicsLine)
             
            pass

    def getAxisByRectangle(self, startPointScene, endPointScene):
        attribute = -1
    
        #Get first selected axis
        for position in self.data.positionToAttribute:
            x_pos_px = self.threshold_x_begin_px + self.bar_distance_px*position
            if endPointScene.x() >= x_pos_px and startPointScene.x() <= x_pos_px:
                attribute = self.data.positionToAttribute[position]
                return attribute
    
        return -1
        pass
          
    def getAxisByPoint(self, pointScene):
        #print "getAxisByPoint"
    
        half_thickness_px = self.thickness_px / 2
    
        for position in self.data.positionToAttribute:
            x_pos_px = self.threshold_x_begin_px + self.bar_distance_px*position
    
            if pointScene.x() >= x_pos_px-half_thickness_px and pointScene.x() <= x_pos_px+half_thickness_px:
                #print "found"
                return position

        return -1
        pass
          
    def getGapByPoint(self, pointScene):
        #print "getGapByPoint"
    
        half_thickness_px = self.thickness_px / 2
    
        for position in self.data.positionToAttribute:
            x_pos_px = self.threshold_x_begin_px + self.bar_distance_px/2 + self.bar_distance_px*position
            
            if pointScene.x() >= x_pos_px-half_thickness_px and pointScene.x() <= x_pos_px+half_thickness_px:
                #print "found"
                return position
    
        return -1
        pass
      
    def rectangleSelection(self, startPointScene, endPointScene):
    
        attribute = self.getAxisByRectangle(startPointScene, endPointScene)
        if attribute == -1:
            return
    
        # Nothing in rectangle
        if endPointScene.y() < self.threshold_y_begin_px:
            return
            
        if endPointScene.y() >= self.axisHeight + self.threshold_y_begin_px:
            selectionValueMax = 1.0
            
        # Get percentual values
        selectionValueMin = (startPointScene.y() - self.threshold_y_begin_px) / (self.axisHeight - 2 * self.threshold_y_begin_px)
        selectionValueMax = (endPointScene.y() - self.threshold_y_begin_px) / (self.axisHeight - 2 * self.threshold_y_begin_px)

        idList = list()
        
        # Select brushed features
        for id, feature in self.data.featureDict.items():
                       
            normalizedValue = 1.0-feature.normalizedAttributeValues[attribute] 
            
            if normalizedValue >= selectionValueMin and normalizedValue <= selectionValueMax:
                feature.isSelected = True
                idList.append(id)
            else:
                feature.isSelected = False
        
        self.setSelectedFeatures(idList)
        self.data.dataInterface.setSelectedFeatures(idList)
        pass
      
      
    def getWidget(self):
        """Returns the widget in which the parallel coordinates are drawn"""
        return self.graphicsView
      
      
class PCGraphicsView(QtGui.QGraphicsView):
    """This Graphics View is used to display Parallel Coordinates"""
    def __init__(self, qGraphicsScene, parent, pcManager):
        QtGui.QGraphicsView.__init__(self, qGraphicsScene, parent)
        
        self.pcManager = pcManager
        
        self.drawingState = False
        self.currentState = "None"
        self.clickedAxis = -1
        self.gapAxis = -1
        
        # Rect for selection
        self.selectionStartX = 0
        self.selectionStartY = 0
        
        # Current position of mouse
        self.mouseCurrentPosX = 0
        self.mouseCurrentPosY = 0
        
        pass
    
    def paintEvent(self, paintEvent):
        super(PCGraphicsView, self).paintEvent(paintEvent)
        
        painter = QtGui.QPainter(self.viewport())
        pen = QtGui.QPen(QtCore.Qt.red)
        painter.setPen(pen)
            
        if self.currentState == "SelectionRectangle":
            rectangle = QtCore.QRect(self.selectionStartX, self.selectionStartY, self.mouseCurrentPosX - self.selectionStartX, self.mouseCurrentPosY - self.selectionStartY)
            painter.drawRect(rectangle)
        elif self.currentState == "AxisSwitchLine":
            startPoint     = QtCore.QPoint(self.selectionStartX, self.selectionStartY)
            endPoint = QtCore.QPoint(self.mouseCurrentPosX, self.mouseCurrentPosY)
            line = QtCore.QLine(startPoint, endPoint)
            painter.drawLine(line)
            if self.gapAxis != -1 and self.gapAxis != self.clickedAxis:
                pen = QtGui.QPen(QtCore.Qt.blue, self.pcManager.thickness_px, QtCore.Qt.SolidLine);
                painter.setPen(pen)
                
                x_pos_px = self.pcManager.threshold_x_begin_px + self.pcManager.bar_distance_px*self.gapAxis
                
                # Draw Axis
                axisStartPoint = super(PCGraphicsView, self).mapFromScene(QtCore.QPointF(x_pos_px, self.pcManager.y_pos_start_px))
                axisEndPoint = super(PCGraphicsView, self).mapFromScene(QtCore.QPointF(x_pos_px, self.pcManager.y_pos_end_px))

                line = QtCore.QLine(axisStartPoint, axisEndPoint)
                painter.drawLine(line)
            
        pass
    
    def mousePressEvent(self, event):
        super(PCGraphicsView, self).mousePressEvent(event)
        startPointScene = super(PCGraphicsView, self).mapToScene(QtCore.QPoint(event.x(), event.y()))
        self.clickedAxis = self.pcManager.getAxisByPoint(startPointScene)

        if self.clickedAxis == -1:
            self.currentState = "SelectionRectangle"
        else:
            self.currentState = "AxisSwitchLine"
            
        self.drawingState = True
        self.selectionStartX = event.x()
        self.selectionStartY = event.y()
    
        pass
      
      
    def mouseMoveEvent(self, event):
        super(PCGraphicsView, self).mouseMoveEvent(event)
        if self.drawingState == True:
            self.mouseCurrentPosX = event.x()
            self.mouseCurrentPosY = event.y()
            
            if self.currentState == "AxisSwitchLine":
                point = super(PCGraphicsView, self).mapToScene(QtCore.QPoint(self.mouseCurrentPosX, self.mouseCurrentPosY))
                self.gapAxis = self.pcManager.getGapByPoint(point)
                if self.gapAxis == -1:
                    self.gapAxis = self.pcManager.getAxisByPoint(point)
                else:
                    self.gapAxis += 0.5 # adjustment for gaps for use as multiplier
                
            self.repaint()
            
        pass
    
    def mouseReleaseEvent(self, event):
        #print "Mouse released"
        super(PCGraphicsView, self).mouseReleaseEvent(event)
        self.drawingState = False
    
        tempSelectionEndX = event.x()
        tempSelectionEndY = event.y()
        
        startPoint = QtCore.QPoint(0.0, 0.0)
        endPoint = QtCore.QPoint(0.0, 0.0)
        
        # Define points of rectangle
        if self.currentState == "SelectionRectangle":
            if (tempSelectionEndX < self.selectionStartX):
                startPoint.setX(tempSelectionEndX)
                endPoint.setX(self.selectionStartX)
            else:
                startPoint.setX(self.selectionStartX) 
                endPoint.setX(tempSelectionEndX)
            
            if (tempSelectionEndY < self.selectionStartY):
                startPoint.setY(tempSelectionEndY)
                endPoint.setY(self.selectionStartY) 
            else:
                startPoint.setY(self.selectionStartY) 
                endPoint.setY(tempSelectionEndY) 
            
            # Map to scene
            startPointScene = super(PCGraphicsView, self).mapToScene(startPoint)
            endPointScene = super(PCGraphicsView, self).mapToScene(endPoint)
    
            self.pcManager.rectangleSelection(startPointScene, endPointScene)
            
        elif self.currentState == "AxisSwitchLine" and self.clickedAxis != -1 and self.gapAxis != -1:
            self.pcManager.data.moveAxes(self.clickedAxis, self.gapAxis)
        
        # Reset
        self.clickedAxis = -1
        self.gapAxis = -1
        self.currentState = "None"
        self.repaint()
        pass