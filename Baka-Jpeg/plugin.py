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

	coverImgID = getCoverImageID(bk)

	replace_us = [] # list of (find, replace)
	set_me_as_cover = '' # if the cover image filename is changed, set the new name here
	set_me_as_cover_name = ''
	total_space_saved = 0
	compressed_image_count = 0

	skip_png_compression_for_png_inputs = True

	downscale_image_larger_than_xxx = True
	large_image_px = 1800 # image is considered large if any of its dimensions is larger than this
	downscale_to_px = 1600
	downscaled_image_count = 0

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

		downscaled = False
		if downscale_image_larger_than_xxx:
			im_width, im_height = im.size
			im_new_width, im_new_height = im.size

			if im_width > large_image_px or im_height > large_image_px:
				if im_width > im_height:
					im_new_width = downscale_to_px
					im_new_height = int(downscale_to_px / (im_width / im_height))
				else:
					im_new_height = downscale_to_px
					im_new_width = int(downscale_to_px * (im_width / im_height))

			if im_new_width < im_width:
				try: # the best-quality resampler PIL supports is LANCZOS. It was named ANTIALIAS in old version
					resampler = Image.LANCZOS
				except:
					resampler = Image.ANTIALIAS
				im = im.resize((im_new_width, im_new_height), resampler)
				print('Downscaled image to %dx%dpx' % (im_new_width, im_new_height))
				downscaled = True
				# print(im.size)

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
			# to speed up even more, skip png compression for png inputs, as it usually doesn't help
			if downscaled or original_format != 'PNG' or (original_format == 'PNG' and not skip_png_compression_for_png_inputs):
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
			else:
				# go with jpg if it saves at least 10%
				if (jpg_out_size <= 0.9*original_size):
					output_format = 'JPEG'
					output_binary = imgOut1.getvalue()
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
			compressed_image_count += 1
			if downscaled:
				downscaled_image_count += 1
		else:
			print('No significant space saves. No change.')

		# write output, overwrite if necessary
		if original_format == output_format:
			bk.writefile(manifest_id, output_binary)
		elif output_format:
			# delete the original file
			bk.deletefile(manifest_id)

			new_ext = '.jpg'
			if output_format == 'PNG':
				new_ext = '.png'
			new_href = os.path.splitext(OPF_href)[0] + new_ext

			# check if file with the same name exists
			existing_id = bk.href_to_id(new_href)
			new_uuid = 'id-' + str(uuid.uuid4())
			if existing_id:
				# don't overwrite but add uuid to new filename
				new_href = os.path.splitext(OPF_href)[0] + '_' + new_uuid + new_ext

			# add a new file
			output_mediaType = "image/jpeg"
			if output_format == 'PNG':
				output_mediaType = "image/png"
			output_baseName = os.path.split(new_href)[1]
			output_manifestID = new_uuid # ensure it's unique and valid
			bk.addfile(output_manifestID, output_baseName, output_binary, output_mediaType)

			replace_us.append((urllib.parse.quote(OPF_href), urllib.parse.quote(new_href)))
			if manifest_id == coverImgID:
				set_me_as_cover = output_manifestID
				set_me_as_cover_name = output_baseName

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

	if set_me_as_cover:
		print('\nSetting %s as cover image...' % set_me_as_cover_name)
		setCoverImageID(bk, set_me_as_cover)

	print("\nCompressed %d files. %d of them were downscaled.  Saved %s." % ((compressed_image_count), downscaled_image_count, byteToHumanSize(total_space_saved)))

	print('Done.')
	return 0

def getCoverImageID(bk):
	# get cover image id from metadata
	coverImgID = ''
	metadata = bk.getmetadataxml()
	stinx = sigil_bs4.BeautifulSoup(metadata, 'xml')
	for node in stinx.find_all('meta'):
		if node.get('name') == 'cover':
			coverImgID = node.get('content')
			break

	return coverImgID

def setCoverImageID(bk, coverImgID):
	# set metadata: cover
	metadata_xml = bk.getmetadataxml()
	metadata_soup = sigil_bs4.BeautifulSoup(metadata_xml, 'xml')
	metadata_node = metadata_soup.find('metadata')

	if coverImgID:
		for node in metadata_node.find_all('meta'): # remove existing info
			if node.get('name') == 'cover':
				node.decompose()
		meta_cover_tag = metadata_soup.new_tag('meta')
		meta_cover_tag['name'] = 'cover'
		meta_cover_tag['content'] = coverImgID
		metadata_node.append(meta_cover_tag)

		bk.setmetadataxml(str(metadata_soup))

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
