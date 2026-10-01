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
from .epub3 import EPub_Reader, EPub_Writer

from bs4 import BeautifulSoup

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
        #print(custom_words_filename)
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

    pkg = None
    with EPub_Reader(input_path) as reader:
        pkg = reader.package

    # Add custom fonts and styles to the epub package.
    for d in ["fonts", "css" ]:
        res_dir = resources.files("epub2shaw.data").joinpath(d)
        parent = res_dir.parent.as_posix()

        filenames = [f for f in res_dir.iterdir() if f.is_file()]
        css_hrefs = []  # collect lits of css files for which links will need to e added head element of each html file.
        for filename in filenames:
            epub_href = str(filename.as_posix()).removeprefix(str(parent) + '/')

            # XML ID data type must start with a letter or underscore,
            # containing only letters, digits, hyphens, underscores, colons,
            # and periods.
            # Therefore generate a valid id from the href, replace '/' with ':'
            epub_id = epub_href.replace('/', ':')
            # FIXME: check epub_id is unique, and make unique if it isn't

            with open(filename, 'rb') as file:
                data = file.read()
                epub_media_type = None
                if epub_href.endswith('.css'):
                    epub_media_type = 'text/css'
                    css_hrefs.append(epub_href)
                elif epub_href.endswith('.otf'):
                    epub_media_type = 'application/vnd.ms-opentype'
                else:
                    raise Exception(f"Cannot infer media type for \"{epub_href}\".")
                
                pkg.add_item(href = epub_href, id = epub_id, media_type = epub_media_type)
                pkg.set_data(epub_id, data)

    items = pkg.item_list()
    for item in items:
        id = item["id"]
        href = item["href"]

        if item['media-type'] == 'application/xhtml+xml':

            # Transliterate HTML files before writing them
            print(f"Transliterating: \"{href}\"")
            xhtml_content = pkg.get_data(id).decode('utf-8')

            transliterated_content = html2shaw(xhtml_content, transliterator)

            # New links should be appended to the head element, and be of the form:
            #    <link href="../css/new_file.css" rel="stylesheet" type="text/css"/>
            # However the href in the link nedds to be adjusted for the relative location of the html file.
            for css_href in css_hrefs:
                relative_css_href = str(Path('/'+css_href).relative_to(Path('/'+href).parent, walk_up=True).as_posix())
                link_to_insert = f'<link href="{relative_css_href}" rel="stylesheet" type="text/css"/>'
                soup = BeautifulSoup(transliterated_content, "xml")
                if soup.head:
                    soup.head.append(BeautifulSoup(link_to_insert, "xml").find())

                # now change the language to Shavian
                html_tag = soup.find('html')
                if html_tag:
                    # Update or add the attributes
                    html_tag['lang'] = 'en-Shaw'
                    html_tag['xml:lang'] = 'en-Shaw'

                transliterated_content = str(soup)

            pkg.set_data(id, transliterated_content.encode('utf-8'))


    with EPub_Writer(output_file) as writer:
        writer.write_package(pkg)
        

    constructed_words = transliterator.get_constructed_words()
    unknown_words = transliterator.get_unknown_words()
    unsorted_words = unknown_words | constructed_words
    sorted_words = {k: [{ "Shaw" : unsorted_words[k], "tag" : "0"}] for k in sorted(unsorted_words)}

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(sorted_words, f, indent=4, sort_keys=True, ensure_ascii=False)
    
    if len(sorted_words) > 0:
        print(f"{len(sorted_words)} unknown words found.")
        
    print("HTML translation complete!")

