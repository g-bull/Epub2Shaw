# SPDX-FileCopyrightText: 2026 Geoff Bull
# SPDX-License-Identifier: MIT

import io
import json
import csv
import sys
from io import StringIO

import tomllib
from importlib import resources

from pathlib import Path
import zipfile

from bs4 import BeautifulSoup

#class Package:

class EPub_Reader:

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.archive = None

    def __enter__(self):
        self.archive = zipfile.ZipFile(self.file_path, 'r')
        self.root_path = self._get_root_path()
        self.package_xml = self._get_package()
        #print(self.package_xml)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.archive:
            self.archive.close()

    def _get_package(self):
        with self.archive.open(self.root_path) as binary_file:
            # Decode bytes into a text stream
            with io.TextIOWrapper(binary_file, encoding='utf-8') as text_file:
                return text_file.read()



    def _get_root_path(self):

        with self.archive.open("META-INF/container.xml") as binary_file:
            # get the value of full-path from  <container><rootfiles><rootfile>
            # if there is more than one <rootfile>, ignore all but the first.
            with io.TextIOWrapper(binary_file, encoding='utf-8') as text_file:
                xml_content = text_file.read()

                soup = BeautifulSoup(xml_content, 'xml')
                rootfiles = soup.find_all('rootfile')


                for rootfile in rootfiles:
                    attrs = rootfile.attrs
                    return attrs['full-path']
                    