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
dc_namespace = "http://purl.org/dc/elements/1.1/"

namespaces = {
    'opf':      "http://www.idpf.org/2007/opf",
    'dc':       "http://purl.org/dc/elements/1.1/"
}
for ns in namespaces:
    etree.register_namespace(ns, namespaces[ns])

opf_tag = { tag : f"{{{opf_namespace}}}{tag}" for tag in [
    "package", 
    "metadata",
    "meta",
    "link",
    "manifest",
    "item",
    "spine",
    "itemref",
    "guide",
    "reference",
    "bindings",
    "collection"]
}

dc_tag = { tag : f"{{{dc_namespace}}}{tag}" for tag in [
    #mandatory:
    "identifier", 
    "language",
    "title",
    #optional:
    "contributor",
    "coverage",
    "creator"
    "date",
    "description",
    "format",
    "publisher",
    "relation ",
    "rights",
    "source",
    "subject",
    "type"]
}


#class Package:
class Epub3_Exception(Exception):
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

class Metadata_Item:
    """
    The meta element provides a generic means of including package metadata.
    Usage:    As child of the metadata element. Repeatable.

    Attributes:
        dir [optional]
        id [optional]
        property [required]
        refines [optional]
        scheme [optional]
        xml:lang [optional]

    Content Model: Text    
    """
   
    def __init__(self, element: etree.ElementTree):
        self.tag = element.tag
        self.attrs = element.attrib
        self.text = element.text
    
    def to_xml(self, parent: etree.Element):
        element = etree.SubElement(parent, self.tag)
        for key in self.attrs:
            element.set(key, self.attrs[key])

        element.text = self.text
        

class Metadata:
    """
    The metadata element encapsulates meta information.
    REQUIRED first child of package.

    Attributes:None

    Content Model: (In any order)
        dc:identifier [1 or more]
        dc:title [1 or more]
        dc:language [1 or more]
        Dublin Core Optional Elements [0 or more]
        meta [1 or more]
        OPF2 meta [0 or more] (legacy)
        link [0 or more]
    """
   
    def __init__(self, element: etree.ElementTree):

        self.attrs = element.attrib
        self.items = []
        for child in element:
            self.items.append(Metadata_Item(child))


    def to_xml(self, parent: etree.Element):
        nsmap = {'dc': dc_namespace}
        element = etree.SubElement(parent, "metadata", nsmap=nsmap)
        for key in self.attrs:
            element.set(key, self.attrs[key])

        for item in self.items:
            item.to_xml(element)
        
class Manifest_Item:
   
    def __init__(self, attrs: dict[str, str]):
        self.attrs = attrs
        self.data: bytes | None = None

    def __str__(self):
        return str(f"Item: href =\"{self.href}\" id =\"{self.id}\" media-type=\"{self.media_type}\" properties=\"{self.properties}\"")

    def set_data(self, data: bytes):
        self.data = data

    def get_data(self):
        return self.data

    def get_attrs(self):
        return self.attrs

    def to_xml(self, parent: etree.Element):
        element = etree.SubElement(parent, "item")
        for key in self.attrs:
            element.set(key, self.attrs[key])
        

    
class Manifest:

   
    def __init__(self, element: etree.Element):
        self.attrs: dict = element.attrib

        self.items = {}
        for child in element:
            if child.tag != opf_tag["item"]:
                raise Unexpected_Element_Exception(f"Unexpected element: \"{child.tag}\", expected \"{opf_tag["item"]}\"")

            id = child.get("id")
            self.items[id] = Manifest_Item(child.attrib)


    def __str__(self):
        return str(f"Item: href =\"{self.href}\" id =\"{self.id}\" media-type=\"{self.media_type}\" properties=\"{properties}\"")

    def set_data(self, id, data):

        if id in self.items:
            self.items[id].set_data(data)
        else:
            raise Epub3_Exception(f"Failed to set data for non-existent manifest id:: \"{id}\"")

    def get_data(self, id):

        if id in self.items:
            return self.items[id].get_data()
        else:
            raise Epub3_Exception(f"Failed to get data for non-existent manifest id: \"{id}\"")

    def item_list(self):
        return [ self.items[id].get_attrs() for id in self.items]

    def add_item(self, id: str, href: str, media_type: str, replace: bool = False):
        if id not in self.items:
            self.items[id] = Manifest_Item({"href" : href,
                                            "id" : id,
                                            "media-type" : media_type})
        elif replace:
            self.items[id] = Manifest_Item({"href" : href,
                                            "id" : id,
                                            "media-type" : media_type})
        else:
            raise Epub3_Exception(f"Attempted to add non-unique id to the manifest: \"{id}\"")

    def remove_item(self, id : str):
        self.items.pop(id, None) # Don't raise KeyError if id not in dictionary

    def id_of_href(self, href: str) -> str | None:
        items_ = self.item_list()
        for item_ in items_:
            if item_["href"] == href:
                return item_["id"]
        return None


    def to_xml(self, parent: etree.Element):
        element = etree.SubElement(parent, "manifest")
        for key in self.attrs:
            element.set(key, self.attrs[key])

        for id in self.items:
            self.items[id].to_xml(element)
        

class Spine:

   
    def __init__(self, element: etree.Element):
        self.attrs = element.attrib

        self.idrefs = []
        for child in element:
            if child.tag != opf_tag["itemref"]:
                raise Unexpected_Element_Exception(f"Unexpected element: \"{child.tag}\", expected \"{opf_tag["itemref"]}\"")
            idref = child.attrib.get("idref")
            self.idrefs.append(idref)

    def __str__(self):
        return str(f"Spinre: id =\"{self.id}\" page-progression-direction=\"{self.page_progression_direction}\" tov=\"{self.toc}\"")

    def remove_item(self, id : str):
        self.idrefs = [ idref for idref in self.idrefs if idref != id]

    def to_xml(self, parent: etree.Element):
        element = etree.SubElement(parent, "spine")
        for key in self.attrs:
            element.set(key, self.attrs[key])

        for idref in self.idrefs:
            child = etree.Element(opf_tag["itemref"])
            child.set("idref", idref)
            element.append(child)
        


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

   
    def __init__(self, element: etree.Element):
        self.attrs: dict = element.attrib

        self.refs = []
        for child in element:
            if child.tag != opf_tag["reference"]:
                raise Unexpected_Element_Exception(f"Unexpected element: \"{child.tag}\", expected \"{opf_tag["reference"]}\"")
            self.refs.append(child.attrib)


    def __str__(self):
        return str(f"Item: href =\"{self.href}\" id =\"{self.id}\" media-type=\"{self.media_type}\" properties=\"{properties}\"")

    def to_xml(self, parent: etree.Element):
        element = etree.SubElement(parent, "guide")
        for key in self.attrs:
            element.set(key, self.attrs[key])

        for ref in self.refs:
            child = etree.Element(opf_tag["reference"])
            for key in ref:
                child.set(key, ref[key])
            element.append(child)
        

class Package:
    """
    The package element encapsulates all the information expressed in the package document.
    Usage: REQUIRED root element [xml] of the package document.

    Attributes:
        dir [optional]
        id [optional]
        prefix [optional]
        xml:lang [optional]
        unique-identifier [required]
        version [required]

    Content Model: (in this order)
        metadata [exactly 1]
        manifest [exactly 1]
        spine [exactly 1]
        guide [0 or 1] (legacy)
        bindings [0 or 1] (deprecated)
        collection [0 or more]
    """

    def __init__(self, tree: etree.ElementTree | None = None):
        self.root = None
        self.tree = tree
        self.attrs = None



        self.metadata = None
        self.manifest: Manifest | None = None
        self.spine = None
        self.guide = None

        if self.tree is not None:
            self.root = self.tree.getroot()

            if self.root.tag != opf_tag["package"]:
                raise Unexpected_Element_Exception(f"Unexpected element: \"{self.root.tag}\", expected \"{opf_tag["package"]}\"")

            self.attrs = self.root.attrib
            for child in self.root:
                if child.tag == opf_tag["metadata"]:
                    self.metadata = Metadata(child)
                elif child.tag == opf_tag["manifest"]:
                    self.manifest = Manifest(child)
                elif child.tag == opf_tag["spine"]:
                    self.spine = Spine(child)
                elif child.tag == opf_tag["guide"]:
                    self.guide = Guide(child)
                elif child.tag == opf_tag["bindings"]:
                    raise Unsupported_Feature_EXception("binding in a package element not supported yet!")
                elif child.tag == opf_tag["collection"]:
                    raise Unsupported_Feature_EXception("collection in a package element not supported yet!")
                else:
                    raise Unexpected_Element_Exception(f"Unexpected element: \"{child.tag}\"")

    def item_list(self):
        return self.manifest.item_list()

    def set_data(self, id: str, data: bytes):
        self.manifest.set_data(id, data)

    def get_data(self, id: str):
        return self.manifest.get_data(id)

    def add_item(self, id: str, href: str, media_type: str, replace: bool = False):
        self.manifest.add_item(id=id, href=href, media_type=media_type, replace=replace)

    def remove_item(self, id: str):
        self.manifest.remove_item(id=id)
        self.spine.remove_item(id=id)

    def id_of_href(self, href: str) -> str | None:
        return self.manifest.id_of_href(href)

    def to_xml(self) -> bytes:
        nsmap = {None: opf_namespace}
        element = etree.Element(opf_tag["package"], nsmap=nsmap)
        if self.attrs is not None:
            for key in self.attrs:
                element.set(key, self.attrs[key])
        self.metadata.to_xml(element)
        self.manifest.to_xml(element)
        self.spine.to_xml(element)
        self.guide.to_xml(element)
        etree.cleanup_namespaces(element)

        xml_data = etree.tostring(element, xml_declaration=True, encoding="UTF-8", pretty_print=True)

        tree = etree.ElementTree(element)
        tree.write("output.xml", xml_declaration=True, encoding="UTF-8", pretty_print=True)    
        return xml_data


class EPub_Writer:

    def __init__(self, file_path: str, root_path: str = 'document/content.opf'):
        self.file_path = file_path
        self.archive = None
        self.root_path = root_path
        self.root_dir = Path(self.root_path).parent

    def __enter__(self):
        
        self.output_buffer = io.BytesIO()
        self.archive = zipfile.ZipFile(self.output_buffer, mode="w", compression=zipfile.ZIP_DEFLATED)


        container_filename = "META-INF/container.xml"

        container_xml = f"""<?xml version="1.0" encoding="utf-8"?>
        <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
            <rootfiles>
                <rootfile full-path="{self.root_path}" media-type="application/oebps-package+xml"/>
            </rootfiles>
        </container>
        """
        self.archive.writestr(container_filename, container_xml)

        self.archive.writestr("mimetype", b"application/epub+zip")

        return self

    def write_package(self, pkg: Package):
        
        self.archive.writestr(self.root_path, pkg.to_xml())


        items = pkg.item_list()

        for item in items:
            id = item["id"]
            href = item["href"]

            epub_path = (self.root_dir.joinpath(href)).as_posix() 

            data = pkg.get_data(id)
            self.archive.writestr(epub_path, data)

    #def write_rootfile(self, xml : str):
    #    self.archive.writestr(self.root_path, xml.encode('utf-8'))

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.archive:

            self.archive.close()

            with open(self.file_path, 'wb') as f:
                f.write(self.output_buffer.getvalue())


class EPub_Reader:

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.archive = None

    def __enter__(self):
        self.archive = zipfile.ZipFile(self.file_path, 'r')
        self.root_path = self._get_root_path()
        self.root_dir = Path(self.root_path).parent
        self.package: Package = self._read_package()

        # Retrieve the archivew data according to the manifest.
        items = self.package.item_list()
        for item in items:
            id = item["id"]
            href = item["href"]
            epub_path = (self.root_dir.joinpath(href)).as_posix() 
            data  = self.archive.read(epub_path)
            self.package.set_data(id, data) 

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.archive:
            self.archive.close()

    # Temporary since we can't  generate a opf file yet
    def read_file(self, path):
        return self.archive.read(path)

    def item_list(self):
        return self.package.item_list()

    def get_data(self, id: str):
        return self.package.get_data(id)
    
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
        raise Epub3_Exception("Couldn't retrieve the rootfile path from META-INF/container.xml.")            