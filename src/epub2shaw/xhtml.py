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
           
def remove_nav_items(xhtml_content, hrefs_to_remove):
    # Use 'xml' parser to maintain XHTML/XML compliance
    soup = BeautifulSoup(xhtml_content, "xml")

    # Find all <li> tags in the document
    for li in soup.find_all('li'):
        # Look for an anchor <a> tag inside the list item
        a_tag = li.find('a')
        
        if a_tag and a_tag.has_attr('href'):
            # If the href value matches any URL in your target list, remove the <li> completely
            if a_tag['href'] in hrefs_to_remove:
                li.decompose()

    return str(soup)                

# ==========================================
# EXAMPLE USAGE
# ==========================================
if __name__ == "__main__":

    # Test XHTML document
    xhtml_input = """<?xml version="1.0" encoding="utf-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en-US" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US">
	<head>
		<title>Table of Contents</title>
	</head>
	<body epub:type="frontmatter">
		<nav aria-labelledby="toc-title" id="toc" role="doc-toc" epub:type="toc">
			<h2 id="toc-title" epub:type="title">Table of Contents</h2>
			<ol>
				<li>
					<a href="text/titlepage.xhtml">Titlepage</a>
				</li>
				<li>
					<a href="text/imprint.xhtml">Imprint</a>
				</li>
				<li>
					<a href="text/chapter-1.xhtml">I: The Science of Deduction</a>
				</li>
				<li>
					<a href="text/chapter-2.xhtml">II: The Statement of the Case</a>
				</li>
				<li>
					<a href="text/chapter-3.xhtml">III: In Quest of a Solution</a>
				</li>
				<li>
					<a href="text/chapter-4.xhtml">IV: The Story of the Bald-Headed Man</a>
				</li>
				<li>
					<a href="text/chapter-5.xhtml">V: The Tragedy of Pondicherry Lodge</a>
				</li>
				<li>
					<a href="text/chapter-6.xhtml">VI: Sherlock Holmes Gives a Demonstration</a>
				</li>
				<li>
					<a href="text/chapter-7.xhtml">VII: The Episode of the Barrel</a>
				</li>
				<li>
					<a href="text/chapter-8.xhtml">VIII: The Baker Street Irregulars</a>
				</li>
				<li>
					<a href="text/chapter-9.xhtml">IX: A Break in the Chain</a>
				</li>
				<li>
					<a href="text/chapter-10.xhtml">X: The End of the Islander</a>
				</li>
				<li>
					<a href="text/chapter-11.xhtml">XI: The Great Agra Treasure</a>
				</li>
				<li>
					<a href="text/chapter-12.xhtml">XII: The Strange Story of Jonathan Small</a>
				</li>
				<li>
					<a href="text/colophon.xhtml">Colophon</a>
				</li>
				<li>
					<a href="text/uncopyright.xhtml">Uncopyright</a>
				</li>
			</ol>
		</nav>
		<nav aria-labelledby="landmarks-title" id="landmarks" epub:type="landmarks">
			<h2 id="landmarks-title" epub:type="title">Landmarks</h2>
			<ol>
				<li>
					<a href="text/titlepage.xhtml" epub:type="frontmatter">Frontmatter</a>
				</li>
				<li>
					<a href="text/chapter-1.xhtml" epub:type="bodymatter">The Sign of the Four</a>
				</li>
			</ol>
		</nav>
	</body>
    </html>
    """

    # For visual check of insertion
    hrefs_to_remove = [ "text/colophon.xhtml", "text/imprint.xhtml", "text/uncopyright.xhtml" ]

    modified_xhtml = remove_nav_items(xhtml_input, hrefs_to_remove)
    print(modified_xhtml)


