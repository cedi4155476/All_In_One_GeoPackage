# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AllInOneGeopackage
                                 A QGIS plugin
 This Plugin writes and reads Project files in Geopackages.
                              -------------------
        begin                : 2016-03-31
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Cédric Christen
        email                : cch@sourcepole.ch
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
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import resources

from read import Read
from write import Write


class AllInOneGeopackage:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.toolbar = self.iface.addToolBar(u'All-In-One Geopackage')
        self.toolbar.setObjectName(u'All-In-One Geopackage')

    def initGui(self):
        self.actionWrite = QAction(
            QIcon(":/plugins/AllInOneGeopackage/write.png"),
            u"Write Project in GeoPackage",
            self.iface.mainWindow()
        )
        self.actionWrite.setWhatsThis(u"Write Project in GeoPackage")
        self.iface.addPluginToMenu("&All-In-One Geopackage", self.actionWrite)
        self.toolbar.addAction(self.actionWrite)
        QObject.connect(self.actionWrite, SIGNAL("triggered()"), self.write)

        self.actionRead = QAction(
            QIcon(":/plugins/AllInOneGeopackage/read.png"),
            u"Read Project from GeoPackage",
            self.iface.mainWindow()
        )
        self.actionRead.setWhatsThis(u"Read Project from GeoPackage")
        self.iface.addPluginToMenu("&All-In-One Geopackage", self.actionRead)
        self.toolbar.addAction(self.actionRead)
        QObject.connect(self.actionRead, SIGNAL("triggered()"), self.read)

    def unload(self):
        self.iface.removePluginMenu("&All-In-One Geopackage", self.actionWrite)
        self.iface.removePluginMenu("&All-In-One Geopackage", self.actionRead)
        self.iface.removeToolBarIcon(self.actionWrite)
        self.iface.removeToolBarIcon(self.actionRead)

    def write(self):
        write = Write(self.iface.mainWindow(), self.iface)

    def read(self):
        read = Read(self.iface.mainWindow(), self.iface)
