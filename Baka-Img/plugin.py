#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os, re, codecs, random, string, uuid, io, urllib
import sigil_bs4
import sigil_gumbo_bs4_adapter as gumbo_bs4
from PIL import Image
from io import BytesIO

plugin_name = 'Baka-Img'
plugin_path = ''
text_type = str

def run(bk):
	# get python plugin path
	global plugin_path
	plugin_path = os.path.join(bk._w.plugin_dir, plugin_name)

	for (textID, textHref) in bk.text_iter():
		print('\nProcessing text file: %s' % textHref)

		textContents = bk.readfile(textID) # Read the section into textContents
		if not isinstance(textContents, text_type):	# If the section is not str then sets its type to 'utf-8'
			textContents = text_type(textContents, 'utf-8')

		soup = sigil_bs4.BeautifulSoup(textContents, "xml")

		# TODO: near square image?
		# done in getSvgForImage. not yet backport to baka-epub

		useImgForLandscape = False
		svgSizePercent = 98

		removeMe = []
		for divNode in soup.find_all("div"):
			if divNode.has_attr('class') and "svg_outer" in divNode['class']:
				for imgNode in divNode.find_all(["img", "svg"]):
					if imgNode.name == 'img':
						imgSrc = imgNode['src']
					else:
						imgSrc = imgNode.image['xlink:href']
					if imgSrc.startswith('../'): imgSrc = imgSrc[3:]
					imgID = bk.href_to_id(imgSrc)
					if imgID: # image file exists
						print('Found image: ' + imgSrc)
						if (len(bk.readfile(imgID)) == 0):
							print('Zero-length file. Removing...')
							removeMe.append(divNode)
						else:
							_useImg = useImgForLandscape
							if "svg_yes" in divNode['class']:
								_useImg = False
							_svgSizePercent = svgSizePercent
							if "svg_100" in divNode['class']:
								_svgSizePercent = 100
							svgNode = sigil_bs4.BeautifulSoup(getSvgForImage(bk, imgID, svgSizePercent=_svgSizePercent, useImgForLandscape=_useImg, dontWrapInDiv=True), "xml")
							imgNode.replace_with(svgNode)
					else:
						print('404 error: ' + imgSrc + '. Removing...')
						removeMe.append(divNode)

		for element in removeMe:
			element.decompose()

		textContents = str(soup)
		textContents = '<?xml version="1.0" encoding="utf-8"?>' + re.sub('<\?xml\s.*?\?>', '', textContents)
		bk.writefile(textID, textContents)

	print('Done.')
	return 0

def getSvgForImage(bk, manifestID, svgSizePercent=98, dispWidth=None, dispHeight=None, useImgForLandscape=True, dontWrapInDiv=False):
	from PIL import Image
	from io import BytesIO

	if not manifestID:
		return ''
	href = bk.id_to_href(manifestID)

	if manifestID and href: # id is specified and confirmed to exist
		imgName = urllib.parse.quote(os.path.split(href)[1])

		imgfile = bk.readfile(manifestID)
		imgfile_obj = BytesIO(imgfile)

		try:
			im =  Image.open(imgfile_obj)
			width, height = im.size

			template = '<div class="svg_outer svg_inner"><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="%d%%" height="%d%%" viewBox="0 0 __width__ __height__" preserveAspectRatio="xMidYMid meet"><image width="__width__" height="__height__" xlink:href="__addr__"/></svg></div>' % (svgSizePercent, svgSizePercent)
			if (1.0*width > 1.2*height) and useImgForLandscape: # do not wrap landscape images. They actually look better this way
				template = '<div class="svg_outer svg_inner"><img alt="" src="__addr__" width="100%" /></div>'
			if width < 400 and height < 400: # don't stretch small images
				template = '<div class="svg_outer svg_inner"><img alt="" src="__addr__" /></div>'
				# use the original display resolution if it's available and is even smaller
				# note that dispWidth and dispHeight might not be pixel
				# don't bother with something like 70%
				if isfloat(dispWidth) and isfloat(dispHeight):
					dispWidth = int(float(dispWidth))
					dispHeight = int(float(dispHeight))
					if dispWidth < width and dispHeight < height:
						template = '<div class="svg_outer svg_inner"><img alt="" src="__addr__" width="%d" height="%d" /></div>' % (dispWidth, dispHeight)
			imageCode = template.replace('__addr__', '../Images/' + imgName).replace('__width__', str(width)).replace('__height__', str(height))
		except Exception as e:
			print('Error occured when reading image file: ' + str(e))
			template = '<div class="svg_outer svg_inner"><img alt="" src="__addr__" /></div>'
			imageCode = template.replace('__addr__', '../Images/' + imgName)

		if dontWrapInDiv:
			return imageCode.replace('<div class="svg_outer svg_inner">', '').replace('</div>','')
		else:
			return imageCode
	else:
		return ''

def isfloat(value):
	try:
		float(value)
		return True
	except (ValueError, TypeError):
		return False

def main():
	print ("I reached main when I should not have.\n")
	return -1

if __name__ == "__main__":
	sys.exit(main())
