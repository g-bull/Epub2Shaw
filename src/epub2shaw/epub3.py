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
class Epub3_Exception(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg

    def __str__(self) -> str:
        return repr(self.msg)
class Namespace_Exception(Epub3_Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg

    def __str__(self) -> str:
        return repr(self.msg)

class Unexpected_Element_Exception(Epub3_Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg

    def __str__(self) -> str:
        return repr(self.msg)

class Unsupported_Feature_EXception(Epub3_Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg

    def __str__(self) -> str:
        return repr(self.msg)

    
    

class Manifest_Item:
   
    def __init__(self, href, id, media_type, 
                 fallback = None,
                 media_overlay = None,
                 properties = None):
        self.href: str  | None = href
        self.id: str  | None = id
        self.media_type: str | None = media_type
        self.fallback: str | None = fallback
        media_overlay: str | None = media_overlay
        self.properties: str | None = properties
        self.content: bytes | None = None

    def __str__(self):
        return str(f"Item: href =\"{self.href}\" id =\"{self.id}\" media-type=\"{self.media_type}\" properties=\"{properties}\"")


class Package:

    opf_namespace = "http://www.idpf.org/2007/opf"

    def __init__(self, tree: etree.ElementTree | None = None):
        self.root = None
        self.tree = tree


        self.metadata = None
        self.manifest: dict[str, Manifest_Item] | None = None
        self.spine = None
        self.guide = None

        if self.tree is not None:
            self.root = self.tree.getroot()

            tag = etree.QName(self.root.tag)
            if tag.namespace != self.opf_namespace:
                raise Namespace_Exception(f"OPF package namespace is incorrect: \"{tag.namespace}\", expected \"{self.opf_namespace}\"")
            if tag.localname != "package":
                raise Unexpected_Element_Exception(f"Unexpected element: \"{tag.localname}\", expected \"package\"")


            print(self.root.tag)
            print(self.root.attrib)
            for child in self.root:
                """ Should see children in this order:
                In this order:
                    metadata [exactly 1]
                    manifest [exactly 1]
                    spine [exactly 1]
                    guide [0 or 1] (legacy)
                    bindings [0 or 1] (deprecated)
                    collection [0 or more]
                """
                if child.tag == "{%s}metadata" % self.opf_namespace:
                    print("metadata")
                    print(child.attrib)
                elif child.tag == "{%s}manifest" % self.opf_namespace:
                    print("manifest")
                    self.manifest = self._parse_manifest(child)
                elif child.tag == "{%s}spine" % self.opf_namespace:
                    print("spine")
                elif child.tag == "{%s}guide" % self.opf_namespace:
                    print("guide")
                elif child.tag == "{%s}bindings" % self.opf_namespace:
                    raise Unsupported_Feature_EXception("binding in a package element not supported yet!")
                elif child.tag == "{%s}collection" % self.opf_namespace:
                    raise Unsupported_Feature_EXception("collection in a package element not supported yet!")
                else:
                    raise Unexpected_Element_Exception(f"Unexpected element: \"{child.tag}\"")

    def _parse_manifest(self, element):
        manifest = {}
        for child in element:
            href = child.attrib.get("href")
            id = child.attrib.get("id")
            media_type = child.attrib.get("media-type")
            fallback = child.attrib.get("fallback")
            media_overlay = child.attrib.get("media-overlay")
            properties = child.attrib.get("properties")
            
            manifest[id] = Manifest_Item(href=href, id=id, media_type=media_type, 
                                         fallback=fallback,
                                         media_overlay=media_overlay,
                                         properties=properties
                                         )

        for item in manifest:
            print(item)
        return manifest



class EPub_Reader:

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.archive = None

    def __enter__(self):
        self.archive = zipfile.ZipFile(self.file_path, 'r')
        self.root_path = self._get_root_path()
        print("root_path: " + str(self.root_path))
        self.package: Package = self._read_package()
        #print(self.package_xml)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.archive:
            self.archive.close()

    def _read_package(self):
        with self.archive.open(self.root_path) as xml_file:
            return Package(tree=etree.parse(xml_file))



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
                    