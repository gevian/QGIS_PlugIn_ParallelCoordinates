# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ParallelCoordinates_Plugin
                                 A QGIS plugin
 Allows interactive visual analysis using parallel coordinates.
                              -------------------
        begin                : 2014-06-28
        copyright            : (C) 2014 by Magnus Heitzler
        email                : magnus.heitzler@gmx.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
import os
from PyQt4 import uic
from PyQt4 import QtCore
from qgis.core import *  
import webbrowser

from parallelcoordinates import *

class ParallelCoordinates_Plugin:
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
    
    def initGui(self):
        # Timer used to delay the update of the parallel coordinates which speeds up the graphic
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.visibleFeaturesChanged)
        
        # Hide invisible is checked from the beginning on
        self.allFeaturesVisible = False
        
        # Thanks to "Underdark" for this method of how to dynamically load the ui file
        path = os.path.dirname( os.path.abspath( __file__ ) )
        self.dockWidget = uic.loadUi( os.path.join( path, "ui_pk_mainWidget.ui" ) )
        
        self.iface.addDockWidget( QtCore.Qt.BottomDockWidgetArea, self.dockWidget )
        
        # Update if layers changed
        QgsMapLayerRegistry.instance().layerWillBeRemoved.connect(self.updateLayers)  # @UndefinedVariable
        QgsMapLayerRegistry.instance().layerWasAdded.connect(self.updateLayers)  # @UndefinedVariable
       
        # Important member variables
        self.currentLayer = "no layer"
        self.attributesToBeDisplayed = list()
        
        # Attribute dialog
        self.attributesDialog = uic.loadUi( os.path.join( path, "ui_pk_attributesDialog.ui" ) )
        self.dockWidget.selectAttributes.clicked.connect(self.showDialog)
        self.dockWidget.layerComboBox.currentIndexChanged.connect(self.selectedLayerChanged)

        # Progress dialog
        self.progressDialog = uic.loadUi(os.path.join (path, "ui_pk_progressDialog.ui"))


        self.dockWidget.hideInvisibleFeaturesCheckBox.clicked.connect(self.visibleFeaturesChanged)
        
        # Initialize self.dockWidget.layerComboBox and self.dockWidget.selectAttributes
        self.updateLayers("")
        
        # Set up parallel coordinates classes
        self.pcManager = PCManager(self.dockWidget)
        self.dataInterface = QGIS_VL_PCDataInterface(self.iface, self)
        self.pcManager.setDataInterface(self.dataInterface)
        self.pcWidget = self.pcManager.getWidget()
        self.pcWidget.setStyleSheet("background-color:white;")
        
        self.dockWidget.layerComboBox.currentIndexChanged.connect(self.selectedLayerChanged)
    
        self.dockWidget.helpPushButton.clicked.connect(self.displayHelp)
    
        self.dockWidget.dockWidgetContents.layout().insertWidget(0, self.pcWidget)
        
        self.iface.mapCanvas().selectionChanged.connect(self.featureSelectionChanged)
        self.iface.mapCanvas().extentsChanged.connect(self.mapExtentChanged)
        pass
 
    def unload(self):
        self.timer.timeout.disconnect(self.visibleFeaturesChanged)
        self.pcManager.removeData()
        #del self.pcManager
        #del self.dataInterface
        self.iface.removeDockWidget(self.dockWidget)
        pass
        
    def run(self):
        pass
    
    def updateLayers(self, layerToBeRemoved):
        if QgsMapLayerRegistry is None:  # @UndefinedVariable
            return
        
        # Temporary disconnect signal/slot to prevent that selectedLayerChanged() is called too often
        # Maybe not the cleanest solution?
        self.dockWidget.layerComboBox.currentIndexChanged.disconnect(self.selectedLayerChanged)
    
        # Clear
        self.dockWidget.layerComboBox.clear()
        self.dockWidget.layerComboBox.addItem("no layer", "no layer")
    
        # Add new layers of type vector except for the one to be removed
        layers = QgsMapLayerRegistry.instance().mapLayers()  # @UndefinedVariable
    
        for name, layer in layers.iteritems():
            if layer.type() == 0 and name != layerToBeRemoved:
                self.dockWidget.layerComboBox.addItem(layer.name(), name)
      
        # Reconnect
        self.dockWidget.layerComboBox.currentIndexChanged.connect(self.selectedLayerChanged)
        
        # Call selectedLayerChanged
        self.selectedLayerChanged()
          
          
    def selectedLayerChanged(self):
        # Disconnect if necessary
        layerID = str(self.dockWidget.layerComboBox.itemData(self.dockWidget.layerComboBox.currentIndex()))

        # Nothing changed, nothing to do
        if (self.currentLayer == layerID):
            return
        else:
            # update layers
            self.currentLayer = layerID
            self.attributesToBeDisplayed = []
        
        # Disable pushbutton if "no layer" is chosen
        if (self.currentLayer == "no layer"):
            self.dockWidget.selectAttributes.setEnabled(False)
        else:
            self.dockWidget.selectAttributes.setEnabled(True)
        
        if (self.dataInterface.setDataOfInterest(self.currentLayer)):
            self.progressDialog.show()
            self.pcManager.updateData(self.setProgress)
            self.progressDialog.hide()
        else:
            self.pcManager.removeData()


    pass

    def setProgress(self, progress):
        self.progressDialog.progressBar.setValue(progress)
        QgsApplication.processEvents()
        pass


    def showDialog(self):
        # Clean up the table
        self.attributesDialog.attributesTable.clearContents()
        
        while (self.attributesDialog.attributesTable.rowCount() != 0):
            self.attributesDialog.attributesTable.removeRow(0)
        
        # Get selected Layer
        layers = QgsMapLayerRegistry.instance().mapLayers()  # @UndefinedVariable
        selectedLayer = layers[self.currentLayer]
    
        # Refill the table according to self.attributeToPosition
        dataProvider = selectedLayer.dataProvider()
        allAttrs = dataProvider.attributeIndexes()
        #dataProvider.select(allAttrs) -- Depreciated in 2.0

        fields = dataProvider.fields()
        for index in range(fields.size()):
            field = fields[index]

            # Add new row
            self.attributesDialog.attributesTable.insertRow(self.attributesDialog.attributesTable.rowCount())
            
            # Add index
            indexItem = QtGui.QTableWidgetItem()
            indexItem.setText(str(index))
            
            self.attributesDialog.attributesTable.setItem(self.attributesDialog.attributesTable.rowCount()-1, 0, indexItem)
            
            # Add attributeName
            attributeItem = QtGui.QTableWidgetItem()
            attributeItem.setText(field.name())
            
            self.attributesDialog.attributesTable.setItem(self.attributesDialog.attributesTable.rowCount()-1, 1, attributeItem)
            
            # Add checkBox
            checkbox = QtGui.QCheckBox()
            self.attributesDialog.attributesTable.setCellWidget(self.attributesDialog.attributesTable.rowCount()-1, 2, checkbox)
            
            if index in self.attributesToBeDisplayed:
                checkbox.setCheckState(QtCore.Qt.Checked)    
        
        # Show the dialog
        self.attributesDialog.exec_()
    
        
        if (self.attributesDialog.result() == QtGui.QDialog.Accepted):
            self.attributesToBeDisplayed = []
            # Iterate over the checkboxes and add corresponding text to the dict
            axis_position  = 0
            for i in range(0, self.attributesDialog.attributesTable.rowCount()):
                cb = self.attributesDialog.attributesTable.cellWidget(i, 2)
                index = int(self.attributesDialog.attributesTable.item(i, 0).text()) # table is PyQt specific
                if (cb.checkState() == QtCore.Qt.Checked):      # insert if checked
                    self.attributesToBeDisplayed.append(index)
                    axis_position += 1
    
        self.pcManager.setVisibleAttributes(self.attributesToBeDisplayed)
    pass
      
    def featureSelectionChanged(self, layer):
        if self.dataInterface is None:
            return
        
        if layer.id() == self.dataInterface.layerID:
            #print layer.selectedFeaturesIds()
            self.pcManager.setSelectedFeatures(layer.selectedFeaturesIds())
    pass
      
    def mapExtentChanged(self):
        self.timer.start(500);
    pass
      
    def visibleFeaturesChanged(self):
        
        if self.dockWidget.hideInvisibleFeaturesCheckBox.isChecked():
            selectionRectangle = self.iface.mapCanvas().extent() # Features only in extent
            self.allFeaturesVisible = False
        else:
            if self.allFeaturesVisible == True: # If all features are visible, we do not need to iterate through all features
                return
            else:
                selectionRectangle = QgsRectangle() # @UndefinedVariable; All Features of layer
                self.allFeaturesVisible = True
                
        layers = QgsMapLayerRegistry.instance().mapLayers()  # @UndefinedVariable
        #print "visibleFeaturesChanged"
        if self.currentLayer in layers:
            selectedLayer = layers[self.currentLayer]
            #provider = selectedLayer.dataProvider() # Depreciated in 2.0
            #provider.select([], selectionRectangle, False) # @UndefinedVariable

            #feat = QgsFeature() # @UndefinedVariable
            #idList = list()

            #while provider.nextFeature(feat):
            #    idList.append(feat.id())

            idList = list()
            request=QgsFeatureRequest()
            request.setFilterRect(selectionRectangle)
            for feat in selectedLayer.getFeatures(request):
                idList.append(feat.id())


            
            #print idList
            self.pcManager.setVisibleFeatures(idList)
    pass

    def displayHelp(self):
        path = os.path.dirname( __file__ )
        webbrowser.open_new_tab(path + '/help/index.html')
    
    pass


class QGIS_VL_PCDataInterface(PCDataInterface):
    """This concrete class implements the abstract functions defined by PCDataInterface for a QGISVectorLayer"""
    def __init__(self, iface, plugin):
        PCDataInterface.__init__(self)
        
        self.plugin = plugin
        self.iface = iface
        self.layerID = "no layer"
        
    def setDataOfInterest(self, layerID):
        self.layerID = layerID
        
        # Get layer
        layers = QgsMapLayerRegistry.instance().mapLayers()  # @UndefinedVariable
        if layerID not in layers:
            return False
        
        self.selectedLayer = layers[layerID]
        
        self.selectedFeatureIds = self.selectedLayer.selectedFeaturesIds()
        
        self.provider = self.selectedLayer.dataProvider()
        self.featureIterator = self.selectedLayer.getFeatures()

        self.fields = self.provider.fields()
        self.fieldsCount = len(self.fields)
        self.fieldIndex = -1
        
        return True
    pass
    
    def getAttributesToBeDisplayed(self):
        return self.selectAttributes
    pass
      
    def finished(self):
        # In this case, it just resets everything related to the layerID 
        self.setDataOfInterest(self.layerID) 
    pass
    
    
    def nextAttribute(self, attribute):
        self.fieldIndex += 1
        if (self.fieldIndex == self.fieldsCount):
            self.fieldIndex = -1
            return False
        
        # Set attribute values           
        attribute.id = self.fieldIndex
        attribute.name = self.fields[self.fieldIndex].name()
        
        # Define type
        typeName = self.fields[self.fieldIndex].typeName()
        if typeName == "Real" or typeName == "Integer":
            attribute.scale = "numerical"
            
            attribute.isVisible = True
            attribute.unit = "unknown"
            attribute.minimum = float(self.provider.minimumValue(self.fieldIndex))
            attribute.maximum = float(self.provider.maximumValue(self.fieldIndex))
            
        else: # typeName == "String"
            attribute.scale = "categorical"
            
            attribute.isVisible = True
            uniqueValuesList = self.provider.uniqueValues(self.fieldIndex)
            uniqueValuesList = [str(value) for value in uniqueValuesList]
            attribute.uniqueValues = uniqueValuesList
            attribute.numberUniqueValues = len(uniqueValuesList)
            #print uniqueValuesList
    
        return True
    
    def nextFeature(self, feature):
        # Set feature values
        qgsFeature = QgsFeature()
        hasNextFeature = self.featureIterator.nextFeature(qgsFeature)
        #print "Has next feature: " + str(hasNextFeature)

        if (hasNextFeature == False):
            return False

        featureAttributes = qgsFeature.attributes()
        featureAttributeMap = dict()
        for fieldIndex in range (self.fieldsCount): # TODO: Maybe switch from map representation to list representation
            if featureAttributes[fieldIndex] == NULL:
                featureAttributeMap[fieldIndex] = None
            else:
                featureAttributeMap[fieldIndex] = featureAttributes[fieldIndex]

        featureID = qgsFeature.id()
        featureIsSelected = False
        
        if featureID in self.selectedFeatureIds:
            featureIsSelected = True
        
        # Construct the PCFeature
        feature.id = featureID
        feature.isSelected = featureIsSelected
        feature.isVisible = True
        feature.attributeValues = featureAttributeMap.copy()
        feature.normalizedAttributeValues =  {}

        # Return if there are any features left to get # TODO: Revise
        return True
        
    def setSelectedFeatures(self, idList):
        self.selectedLayer.removeSelection()
        self.selectedLayer.select(idList)

    pass
  
