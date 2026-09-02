import json
import csv
import sys
import tomllib

from bs4 import BeautifulSoup, NavigableString, Comment

from Transliterators import Transliterator

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

    # 1. Extract and save the header
    xml_header = ""
    if xhtml_content.startswith("<?xml"):
        parts = xhtml_content.split("?>", 1)
        xml_header = parts[0] + "?>\n"  # Save the header string
        xhtml_content = parts[1].strip()

    soup = BeautifulSoup(xhtml_content, "html.parser")

    # Define tags that should NEVER have their text contents translated
    SKIPPED_TAGS = {"script", "style", "meta", "head", "title"}

    # Iterate through all text nodes in the document tree
    # Skip deliniated roman numerals
    for text_node in soup.find_all(
        string=lambda text: (text.parent and text.parent.get('epub:type') != 'z3998:ordinal z3998:roman')
        ):

        # Skip comments
        if isinstance(text_node, Comment):
            continue
            
        # Skip text nodes that belong to code, styling, or metadata containers
        if text_node.parent.name in SKIPPED_TAGS:
            continue

        # Clean up the string to evaluate if it contains actual translatable text
        clean_text = text_node.strip()
        if not clean_text:
            continue  # Skips structural whitespace/newlines

        try:
            # Transliterate the text fragment
            translated_text = transliterator.transliterate(clean_text)
            
            # Replace the original node content with the transliterated version
            # Using .replace_with() keeps the exact HTML structure intact
            text_node.replace_with(NavigableString(translated_text))
        except Exception as e:
            print(f"Skipped transliterating '{clean_text}' due to error: {e}")

    # 5. Save the modified, fully translated HTML structure
    if "output_filename" in config["book"]:
        with open(config["book"]["output_filename"], "w", encoding="utf-8") as f:
            f.write(xml_header + str(soup))

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


