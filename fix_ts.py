import xml.etree.ElementTree as ET
import sys
import os

file = sys.argv[1]
tree = ET.parse(file, parser=ET.XMLParser(encoding="utf-8"))
root = tree.getroot()

# pylupdate6 doesn't set locale on creation, make sure it's there
locale = os.path.splitext(os.path.basename(file))[0]
root.set('language', locale)

# Removing line info so updating tr.py affects git history much less
for location in root.findall('.//location'):
    location.set('line', '0')

modified_xml = ET.tostring(root, encoding='utf-8', xml_declaration=False).decode()
with open(file, 'r', encoding='utf-8') as f:
    original_xml = f.read()

# These declarations are hardcoded in pylupdate6, make sure everything is correct
declarations = original_xml.split('\n', 2)[:2]
assert declarations[0] == '<?xml version="1.0" encoding="utf-8"?>', 'xml format has changed'
assert declarations[1] == '<!DOCTYPE TS>', 'doctype format has changed'
final_xml = '\n'.join(declarations) + '\n' + modified_xml + '\n'

with open(file, 'w', encoding='utf-8') as f:
    f.write(final_xml)