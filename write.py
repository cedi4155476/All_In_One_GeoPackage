# coding=latin-1

from qgis.core import *
from qgis.gui import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import tempfile
import os
import sqlite3
from xml.etree import ElementTree as ET


class Write():
    def __init__(self, iface, parent=None):
        ''' Klasse wird initialisiert '''
        self.parent = parent
        self.iface = iface

    def read_project(self, path):
        ''' Überprüfen ob es sich um ein File handelt und dieses dann als ElementTree objekt zurückgeben '''
        if not os.path.isfile(path):
            return False

        return ET.parse(path)

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

    def run(self):
        ''' Hauptfunktion in welcher alles Abläuft '''
        project = QgsProject.instance()
        if project.isDirty():
            # Wenn das Projekt seit dem letzten bearbeiten nicht gespeichert wurde,
            # wird eine Temporärdatei erstellt und dann gelöscht
            tmpfile = os.path.join(tempfile.gettempdir(), "temp_project.qgs")
            file_info = QFileInfo(tmpfile)
            project.write(file_info)
            project_path = project.fileName()
            xmltree = self.read_project(project_path)
            os.remove(project.fileName())
            project.dirty(True)
        else:
            # Sonst wird einfach der Pfad die Datei selber verwendet
            project_path = project.fileName()
            xmltree = self.read_project(project_path)
            project.dirty(False)

        # Wenn etwas mit der Projektdatei nicht mehr stimmt, muss abgebrochen werden.
        if not xmltree:
            self.iface.messageBar().pushMessage("Error", "Es gibt Probleme mit der Projektdatei, bitte überprüfen Sie diese.", level=QgsMessageBar.CRITICAL)
            return

        QgsMessageLog.logMessage("XML wurde erfolgreich eingelesen.", 'All-In-One Geopackage', QgsMessageLog.INFO)
        root = xmltree.getroot()
        projectlayers = root.find("projectlayers")

        # Es wird nach allen Daten-quellen gesucht
        sources = []
        for layer in projectlayers:
            layer_path = self.make_path_absolute(layer.find("datasource").text.split("|")[0], project_path)
            if layer_path not in sources:
                QgsMessageLog.logMessage("Quelldatei gefunden: " + layer_path, 'All-In-One Geopackage', QgsMessageLog.INFO)
                sources.append(layer_path)

        # Sind mehrere Datenquellen vorhanden müssen deren Ursprung überprüft werden
        if len(sources) > 1:
            gpkg_found = False
            for path in sources:
                if self.database_connect(path):
                    if self.check_gpkg(path) and not gpkg_found:
                        gpkg_found = True
                        gpkg_path = path
                    elif self.check_gpkg(path) and gpkg_found:
                        # Hat ein Projekt Layer aus verschiedenen GeoPackage Datenbanken,
                        # kann das Einschreiben nicht ausgeführt werden
                        QgsMessageLog.logMessage("Es werden mehrere GeoPackage Datenbanken vom Projekt benutzt.", 'All-In-One Geopackage', QgsMessageLog.CRITICAL)
                        self.iface.messageBar().pushMessage("Error", "Es werden mehrere GeoPackage Datenbanken vom Projekt benutzt.", level=QgsMessageBar.CRITICAL)
                        return
            QgsMessageLog.logMessage("Es kann nicht garantiert werden, dass Layer, welche nicht im GeoPackage gespeichert sind, beim auslesen richtig angezeigt werden.", 'All-In-One Geopackage', QgsMessageLog.WARNING)
            self.iface.messageBar().pushMessage("Warnung", "Es kann nicht garantiert werden, dass Layer, welche nicht im GeoPackage gespeichert sind, beim auslesen richtig angezeigt werden.", level=QgsMessageBar.WARNING)
        else:
            gpkg_path = sources[0]

        self.database_connect(gpkg_path)

        if not self.check_gpkg(gpkg_path):
            # Stammen die Layer nicht aus einer GeoPackage Datei, kann nicht weiterverarbeitet werden
            raise

        # Es wird nach Bildern im Projekt gesucht
        composer_list = root.findall("Composer")
        images = []
        for composer in composer_list:
            for comp in composer:
                img = self.make_path_absolute(comp.find("ComposerPicture").attrib['file'], project_path)
                if img not in images:
                    QgsMessageLog.logMessage("Bilddatei gefunden: " + img, 'All-In-One Geopackage', QgsMessageLog.INFO)
                    images.append(img)

        # Die Daten werden in die Datenbank eingeschrieben
        inserts = (os.path.basename(project.fileName()), ET.tostring(root))
        extensions = (None, None, 'all_in_one_geopackage', 'Insert and read a QGIS Project file into the GeoPackage database.', 'read-write')

        try:
            # Falls bereits ein Projekt vorhanden ist, wird nichts geändert
            self.c.execute('SELECT name FROM _qgis')
            reply = QMessageBox.question(self.parent, "Warnung", "Es ist bereits ein Projekt vorhanden, \nSoll dieses Überschrieben werden?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes
            if reply:
                self.c.execute('UPDATE _qgis SET name=?, xml=?', inserts)
                QgsMessageLog.logMessage("Projekttabelle wurde ersetzt.", 'All-In-One Geopackage', QgsMessageLog.INFO)
            else:
                QgsMessageLog.logMessage("Verarbeitung abgebrochen.", 'All-In-One Geopackage', QgsMessageLog.INFO)
        except sqlite3.OperationalError:
            self.c.execute('CREATE TABLE _qgis (name text, xml text)')
            self.c.execute('INSERT INTO _qgis VALUES (?,?)', inserts)
            self.c.execute('INSERT INTO gpkg_extensions VALUES (?,?,?,?,?)', extensions)
            QgsMessageLog.logMessage("Projekt " + inserts[0] + " wurde gespeichert.", 'All-In-One Geopackage', QgsMessageLog.INFO)

        if images:
            # Falls vorhanden, werden hier die Bilder in die Datenbank eingelesen
            # Jedoch nur, wenn die Tabelle noch nicht existiert
            try:
                self.c.execute('SELECT name FROM _img_project')
                if reply:
                    self.c.execute('DROP TABLE _img_project')
                    raise sqlite3.OperationalError
            except sqlite3.OperationalError:
                self.c.execute('CREATE TABLE _img_project (name text, type text, blob blob)')
                for image in images:
                    with open(image, 'rb') as input_file:
                        blob = input_file.read()
                        name, type = os.path.splitext(os.path.basename(image))
                        inserts = (name, type, sqlite3.Binary(blob))
                        self.conn.execute('INSERT INTO _img_project VALUES(?, ?, ?)', inserts)
                        QgsMessageLog.logMessage("Bild " + name + " wurde gespeichert.", 'All-In-One Geopackage', QgsMessageLog.INFO)
        self.conn.commit()
