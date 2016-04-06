# coding=latin-1

import tempfile
import sqlite3
import os
from qgis.core import *
from PyQt4.QtCore import *
from xml.etree import ElementTree as ET


class Read():
    def __init__(self, iface, parent=None):
        self.parent = parent
        self.iface = iface

    def database_connect(self, path):
        ''' Datenbank mit sqlite3 Verbinden, bei Fehlschlag wird False zurückgegeben '''
        try:
            self.conn = sqlite3.connect(path)
            self.c = self.conn.cursor()
            return True
        except:
            return False

    def check_gpkg(self, path):
        ''' Es wird überprüft, ob die Datei wirklich ein Geopackage ist '''
        try:
            self.c.execute('SELECT * FROM gpkg_contents')
            self.c.fetchone()
            return True
        except:
            return False

    def make_path_absolute(self, path, project_path):
        ''' Pfad wird Absolut und Betriebsystemübergreifend gemacht'''
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(project_path), path)
        return os.path.normpath(path)

    def run(self, gpkg_path):
        # Überprüfen ob es sich um eine GeoPackage Datei handelt
        self.database_connect(gpkg_path)
        if not self.check_gpkg(gpkg_path):
            print "please select gpkg"

        # Den XML-Code aus der Datenbank herauslesen
        self.c.execute('SELECT name, xml FROM _qgis')
        file_name, xml = self.c.fetchone()
        xml_tree = ET.ElementTree()
        root = ET.fromstring(xml)
        xml_tree._setroot(root)
        projectlayers = root.find("projectlayers")

        # layerpfäde im xml werden angepasst
        project_path = os.path.join(tempfile.gettempdir(), file_name)
        for layer in projectlayers:
            layer_element = layer.find("datasource")
            layer_info = layer_element.text.split("|")
            layer_path = self.make_path_absolute(layer_info[0], gpkg_path)
            if layer_path.endswith('.gpkg'):
                if len(layer_info) >= 2:
                    for i in range(len(layer_info)):
                        if i == 0:
                            layer_element.text = layer_path
                        else:
                            layer_element.text += "|" + layer_info[i]
                elif len(layer_info) == 1:
                    layer_element.text = layer_path

        # Überprüfen, ob im Composer ein Bild enthalten ist
        composer_list = root.findall("Composer")
        images = []
        for composer in composer_list:
            for comp in composer:
                composer_picture = comp.find("ComposerPicture")
                img = self.make_path_absolute(composer_picture.attrib['file'], project_path)
                # Wenn ja, wird der Pfad angepasst
                composer_picture.set('file', './' + os.path.basename(img))
                images.append(img)

        # und das Bild wird im selben ordner wie das Projekt gespeichert
        if images:
            self.c.execute("SELECT name, type, blob FROM _img_project")
            images = self.c.fetchall()
            for img in images:
                name, type, blob = img
                img_name = name + type
                img_path = os.path.join(tempfile.gettempdir(), img_name)
                with open(img_path, 'wb') as file:
                    file.write(blob)
        # Projekt wird gespeichert und gestartet
        xml_tree.write(project_path)
        QgsProject.instance().read(QFileInfo(project_path))
