import spacy
from bs4 import BeautifulSoup, NavigableString

import copy

# Load the spaCy English language model
# Make sure you run 'python -m spacy download en_core_web_sm' first
nlp = spacy.load("en_core_web_sm")

def add_element_after_sentences(xhtml_content, element_to_insert):
    """
    Parses XHTML and inserts a copy of element_to_insert after every sentence
    found within text nodes.
    """
    # Use 'xml' parser to maintain XHTML/XML compliance
    soup = BeautifulSoup(xhtml_content, "xml")
    
    # Extract block elements that might contain sentences
    # Avoid splitting text inside structural elements like <script>, <style>, or <link>
    text_nodes = [
        node for node in soup.find_all(string=True)
        if node.parent.name not in ['script', 'style', 'head'] and node.strip()
    ]
    
    for node in text_nodes:
        parent = node.parent
        text_content = str(node)
        
        # Use spaCy to analyze the sentences in the current text block
        doc = nlp(text_content)

        for sent in reversed(list(doc.sents)):
            new_element = copy.copy(BeautifulSoup(element_to_insert, "xml"))
            node.insert_after(new_element)
            node.insert_after(text_content[sent.start_char:sent.end_char])

        node.replace_with("") # remove the old node

    return str(soup)                
           


# ==========================================
# EXAMPLE USAGE
# ==========================================
if __name__ == "__main__":

    # Test XHTML document
    xhtml_input = """<?xml version="1.0" encoding="UTF-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en-US" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US">
            <head>
                <link href="../css/core.css" rel="stylesheet" type="text/css"/>
                <link href="../css/local.css" rel="stylesheet" type="text/css"/>
            </head>
            <body epub:type="bodymatter z3998:fiction">
                <section id="chapter-3" role="doc-chapter" epub:type="chapter">
        <div>
            <p>This is the first sentence. “Major Sholto was a very particular friend of papa’s,” she said. He introduced Mr. Sherlock Holmes. This is the second sentence! Here is a third one.</p>
            <p>Another paragraph starts here. Does it catch questions? Yes, it does.</p>
        </div>
                </section>
    </body>
    </html>"""

    # For visual check of insertion
    element_to_insert = '<span style="color: green; margin-left: 5px;"> [XXX] </span>'

    modified_xhtml = add_element_after_sentences(xhtml_input, element_to_insert)
    print(modified_xhtml)


