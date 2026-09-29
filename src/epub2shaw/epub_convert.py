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


from .Transliterators import Transliterator
from .html2shaw import html2shaw
from .epub3 import EPub_Reader

def main():

    # Check if arguments were passed
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} config_filename")
        exit(1)

    config_filename = sys.argv[1]

    config_toml = resources.files("epub2shaw.data").joinpath("config.toml").read_text(encoding="utf-8")
    config = tomllib.loads(config_toml)

    with open(config_filename, "rb") as f:
        config |= tomllib.load(f)

    # file paths in the config file are relative to the directory containing the config file.
    config_dir = Path(config_filename).parent

    readlex_dict_json = resources.files("epub2shaw.data.readlex").joinpath("readlex_converter.json").read_text(encoding="utf-8")
    readlex_dict: dict[str, list[dict[str, str]]] = json.loads(readlex_dict_json)

    if "book" in config and ("words_filename" in config["book"]):

        custom_words_filename = config_dir.joinpath(config["book"]["words_filename"])
        print(custom_words_filename)
        with open(custom_words_filename, 'r', encoding="utf-8") as file:
            json_data = file.read()
            extra_dict: dict[str, list[dict[str, str]]] = json.loads(json_data)
            readlex_dict |= extra_dict

    with resources.files("epub2shaw.data.readlex").joinpath("readlex_converter_phrases.json").open(mode="r", encoding="utf-8", newline="") as f:
        csv_reader = csv.reader(f)
        phrases = [row[0] for row in csv_reader if row]

    if "book" in config and ("phrases_filename" in config["book"]):
        custom_phrases_filename = config_dir.joinpath(config["book"]["phrases_filename"])
        with open(custom_phrases_filename, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            phrases += [row[0] for row in reader if row]


    if ("book" not in config) or ("input_filename" not in config["book"]):
        print("Input file not specified")
        exit(1)

    input_path = config_dir.joinpath(config["book"]["input_filename"])


    if not input_path.exists():
        print(f"Input file doesn't exist: {input_path}")
        exit(1)

    if not input_path.is_file():
        print(f"Input file must be must a file: {input_path}")
        exit(1)

    if not (input_path.suffix == '.epub'):
        print(f"Input file must be must an epub file: {input_path}")
        exit(1)

    if "output_dir" not in config["book"]:
        print("Output directory not specified.")
        exit(1)

    output_dir = config_dir.joinpath(config["book"]["output_dir"])

    if not output_dir.exists():
        print(f"Output directory doesn't exist: {output_dir}")
        exit(1)

    if not output_dir.is_dir():
        print(f"Output director must be must a directory: {output_dir}")
        exit(1)

    output_basename_suffix = config["default"]["output_basename_suffix"]
    output_file = output_dir.joinpath(input_path.stem + output_basename_suffix + ".epub")

    transliterator = Transliterator(readlex_dict, phrases)

    with EPub_Reader(input_path) as reader:
        items = reader.item_list()

        output_buffer = io.BytesIO()

        with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as output_epub:

            # write the mimetype tpo the archive
            output_epub.writestr("mimetype", "application/epub+zip\n")

            container_filename = "META-INF/container.xml"

            container_xml = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
                <rootfiles>
                    <rootfile full-path="{reader.root_path}" media-type="application/oebps-package+xml"/>
                </rootfiles>
            </container>
            """
            output_epub.writestr(container_filename, container_xml)
            output_epub.writestr(reader.root_path, reader.read_file(reader.root_path))


            for item in items:
                id = item["id"]
                href = item["href"]
                epub_path = (reader.root_dir.joinpath(href)).as_posix() 

                data = reader.get_data(id)
                #data  = self.archive.read(epub_path)

                if not epub_path.endswith(".xhtml"):
                    # just copy not HTML files to new epub
                    print(f"not-HTML file {epub_path}")
                    #data = input_epub.read(filename)
                    output_epub.writestr(epub_path, data)
                else:
                    # Transliterate HTML files before writing them
                    print(f"Transliterating: \"{epub_path}\"")
                    xhtml_content = data.decode('utf-8')

                    transliterated_content = html2shaw(xhtml_content, transliterator)
                    output_epub.writestr(epub_path, transliterated_content)

        with open(output_file, 'wb') as f:
            f.write(output_buffer.getvalue())

        """
        for d in ["fonts", "css" ]:
                res_dir = resources.files("epub2shaw.data").joinpath(d)
                files = [f for f in res_dir.iterdir() if f.is_file()]
                for file in files:
                    print(file)
        """       

        constructed_words = transliterator.get_constructed_words()
        #if len(constructed_words) > 0:
        #    print("Constructed words:")
        #    for word, transliteration in constructed_words.items():
        #        print("    " + word + "  ->  " + transliteration)
        #    print()

        unknown_words = transliterator.get_unknown_words()
        #if len(unknown_words) > 0:
        #    print("Unknown words:")
        #    for word in unknown_words.keys():
        #        print("    " + word)
        #    print()
        #    
        #print("HTML translation complete!")

        unsorted_words = unknown_words | constructed_words
        sorted_words = {k: [{ "Shaw" : unsorted_words[k], "tag" : "0"}] for k in sorted(unsorted_words)}

        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(sorted_words, f, indent=4, sort_keys=True, ensure_ascii=False)
        
        #if len(sorted_words) > 0:
        #    print("Unknown words:")
        #    for key, value in sorted_words.items():
        #        print("    " + str(key) + "  ->  " + str(value))
        #    print()
            
        print("HTML translation complete!")

