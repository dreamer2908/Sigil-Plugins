#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os, re, uuid, io, urllib
import sigil_bs4
import sigil_gumbo_bs4_adapter as gumbo_bs4
from PIL import Image
from io import BytesIO

plugin_name = 'Baka-Jpeg'
plugin_path = ''
text_type = str

def run(bk):
	# get python plugin path
	global plugin_path
	plugin_path = os.path.join(bk._w.plugin_dir, plugin_name)

	replace_us = [] # list of (find, replace)
	set_me_as_cover = '' # if the cover image filename is changed, set the new name here
	total_space_saved = 0

	for (manifest_id, OPF_href, media_type) in bk.image_iter():
		print('\nProcessing image: %s' % OPF_href)

		# read image
		imgfile = bk.readfile(manifest_id)
		imgfile_obj = BytesIO(imgfile)
		try:
			im =  Image.open(imgfile_obj)
		except Exception as e:
			print('Error: %r' % e)
			print('Skipped.')
			continue

		# show original info
		original_size = len(imgfile)
		original_format = im.format
		print('Input size: %d' % original_size)
		print('Input format: %s' % im.format)

		# Only continue if it's BMP, PNG, and JPEG
		# Well, at least don't touch GIF (may have animation) or whatever uncommon formats
		if original_format not in ['BMP', 'PNG', 'JPEG']:
			print('Not BMP, PNG, or JPEG. Skipped.')
			continue

		# Try a few encoding to get the smallest size.
		# - PNG - best for texts and sharp patterns, smallest and best quality. Quite big for common photos.
		# - JPG - good quality/size ratio for photos. Bad for texts. We go with 95% quality for no visible loss or artifact
		# Progressive JPGs are almost always smaller than baseline (normal) JPGs
		# The different is not large, but there's no drawback except negligible performance loss
		# Only use lossy compression if it saves more than 10%
		# Note that mode P can't be saved to jpg directly, convert it to RGB first
		imgOut1 = BytesIO()
		im.convert("RGB").save(imgOut1, 'JPEG', quality=95, optimize=True, progressive=True)
		jpg_out_size = len(imgOut1.getvalue())
		print('Output JPEG size: %d' % jpg_out_size)

		output_format = '' # empty = do nothing
		output_binary = ''
		if (original_format in ['PNG', 'BMP']): # lossless source
			# to save time, only do lossless compression if the source is lossless
			imgOut2 = BytesIO()
			im.save(imgOut2, 'PNG', optimize=True)
			png_out_size = len(imgOut2.getvalue())
			print('Output PNG size: %d' % png_out_size)
			# go with jpg if it saves at least 10%, and significantly more than png does
			if (jpg_out_size <= 0.9*original_size) and (jpg_out_size <= 0.9*png_out_size):
				output_format = 'JPEG'
				output_binary = imgOut1.getvalue()
			# otherwise, go with png if it saves something
			elif (png_out_size < original_size):
				output_format = 'PNG'
				output_binary = imgOut2.getvalue()
		else: # source is lossy
			# go with jpg if it saves at least 10%
			if (jpg_out_size <= 0.9*original_size):
				output_format = 'JPEG'
				output_binary = imgOut1.getvalue()

		if output_format:
			space_saved = (original_size) - len(output_binary)
			print('Selected format: %s' % output_format)
			print('Saved space: %d' % space_saved)
			total_space_saved += space_saved
		else:
			print('No significant space saves. No change.')

		# write output, overwrite if necessary
		if original_format == output_format:
			bk.writefile(manifest_id, output_binary)
		elif output_format:
			new_ext = '.jpg'
			if output_format == 'PNG':
				new_ext = '.png'
			new_href = os.path.splitext(OPF_href)[0] + new_ext

			# check if file with the same name exists
			existing_id = bk.href_to_id(new_href)
			if existing_id:
				# overwrite
				bk.writefile(existing_id, output_binary)
			else:
				# add a new file
				output_mediaType = "image/jpeg"
				if output_format == 'PNG':
					output_mediaType = "image/png"
				output_baseName = os.path.split(new_href)[1]
				output_manifestID = 'id-' + str(uuid.uuid4()) # ensure it's unique and valid
				bk.addfile(output_manifestID, output_baseName, output_binary, output_mediaType)
				# and then delete the original file
				bk.deletefile(manifest_id)

			replace_us.append((urllib.parse.quote(OPF_href), urllib.parse.quote(new_href)))

	print('\nFinding and replacing filenames in text...\n')
	# print(replace_us)

	for (textID, textHref) in bk.text_iter():
		print('Processing text file: %s' % textHref)

		textContents = bk.readfile(textID) # Read the section into textContents
		if not isinstance(textContents, text_type):	# If the section is not str then sets its type to 'utf-8'
			textContents = text_type(textContents, 'utf-8')

		for (find_me, replace_me) in replace_us:
			textContents = textContents.replace(find_me, replace_me)

		bk.writefile(textID, textContents)

	# TODO: set_me_as_cover

	print("\nCompressed %d file(s). Saved %s." % (len(replace_us), byteToHumanSize(total_space_saved)))

	print('Done.')
	return 0

def byteToHumanSize(size):
	if size >= 1000 * 1024 * 1024:
		return '%0.3f GiB' % (size / (1024 ** 3))
	elif size >= 1000 * 1024:
		return '%0.3f MiB' % (size / 1024 ** 2)
	elif size >= 1000:
		return '%0.3f KiB' % (size / 1024)
	else:
		return '%s bytes' % size

def main():
	print ("I reached main when I should not have.\n")
	return -1

if __name__ == "__main__":
	sys.exit(main())
