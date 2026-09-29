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


opf_namespace = "http://www.idpf.org/2007/opf"

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
        return str(f"Item: href =\"{self.href}\" id =\"{self.id}\" media-type=\"{self.media_type}\" properties=\"{self.properties}\"")

class Manifest:

   
    def __init__(self, element: etree.ElementTree):
        self.id: str  | None = element.get("id")

        self.items = {}
        for child in element:
            if child.tag != "{%s}item"  % opf_namespace:
                raise Unexpected_Element_Exception(f"Unexpected element: \"{child.tag}\", expected \"item\"")
            href = child.attrib.get("href")
            id = child.attrib.get("id")
            media_type = child.attrib.get("media-type")
            fallback = child.attrib.get("fallback")
            media_overlay = child.attrib.get("media-overlay")
            properties = child.attrib.get("properties")
            
            self.items[id] = Manifest_Item(href=href, id=id, media_type=media_type, 
                                         fallback=fallback,
                                         media_overlay=media_overlay,
                                         properties=properties
                                         )

        for item in self.items.values():
            print(f"Manifest item: {item}")



    def __str__(self):
        return str(f"Item: href =\"{self.href}\" id =\"{self.id}\" media-type=\"{self.media_type}\" properties=\"{properties}\"")


class Spine:

   
    def __init__(self, element: etree.ElementTree):
        self.id: str  | None = element.get("id")
        self.page_progression_direction: str  | None = element.get("page-progression-direction")
        self.toc: str  | None = element.get("toc")

        self.idrefs = []
        for child in element:
            if child.tag != "{%s}itemref" % opf_namespace:
                raise Unexpected_Element_Exception(f"Unexpected element: \"{child.tag}\", expected \"itemref\"")
            idref = child.attrib.get("idref")
            self.idrefs.append(idref)

        for item in self.idrefs:
            print(f"Spine item: {item}")


    def __str__(self):
        return str(f"Item: href =\"{self.href}\" id =\"{self.id}\" media-type=\"{self.media_type}\" properties=\"{properties}\"")


class Guide:

    # This is only for legacy EPub2, but mamny epub3 files contain a guide.
    """
        There may be one guide element, containing one or more reference elements.
        The guide element identifies fundamental structural components of the publication, to enable Reading Systems to provide convenient access to them.

        For example:
        <guide>
                <reference type="toc" title="Table of Contents" href="toc.html" />
                <reference type="loi" title="List Of Illustrations" href="toc.html#figures" />
                <reference type="other.intro" title="Introduction" href="intro.html" />
        </guide>
    """

   
    def __init__(self, element: etree.ElementTree):
        self.attribs: dict  | None = element.attribs()

        self.refs = []
        for child in element:
            if child.tag != "{%s}reference" % opf_namespace:
                raise Unexpected_Element_Exception(f"Unexpected element: \"{child.tag}\", expected \"reference\"")
            self.idrefs.append(child.attribs)

        for item in self.refs:
            print(f"Guide item: {item}")


    def __str__(self):
        return str(f"Item: href =\"{self.href}\" id =\"{self.id}\" media-type=\"{self.media_type}\" properties=\"{properties}\"")




class Package:

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
            if tag.namespace != opf_namespace:
                raise Namespace_Exception(f"OPF package namespace is incorrect: \"{tag.namespace}\", expected \"{opf_namespace}\"")
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
                if child.tag == "{%s}metadata" % opf_namespace:
                    print("metadata")
                    print(child.attrib)
                elif child.tag == "{%s}manifest" % opf_namespace:
                    print("manifest")
                    self.manifest = Manifest(child)
                elif child.tag == "{%s}spine" % opf_namespace:
                    self.spine = Spine(child)
                elif child.tag == "{%s}guide" % opf_namespace:
                    print("guide")
                elif child.tag == "{%s}bindings" % opf_namespace:
                    raise Unsupported_Feature_EXception("binding in a package element not supported yet!")
                elif child.tag == "{%s}collection" % opf_namespace:
                    raise Unsupported_Feature_EXception("collection in a package element not supported yet!")
                else:
                    raise Unexpected_Element_Exception(f"Unexpected element: \"{child.tag}\"")




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
                    