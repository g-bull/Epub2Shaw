# SPDX-FileCopyrightText: 2026 Geoff Bull
# SPDX-License-Identifier: MIT

from bs4 import BeautifulSoup, NavigableString, Comment
from Transliterators import Transliterator

def html2shaw(xhtml_content: str, transliterator: Transliterator):
    
    # Extract and save the header
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
        string=lambda text: (text.parent 
                             and text.parent.get('epub:type') != 'z3998:ordinal z3998:roman' 
                             and text.parent.get('lang') != 'fr' 
                             and text.parent.get('lang') != 'la')
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

    return xml_header + str(soup)