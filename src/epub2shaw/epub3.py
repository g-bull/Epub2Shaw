# SPDX-FileCopyrightText: 2026 Geoff Bull
# SPDX-License-Identifier: MIT

import io
import json
import csv
import sys
from io import StringIO

from lxml import etree

import tomllib
from importlib import resources

from pathlib import Path
import zipfile

#from bs4 import BeautifulSoup

#class Package:
class EPub:

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.archive = None
        self.root_path = None
        self.package_xml = None

class EPub_Reader:

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.archive = None

    def __enter__(self):
        self.archive = zipfile.ZipFile(self.file_path, 'r')
        self.root_path = self._get_root_path()
        print("root_path: " + str(self.root_path))
        self.package_xml = self._get_package()
        #print(self.package_xml)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.archive:
            self.archive.close()

    def _get_package(self):
        with self.archive.open(self.root_path) as xml_file:
            return etree.parse(xml_file)



    def _get_root_path(self):

        with self.archive.open("META-INF/container.xml") as xml_file:
            # get the value of full-path from  <container><rootfiles><rootfile>
            # if there is more than one <rootfile>, ignore all but the first.
            xml_tree = etree.parse(xml_file)
            xml_root = xml_tree.getroot()
            for rootfile in xml_tree.findall(
            ".//x:rootfile[@media-type]", namespaces={"x": "urn:oasis:names:tc:opendocument:xmlns:container"}
            ):
                if rootfile.get("media-type") == "application/oebps-package+xml":
                    return rootfile.get("full-path")
                    