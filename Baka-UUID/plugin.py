#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, uuid
import sigil_bs4

plugin_name = 'Baka-UUID'
plugin_version = '0.1'
plugin_path = ''

text_type = str


def run(bk):
	# get python plugin path
	global plugin_path
	plugin_path = os.path.join(bk._w.plugin_dir, plugin_name)

	BookId = newIdentifierInMetadata(bk)
	editIdentifierInToC(bk, BookId)

	print('Done.')
	return 0


def newIdentifierInMetadata(bk):
	metadata_xml = bk.getmetadataxml()
	metadata_soup = sigil_bs4.BeautifulSoup(metadata_xml, 'xml')
	metadata_node = metadata_soup.find('metadata')

	# remove the old identifier
	for node in metadata_node.find_all('identifier'):
		if node.get('id') == "BookId":
			node.decompose()

	# print('Creating a new BookID.')
	BookId = uuid.uuid4().urn
	id_node = metadata_soup.new_tag('dc:identifier')
	id_node['id'] = "BookId"
	id_node['opf:scheme'] = "UUID"
	id_node.string = BookId
	metadata_node.append(id_node)

	print('Setting metadata: %s' % id_node)

	bk.setmetadataxml(str(metadata_soup))

	return BookId


def editIdentifierInToC(bk, BookId):
	# read toc file contents
	tocManifestId = bk.gettocid()
	tocXml = bk.readfile(tocManifestId)
	tocSoup = sigil_bs4.BeautifulSoup(tocXml, 'xml')
	metaNode = tocSoup.find('head')

	# change the content of the identifier
	for node in metaNode.find_all('meta'):
		if node.get('name') == "dtb:uid":
			node['content'] = "urn:uuid:%s" % (BookId)
			print('Setting identifier in ToC: %s' % node)

	# write back
	bk.writefile(tocManifestId, tocSoup.prettify())


def main():
	print ("I reached main when I should not have.\n")
	return -1


if __name__ == "__main__":
	sys.exit(main())
