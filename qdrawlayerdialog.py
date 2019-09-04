# -*- coding: utf-8 -*-

# QDraw: plugin that makes drawing easier
# Author: Jérémy Kalsron
#         jeremy.kalsron@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# import numpy as np
# import pandas as pd
#
# from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
# from qgis.PyQt.QtGui import QIcon, QColor
# from qgis.PyQt.QtWidgets import QAction, QFileDialog, QTableWidgetItem


from qgis.PyQt.QtCore import QCoreApplication, Qt, QVariant
from qgis.PyQt.QtWidgets import QDialog, QComboBox, QLineEdit, QVBoxLayout, \
    QCheckBox, QDialogButtonBox, QLabel
from qgis.core import QgsFeature, QgsProject, QgsGeometry,\
    QgsCoordinateTransform, QgsCoordinateTransformContext, QgsMapLayer,\
    QgsFeatureRequest, QgsVectorLayer, QgsLayerTreeGroup, QgsRenderContext,\
    QgsWkbTypes

class QDrawLayerDialog(QDialog):

    chsnlanduse = ""

    def draw_dialog(self):
        QDialog.__init__(self)

        self.setWindowTitle(self.tr('Drawing'))

        self.name = QLineEdit()

        gtype = 'Polygon'

        # Choose which object is placed
        LandUseTypes = ['Trees on grass', 'Trees on avenue', 'Grass field', 'Green roofs', 'Cool roofs',
                        'Facade greening', 'Solar Panels', 'Pond/river', 'Fountain', 'Surface albedo change']
        self.ObjectType = QComboBox()
        self.ObjectType.insertItems(0, LandUseTypes)
        # change here by QgsMapLayerComboBox()
        self.layerBox = QComboBox()
        self.layers = []
        for layer in QgsProject.instance().mapLayers().values():
            if layer.providerType() == "memory":
                # ligne suivante à remplacer par if layer.geometryType() == :
                if gtype in layer.dataProvider().dataSourceUri()[:26]:  # must be of the same type of the draw
                    if 'field=' + self.tr('Drawings') + ':string(255,0)' in layer.dataProvider().dataSourceUri()[
                                                                            -28:]:  # must have its first field named Drawings, string type
                        self.layers.append(layer)
                        self.layerBox.addItem(layer.name())
                        global layername
                        layername = layer.name()

        # Save the chosen land use
        chsnlanduse = self.ObjectType.currentText()
        print(chsnlanduse)

        # CheckBox to add to layer
        # self.addLayer = QCheckBox(self.tr('Add to an existing layer'))
        # self.addLayer.toggled.connect(self.addLayerChecked)

        # Ok and cancel button
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        # buttons.accepted.connect(self.addInformation(chsnlanduse, layer))
        buttons.rejected.connect(self.reject)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel(self.tr("Give a name to the feature:")))
        vbox.addWidget(self.name)
        vbox.addWidget(self.ObjectType)
        vbox.addWidget(self.addLayer)
        vbox.addWidget(self.layerBox)
        if len(self.layers) == 0:
            self.addLayer.setEnabled(False)
            self.layerBox.setEnabled(False)
        vbox.addWidget(buttons)
        self.setLayout(vbox)

        self.layerBox.setEnabled(False)
        self.name.setFocus()

    def drawPolygon(self):
        if self.tool:
            self.tool.reset()
        self.tool = DrawPolygon(self.iface, self.settings.getColor())
        self.tool.setAction(self.actions[0])
        self.tool.selectionDone.connect(self.draw)
        self.tool.move.connect(self.updateSB)
        self.iface.mapCanvas().setMapTool(self.tool)
        self.drawShape = 'polygon'
        self.toolname = 'drawPolygon'
        self.resetSB()

    def resetSB(self):
        message = {
            'drawPolygon': 'Left click to place points. Right click to confirm.',
        }
        self.sb.showMessage(self.tr(message[self.toolname]))

    def updateSB(self):
        g = self.geomTransform(
            self.tool.rb.asGeometry(),
            self.iface.mapCanvas().mapSettings().destinationCrs(),
            QgsCoordinateReferenceSystem(2154))
        if self.toolname == 'drawLine':
            if g.length() >= 0:
                self.sb.showMessage(
                    self.tr('Length') + ': ' + str("%.2f" % g.length()) + " m")
            else:
                self.sb.showMessage(self.tr('Length') + ': ' + "0 m")
        else:
            if g.area() >= 0:
                self.sb.showMessage(
                    self.tr('Area') + ': ' + str("%.2f" % g.area()) + " m" + u'²')
            else:
                self.sb.showMessage(self.tr('Area') + ': ' + "0 m" + u'²')
        self.addInformation()
        self.iface.mapCanvas().mapSettings().destinationCrs().authid()

    def __init__(self, iface, gtype):
        self.draw_dialog()
        self.drawPolygon()

    def tr(self, message):
        return QCoreApplication.translate('Qdraw', message)

    def addInformation(self,layername):
        root = QgsProject.instance().layerTreeRoot()
        mygroup = root.findGroup("Drawings")  # We assume the group exists
        vLayer = iface.activeLayer()
        # vLayer = mygroup.findLayer(str(layername))
        vLayer.startEditing()

        # Create feature called Land use
        # caps = vLayer.dataProvider().capabilities()
        if QgsVectorDataProvider.AddAttributes:
            res = vLayer.dataProvider().addAttributes([QgsField("Land use", QVariant.String)])
            vLayer.updateFields()

        landuserastvalue = {'Trees on grass': 1, 'Trees on avenue': 2, 'Grass field': 3,
                            'Green roofs': 4, 'Cool roofs': 5, 'Facade greening': 6,
                            'Solar Panels': 7, 'Pond/river': 8, 'Fountain': 9, 'Surface albedo change': 10}

        for chsnlanduse, v in landuserastvalue.items():
            print(v)
            LanduseValue = str(v)

        vLayer = iface.mapCanvas().currentLayer()
        caps = vLayer.dataProvider().capabilities()

        if caps & QgsVectorDataProvider.AddAttributes:
            vLayer.dataProvider().addAttributes([QgsField("Raster Value", QVariant.String)])
            vLayer.updateFields()

        # Add attributes to "Land Use"
        id_new_col = vLayer.dataProvider().fieldNameIndex("Land use")

        for f in vLayer.getFeatures():
            vLayer.changeAttributeValue(f.id(), id_new_col, chsnlanduse)
            vLayer.updateFeature(f)

        # Connect values to chosen land use
        landuserastvalue = {'Trees on grass': 1, 'Trees on avenue': 2, 'Grass field': 3,
                            'Green roofs': 4, 'Cool roofs': 5, 'Facade greening': 6,
                            'Solar Panels': 7, 'Pond/river': 8, 'Fountain': 9, 'Surface albedo change': 10}

        id_new_col = vLayer.dataProvider().fieldNameIndex(LanduseValue)

        for f in vLayer.getFeatures():
            vLayer.changeAttributeValue(f.id(), id_new_col, LanduseValue)
            vLayer.updateFeature(f)

        vLayer.commitChanges()

    def addLayerChecked(self):
        if self.addLayer.checkState() == Qt.Checked:
            self.layerBox.setEnabled(True)
        else:
            self.layerBox.setEnabled(False)

    def getName(self, iface, gtype):
        dialog = QDrawLayerDialog(iface, gtype)
        result = dialog.exec_()
        return (
            dialog.name.text(),
            dialog.addLayer.checkState() == Qt.Checked,
            dialog.layerBox.currentIndex(),
            dialog.layers,
            result == QDialog.Accepted)


