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

# Check if arguments were passed
if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} config_filename")
    exit(1)

config_filename = sys.argv[1]

with open("config.toml", "rb") as f:
    config_toml = resources.files("epub2shaw.data").joinpath("config.toml").read_text(encoding="utf-8")
    config = tomllib.load(config_toml)

with open(config_filename, "rb") as f:
    config |= tomllib.load(f)

readlex_dict_json = resources.files("epub2shaw.data.readlex").joinpath("readlex_converter.json").read_text(encoding="utf-8")
readlex_dict: dict[str, list[dict[str, str]]] = json.loads(readlex_dict_json)

if "book" in config and ("words_filename" in config["book"]):
    with open(config["book"]["words_filename"], 'r', encoding="utf-8") as file:
        json_data = file.read()
        extra_dict: dict[str, list[dict[str, str]]] = json.loads(json_data)
        readlex_dict |= extra_dict

with resources.files("epub2shaw.data.readlex").joinpath("readlex_converter_phrases.json").open(mode="r", encoding="utf-8", newline="") as f:
    csv_reader = csv.reader(f)
    phrases = [row[0] for row in csv_reader if row]

if "book" in config and ("phrases_filename" in config["book"]):
    with open(config["book"]["phrases_filename"], "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        phrases += [row[0] for row in reader if row]


if ("book" not in config) or ("input_filename" not in config["book"]):
    print("Input file not specified")
    exit(1)

input_filename = config["book"]["input_filename"]

input_path = Path(input_filename)

if not input_path.exists():
    print("Input file doesn't exist: " + input_filename)
    exit(1)

if not input_path.is_file():
    print("Input file must be must a file: " + input_filename)
    exit(1)

if not (input_path.suffix == '.epub'):
    print("Input file must be must an epub file: " + input_filename)
    exit(1)

if "output_dir" not in config["book"]:
    print("Output directory not specified.")
    exit(1)

output_dir = config["book"]["output_dir"]
output_dir_path = Path(output_dir)

if not output_dir_path.exists():
    print("Output directory doesn't exist: " + output_dir)
    exit(1)

if not output_dir_path.is_dir():
    print("Output director must be must a directory: " + output_dir)
    exit(1)

output_basename_suffix = config["default"]["output_basename_suffix"]
output_file = output_dir + "/" + input_path.stem + output_basename_suffix + ".epub"

transliterator = Transliterator(readlex_dict, phrases)

with zipfile.ZipFile(input_filename, "r") as input_epub:

    output_buffer = io.BytesIO()

    with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as output_epub:
    
        for item in input_epub.infolist():
            if not item.filename.endswith(".xhtml"):
                # just copy not HTML files to new epub
                output_epub.writestr(item, input_epub.read(item.filename))
            else:
                # Transliterate HTML files before writing them
                print(item.filename)
                with input_epub.open(item.filename) as binary_file:
                    # Decode bytes into a text stream
                    with io.TextIOWrapper(binary_file, encoding='utf-8') as text_file:
                        xhtml_content = text_file.read()

                transliterated_content = html2shaw(xhtml_content, transliterator)
                output_epub.writestr(item.filename, transliterated_content)

    with open(output_file, 'wb') as f:
        f.write(output_buffer.getvalue())
            

    constructed_words = transliterator.get_constructed_words()
    if len(constructed_words) > 0:
        print("Constructed words:")
        for word, transliteration in constructed_words.items():
            print("    " + word + "  ->  " + transliteration)
        print()

    unknown_words = transliterator.get_unknown_words()
    if len(unknown_words) > 0:
        print("Unknown words:")
        for word in unknown_words.keys():
            print("    " + word)
        print()
        
    print("HTML translation complete!")

