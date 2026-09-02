# SPDX-FileCopyrightText: 2026 Geoff Bull
# SPDX-License-Identifier: MIT

import json
import csv
import sys
import tomllib


from Transliterators import Transliterator
from html2shaw import html2shaw

# Check if arguments were passed
if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} config_filename")
    exit(1)

config_filename = sys.argv[1]

with open("config.toml", "rb") as f:
    config = tomllib.load(f)

with open(config_filename, "rb") as f:
    config |= tomllib.load(f)

with open(config["default"]["words_filename"], 'r', encoding="utf-8") as file:
    json_data = file.read()    
    readlex_dict: dict[str, list[dict[str, str]]] = json.loads(json_data)

if "book" in config and ("words_filename" in config["book"]):
    with open(config["book"]["words_filename"], 'r', encoding="utf-8") as file:
        json_data = file.read()
        extra_dict: dict[str, list[dict[str, str]]] = json.loads(json_data)
        readlex_dict |= extra_dict

with open(config["default"]["phrases_filename"], "r", newline="") as f:
    reader = csv.reader(f)
    phrases = [row[0] for row in reader if row]

if "book" in config and ("phrases_filename" in config["book"]):
    with open(config["book"]["phrases_filename"], "r", newline="") as f:
        reader = csv.reader(f)
        phrases += [row[0] for row in reader if row]


transliterator = Transliterator(readlex_dict, phrases)

if "book" in config and ("input_filename" in config["book"]):
    # for now assume config["book"]["format"] == "HTML"

    input_filename = config["book"]["input_filename"]


    # 1. Load your local HTML file
    with open(input_filename, "r", encoding="utf-8") as f:
        print(input_filename)
        xhtml_content = f.read()

    transliterated_content = html2shaw(xhtml_content, transliterator)

    # Save the transliterated HTML
    if "output_filename" in config["book"]:
        with open(config["book"]["output_filename"], "w", encoding="utf-8") as f:
            f.write(transliterated_content)

    constructed_words = transliterator.get_constructed_words()
    if len(constructed_words) > 0:
        print("Constructed words from " + config["book"]["output_filename"] + ":")
        for word, transliteration in constructed_words.items():
            print("    " + word + "  ->  " + transliteration)
        print()

    unknown_words = transliterator.get_unknown_words()
    if len(unknown_words) > 0:
        print("Unknown words in " + config["book"]["output_filename"] + ":")
        for word in unknown_words.keys():
            print("    " + word)
        print()
        
    print("HTML translation complete!")


