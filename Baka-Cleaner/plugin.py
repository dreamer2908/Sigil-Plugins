#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os, re, codecs, random, string, uuid, io, urllib
import copy
from PIL import Image
from io import BytesIO

try:
	import sigil_bs4
	import sigil_gumbo_bs4_adapter as gumbo_bs4
except:
	import bs4 as sigil_bs4
	import bs4 as gumbo_bs4

plugin_name = 'Baka-Cleaner'
plugin_path = ''
text_type = str

def run(bk):
	# get python plugin path
	global plugin_path
	plugin_path = os.path.join(bk._w.plugin_dir, plugin_name)

	for (textID, textHref) in bk.text_iter():
		if os.path.split(textHref)[1] in ['Cover.xhtml', 'cover.xhtml', 'titlepage.xhtml', 'Section0001.xhtml', 'Illustrations.xhtml']: # main text file is anything but these
			continue
		print('\nProcessing text file: %s' % textHref)

		textContents = bk.readfile(textID) # Read the section into textContents
		if not isinstance(textContents, text_type):	# If the section is not str then sets its type to 'utf-8'
			textContents = text_type(textContents, 'utf-8')

		soup = gumbo_bs4.parse(textContents)

		def reloadSoup():
			nonlocal soup, textContents
			if soup:
				textContents = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(textContents)


		def cleanUpForWordpress():
			nonlocal soup
			# add cleanups for wordpress-based epub
			# - get <h1> from <header class="entry-header">blablah</header> inside <body>
			headingLv = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
			headerNode = soup.body.find("header")
			if headerNode:
				headingTags = headerNode.find_all(headingLv)
				if len(headingTags) > 0:
					del headingTags[0]["class"]
					del headingTags[0]["style"]
					headerNode.replace_with(headingTags[0])
					# clean <body> too
					del soup.body['class']
					del soup.body['style']
			# - unwrap <div class="entry-content">
			# - kill <div class="entry-meta">
			divClassUnwrapMe = ["entry-content", "entry-the-content", "post-entry"]
			divClassRemoveMe = ["entry-meta", "screen-reader-text", "sharedaddy", "wc-comment", "wc-blog-", "comments"]
			deleteMe = []
			for node in soup.body.find_all('div'):
				if node.has_attr('class'):
					if stringContainsAny(node.get('class'), divClassUnwrapMe):
						node.unwrap()
					elif stringContainsAny(node.get('class'), divClassRemoveMe):
						# node.decompose()
						deleteMe.append(node)
			for node in deleteMe:
				node.decompose()
			# - delete <footer>
			for node in soup.find_all(['footer']):
				node.decompose()

			reloadSoup()


		def cleanUpForTruyenFull():
			nonlocal soup

			headingLv = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
			headingTags = soup.body.find_all(headingLv)
			divTags = soup.body.find_all("div", "chapter-c") # WebToEpub note: you need <div class="col-xs-12">

			if len(divTags) > 0:
				textNode = divTags[0].extract()

				headerNode = None
				if len(headingTags) > 0:
					headerNode = headingTags[0].extract()
					del headerNode["class"]
					del headerNode["style"]
					headerNode.string = headerNode.get_text().strip()

				html = soup.serialize_xhtml()
				soup = gumbo_bs4.parse(html)
				for node in soup.body.contents:
					node.extract()

				if headerNode:
					soup.body.append(headerNode)
				soup.body.append(textNode)

				html = soup.serialize_xhtml()
				soup = gumbo_bs4.parse(html)
				# print(len(soup.body.find_all(['a', 'span', 'p'], { 'style':"color:white;font-size:1px;"})))
				# print((soup.body.find_all(lambda tag:tag.has_attr('style') and 'font-size:1px' in tag['style'])))
				# print(len(soup.body.find_all(['a', 'span', 'p'])))
				for node in soup.body.find_all(lambda tag:tag.has_attr('style') and 'font-size:1px' in tag['style']):
					node.decompose()

				html = soup.serialize_xhtml()
				soup = gumbo_bs4.parse(html)
				textNode = soup.body.find("div", "chapter-c")
				# unwrapping the div in a preferrable way
				newTextNode = soup.new_tag('div')
				newTextNode['class'] = "chapter-c"
				# removeMe = []
				previousP = None
				for child in textNode.contents:
					if type(child) == sigil_bs4.element.NavigableString:
						# a lot of unwanted `<p> </p>` line will be created if you wrap everything without checking
						if str(child).strip() != '':
								if previousP:
									previousP.append(copy.copy(child))
								else:
									child = copy.copy(child)
									newTextNode.append(child)
									previousP = child.wrap(soup.new_tag('p'))
						else:
							newTextNode.append(copy.copy(child)) # yes, copy even blank space
					elif type(child) == sigil_bs4.element.Tag:
						if child.name == 'br':
								previousP = None
						elif child.name not in tagsNotAllowedInP:
							# for these, check if they have some contents. skip copying if no
							if (len(child.get_text().strip()) > 0 or len(child.find_all(True)) > 0) or child.has_attr('id') or child.has_attr('name'):
								if previousP:
									previousP.append(copy.copy(child))
								else:
									child = copy.copy(child)
									newTextNode.append(child)
									previousP = child.wrap(soup.new_tag('p'))
						else:
							# stuff not allowed in <p>
							child = copy.copy(child)
							newTextNode.append(child)
				textNode.replace_with(newTextNode)

				html = soup.serialize_xhtml()
				soup = gumbo_bs4.parse(html)
				textNode = soup.body.find("div", "chapter-c")
				textNode.unwrap()


		def splitNodesIntoP(pNodes):
			nonlocal soup

			# level 1:
			#    try to split <p>line 1<br/><br/>line 2<img alt='' src='image.jpg'/>line3</p>
			#    into <p>line 1</p> <p>line 2</p> <p><img alt='' src='image.jpg'/></p> <p>line3</p>
			#    Remember to copy style and class. ID goes to the first p
			# level 2:
			#    into <p>line 1</p> <p></p> <p>line 2</p> <p><img alt='' src='image.jpg'/></p> <p>line3</p>
			# level x:
			#    try to handle <br/> nested inside something else like <p>line 1 <i>italic text<br/>line 2 in italic</i></p>
			#    into <p>line 1 <i>italic text</i></p> <p><i>line 2 in italic</i></p>
			# current at level 2, but empty lines are removed at later stage so it doesn't even matter
			# TODO: copy style, class, id
			unwrapUsID = []
			for textNode in pNodes:
				# for now, we put all new p in a container (and unwrap it later)
				newTextNode = soup.new_tag('div')
				newTextNode_id = 'id-' + str(uuid.uuid4())
				newTextNode['id'] = newTextNode_id
				unwrapUsID.append(newTextNode_id)
				# removeMe = []
				previousP = None
				lastChildWasBr = False
				for child in textNode.contents:
					if type(child) == sigil_bs4.element.NavigableString:
						lastChildWasBr = False
						# a lot of unwanted `<p> </p>` line will be created if you wrap everything without checking
						if str(child).strip() != '':
								if previousP:
									previousP.append(copy.copy(child))
								else:
									child = copy.copy(child)
									newTextNode.append(child)
									previousP = child.wrap(soup.new_tag('p'))
						else:
							newTextNode.append(copy.copy(child)) # yes, copy even blank space

					elif type(child) == sigil_bs4.element.Tag:
						if child.name == 'br':
							if lastChildWasBr:
								newTextNode.append(soup.new_tag('p'))
							lastChildWasBr = True
							previousP = None

						elif child.name == 'img':
							child = copy.copy(child)
							newTextNode.append(child)
							tmpNode = child.wrap(soup.new_tag('div'))
							tmpNode['class'] = "svg_outer svg_inner"
							lastChildWasBr = False
							previousP = None

						elif child.name not in tagsNotAllowedInP:
							lastChildWasBr = False
							# for these, check if they have some contents. skip copying if no
							if (len(child.get_text().strip()) > 0 or len(child.find_all(True)) > 0) or child.has_attr('id') or child.has_attr('name'):
								if previousP:
									previousP.append(copy.copy(child))
								else:
									child = copy.copy(child)
									newTextNode.append(child)
									previousP = child.wrap(soup.new_tag('p'))
						else:
							lastChildWasBr = False
							# stuff not allowed in <p>
							child = copy.copy(child)
							newTextNode.append(child)
				textNode.replace_with(newTextNode)

			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)

			for node in soup.body.find_all('div'):
				if node.get('id') in unwrapUsID:
					node.unwrap()

			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)


		def splitTagtoP(wantedTag):
			nonlocal soup
			pNodes = soup.body.find_all(wantedTag)
			splitNodesIntoP(pNodes)


		def splitPtoP():
			nonlocal soup
			splitTagtoP("p")


		def easyClean1():
			nonlocal soup

			plsWriteBack = False

			# delete all these nodes
			for node in soup.find_all(['style', 'meta', 'input', 'button']):
				node.decompose()
				plsWriteBack = True

			# unwrap all these nodes
			for node in soup.find_all(['font']):
				node.unwrap()
				plsWriteBack = True

			# convert name attribute into id in <a> tag
			tagsFixedCount = 0
			for anchorTag in soup.find_all(['a']):
				if anchorTag.has_attr('name'):
					anchorTag['id'] = anchorTag['name']
					del anchorTag['name']
					tagsFixedCount += 1
			if tagsFixedCount > 0:
				print('Converted %d `name` attribute into `id` in <a> tag(s).' % tagsFixedCount)
				plsWriteBack = True

			# remove lang, link, vlink attr, mso or calibre class
			for node in soup.find_all(True):
				del node['lang']
				del node['link']
				del node['vlink']
				class_attr = node.get('class')
				if class_attr:
					try:
						classes = class_attr.split(' ')
					except:
						classes = class_attr
					new_classes = []
					for cl in classes:
						if not (cl.startswith('Mso') or cl.startswith('mso') or cl.startswith('calibre')):
							new_classes.append(cl)
					if len(new_classes) > 0:
						node['class'] = ' '.join(new_classes)
					else:
						del node['class']

					plsWriteBack = True

			if plsWriteBack:
				reloadSoup()


		def easyClean2():
			nonlocal soup
			plsWriteBack = False

			# remove all data-* attributes from tags
			tagsFixedCount = 0
			for buggyTag in soup.find_all(True):
				attrDel = 0
				for attr in list(buggyTag.attrs.keys()):
					if attr.startswith('data-'):
						del buggyTag[attr]
						attrDel += 1
					elif attr == 'itemprop':
						del buggyTag[attr]
						attrDel += 1
					elif attr == 'target':
						del buggyTag[attr]
						attrDel += 1
				if attrDel > 0:
					tagsFixedCount += 1

			if tagsFixedCount > 0:
				reloadSoup()
				print('Removed itemprop/data-*/target attribute(s) from %d tag(s).' % tagsFixedCount)

			# remove  align/noshade/size/width attributes from <hr> tags
			tagsFixedCount = 0
			for buggyTag in soup.find_all('hr'):
				attrDel = 0
				for attr in list(buggyTag.attrs.keys()):
					if attr in ['align', 'noshade', 'size', 'width']:
						del buggyTag[attr]
						attrDel += 1
				if attrDel > 0:
					tagsFixedCount += 1
			if tagsFixedCount > 0:
				reloadSoup()
				print('Removed all deprecated attributes from %d <hr> tag(s).' % tagsFixedCount)

			# handle align attribute in p, div, span
			tagsFixedCount = 0
			for pdivspanTag in soup.find_all(True):
				alignAttr = pdivspanTag.get('align')
				if alignAttr != None:
					styleAttr = pdivspanTag.get('style')
					if styleAttr:
						pdivspanTag['style'] = 'text-align: %s; ' % alignAttr + styleAttr
					else:
						pdivspanTag['style'] = 'text-align: %s;' % alignAttr
					del pdivspanTag['align']
					tagsFixedCount += 1
			if tagsFixedCount > 0:
				reloadSoup()
				print('Converted align attribute in %d p/div/span tag(s) into css style.' % tagsFixedCount)

			# remove all links except for stylesheet ones
			for node in soup.find_all(['link', 'meta']):
				if not node.get('rel') == "stylesheet":
					node.decompose()
					plsWriteBack = True

			# Ziru’s Musings ads or placeholders for ads
			for node in soup.findAll('div', { 'class': lambda x: x and ('ezoic-adpicker-ad' in x.split()) }):
				node.decompose()
				plsWriteBack = True

			if plsWriteBack:
				reloadSoup()


		def removeAllStyleAttr():
			nonlocal soup
			# hard-core clean up. strip all style
			# generally should not be used
			for node in soup.find_all(True):
				del node['style']
			reloadSoup()


		def removeEmptyStyleAttr():
			nonlocal soup
			plsWriteBack = False
			for node in soup.find_all(True):
				if node.has_attr('style'):
					styleAttr = node['style'].strip()
					if styleAttr:
						node['style'] = styleAttr
					else:
						del node['style']
						plsWriteBack = True
			if plsWriteBack:
				reloadSoup()


		def stripHeaderFormattings():
			nonlocal soup
			# strip all formatings from headings as BTE-GEN does
			headingLv = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
			headingStrippedCount = 0
			for lv in headingLv:
				for headingTag in soup.find_all(lv):
					if len(headingTag.find_all('img')) == 0 and (len(headingTag.find_all(True)) > 0 or headingTag.get('style')):
						headingTag.string = headingTag.get_text().strip()
						del headingTag['style']
						headingStrippedCount += 1
			if headingStrippedCount > 0:
				reloadSoup()
				print('Stripped formatings from %d headings to match BTE-GEN\'s behavior.' % headingStrippedCount)


		def removedNoDisplayDiv():
			nonlocal soup

			# remove all <div style="display:none;">
			modifiedTagCount = 0
			removeMe = []

			for divTag in soup.find_all('div'):
				if divTag and divTag.get("style") and 'display:none' in re.sub("\s", "", divTag.get("style")):
					removeMe.append(divTag)
					modifiedTagCount += 1

			if modifiedTagCount > 0:
				for divTag in removeMe:
					divTag.decompose()
				print('Removed %d <div style="display:none;"> tags.' % modifiedTagCount)
				reloadSoup()


		def fixBadIBUusage():
			nonlocal soup
			# handle the invalid usage of <i> tags in HakoMari vol 2 may 2. This is due to a major error in the source page, but it can't be helped.
			# also stuff here https://baka-tsuki.org/project/index.php?title=User_talk:Dreamer2908
			# ref http://www.w3schools.com/html/html_formatting.asp
			headingLv = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
			tagsFixedCount = 0
			tag2Css =  {
						'b':'font-weight: bold;',
						'strong':'font-weight: bold;',
						'i':'font-style: italic;',
						'em':'font-style: italic;',
						'big':'font-size: large',
						'small':'font-size: smaller',
						'mark':'background-color: yellow; color: black;',
						's':'text-decoration: line-through;',
						'strike':'text-decoration: line-through;',
						'del':'text-decoration: line-through;',
						'ins':'text-decoration: underline;',
						'sub':'vertical-align: sub; font-size: smaller;',
						'sup':'vertical-align: super; font-size: smaller;',
						'u':'text-decoration: underline;',
						}
			for iTag in soup.find_all(['b', 'strong', 'i', 'em', 'big', 'small', 'mark', 's', 'strike', 'del', 'ins', 'sub', 'sup', 'u']):
				illegalChild = iTag.find_all(['p', 'div', 'table', 'blockquote', 'pre', 'caption', 'dl', 'hr', 'section', 'ul', 'ol'] + headingLv)
				if len(illegalChild) > 0:
					tagsFixedCount += 1
					for child in iTag.children:
						if type(child) == sigil_bs4.element.NavigableString:
							# a lot of unwanted `<p><i> </i></p>` line will be created if you wrap everything without checking
							if str(child).strip() != '':
								wrapper = child.wrap(soup.new_tag(iTag.name))
								wrapper.wrap(soup.new_tag('p'))
						elif child.name == 'p':
							for grandChild in child.children:
								if type(grandChild) == sigil_bs4.element.Tag:
									if grandChild.name == iTag.name:
										grandChild.unwrap() # remove italic from italic text
									else:
										grandChild.wrap(soup.new_tag(iTag.name))
								else:
									grandChild.wrap(soup.new_tag(iTag.name))
						elif child.name not in headingLv: # skip styling headings
							styleAttr = child.get('style')
							if styleAttr:
								child['style'] = tag2Css[iTag.name] + styleAttr
							else:
								child['style'] = tag2Css[iTag.name]
					iTag.unwrap()

			if tagsFixedCount > 0:
				reloadSoup()
				print('Fixed %d range of invalid usage of text formatting tags (i/b/u/etc.)' % tagsFixedCount)


		def convertPossibleDivToP():
			nonlocal soup
			# convert div into p if possible
			modifiedTagCount = 0
			for divTag in soup.find_all('div'):
				if canBeConvertedIntoP(divTag):
					divTag.name = 'p'
					modifiedTagCount += 1
				# elif not (divTag.get('style') or divTag.get('id') or divTag.get('class')):
				# 	divTag.unwrap()
			if modifiedTagCount > 0:
				reloadSoup()
				print('Converted %d div tags into p.' % modifiedTagCount)


		def unwarpSingleBigDiv():
			nonlocal soup

			# unwrap the big single div holding all contents
			bigDivCount = 0
			for node in soup.body.contents:
				if (type(node) == sigil_bs4.element.Tag):
					if (node.name == 'div'):
						bigDivCount += 1
					else:
						bigDivCount += 1000
			if bigDivCount == 1:
				soup.body.div.unwrap()
				reloadSoup()
				print('Unwrapped the big single div holding all contents.')


		def unwarpPossibleDiv_basic():
			nonlocal soup

			modifiedTagCount = 0
			for divTag in soup.find_all('div'):
				if canBeUnwrap(divTag):
					divTag.unwrap()
					modifiedTagCount += 1
			if modifiedTagCount > 0:
				reloadSoup()
				print('Unwrapped %d div tags.' % modifiedTagCount)


		def unwarpPossibleDiv_experimental():
			nonlocal soup

			modifiedTagCount = 0
			pNodes = []
			for divTag in soup.find_all('div'):
				if canBeUnwrap(divTag):
					pNodes.append(divTag)
					modifiedTagCount += 1

			splitNodesIntoP(pNodes)

			if modifiedTagCount > 0:
				reloadSoup()
				print('Unwrapped %d div tags.' % modifiedTagCount)


		def removeEmptySpan():
			nonlocal soup
			# remove empty span
			# do this before wrap stray tags
			plsWriteBack = False
			for spanTag in soup.find_all(['span']):
				if spanTag.get_text().strip() == '' and len(spanTag.find_all(['img'])) == 0:
					spanTag.decompose()
					plsWriteBack = True
				else:
					if not (spanTag.get('style') or (spanTag.get('id') and spanTag.get('id').startswith('_Toc'))):
						spanTag.unwrap()
						plsWriteBack = True
					elif spanTag.get('style') and (spanTag.get('style').strip() == "font-weight: 400;" or spanTag.get('style').strip() == ""):
						spanTag.unwrap()
						plsWriteBack = True

			if plsWriteBack:
				reloadSoup()


		def wrapStrayText_basic():
			nonlocal soup

			# wrap stray (direct decendant of body) <br>/<span>/<a>, text formatting tags and text in <p> (krytykal/skythewood/imoutolicious source)
			phantomWrapped = 0
			removeMe = []

			for child in soup.body.contents:
				if type(child) == sigil_bs4.element.NavigableString:
					# a lot of unwanted `<p> </p>` line will be created if you wrap everything without checking
					if str(child).strip() != '':
						child.wrap(soup.new_tag('p'))['class'] = 'baka_epub_stray_elements'
						phantomWrapped += 1
					else:
						child.replace_with('\n') # eliminate blank stray texts that aren't newline or true white spaces

				elif type(child) == sigil_bs4.element.Tag:
					if child.name in ['br', 'a']:
						child.wrap(soup.new_tag('p'))['class'] = 'baka_epub_stray_elements'
						phantomWrapped += 1
					elif child.name in ['span', 'b', 'strong', 'i', 'em', 'big', 'small', 'mark', 's', 'strike', 'del', 'ins', 'sub', 'sup', 'u']:
						# for these, check if they have some contents. remove if no
						if (len(child.get_text().strip()) > 0 or len(child.find_all(True)) > 0):
							child.wrap(soup.new_tag('p'))['class'] = 'baka_epub_stray_elements'
						else:
							removeMe.append(child)
						phantomWrapped += 1

			if phantomWrapped > 0:
				for element in removeMe:
					element.decompose()
				reloadSoup()
				print('Wrapped %d stray <br>/<span>/<a>, text formatting tags and texts in <p>.' % phantomWrapped)


		def wrapStrayText_experimental():
			nonlocal soup

			splitNodesIntoP((soup.body, ))

		def removeEmptyP():
			nonlocal soup

			plsWriteBack = False
			for spanTag in soup.find_all(['p']):
				# remove empty p
				if spanTag.get_text().strip() == '' and len(spanTag.find_all(['img'])) == 0:
					spanTag.decompose()
					plsWriteBack = True

			if plsWriteBack:
				reloadSoup()


		cleanUpForWordpress()
		cleanUpForTruyenFull()
		unwarpSingleBigDiv()

		easyClean1()
		easyClean2()
		removeEmptyStyleAttr()
		stripHeaderFormattings()

		fixBadIBUusage()

		removedNoDisplayDiv()
		convertPossibleDivToP()
		unwarpPossibleDiv_experimental()

		removeEmptySpan()
		wrapStrayText_experimental()


		textContents = soup.serialize_xhtml()

		# strip all comments
		textContents = re.sub('<!--(.*?)-->', '', textContents, flags=re.DOTALL)

		bk.writefile(textID, textContents)

	print('Done.')
	return 0

tagsNotAllowedInP = ['div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8', 'ul', 'ol', 'table', 'hr', 'blockquote', 'form', 'svg', 'image']
def canBeConvertedIntoP(divTag):
	# exception: image with class svg_outer and svg_inner . Don't touch them
	if divTag.has_attr('class') and "svg_outer" in divTag['class']:
		return False
	# if no disallowed tag found, it's possible
	if len(divTag.find_all(tagsNotAllowedInP)) == 0:
		return True
	else:
		return False

def canBeUnwrap(divTag):
	return not (divTag.has_attr('id') or divTag.has_attr('class') or divTag.has_attr('style'))

def stringContainsAny(string1, listOfString):
	for s in listOfString:
		if s in string1:
			return True
	return False

def main():
	print ("I reached main when I should not have.\n")
	return -1

if __name__ == "__main__":
	sys.exit(main())
