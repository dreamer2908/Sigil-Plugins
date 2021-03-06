# Sigil Plugins

Sigil plugins and related stuffs I feel like to publish.

There's no installation package; just download and copy the folder to your Sigin plugin folder (usually at `%localappdata%\sigil-ebook\sigil\plugins`) and restart Sigil.

Not intended for average users. Some experience in plugin development or Python + BeautifulSoup are needed.

0. [Baka-Epub](https://github.com/dreamer2908/Baka-Epub) (in another repo)
1. [Baka-Jpeg](#baka-jpeg)
2. [Baka-UUID](#baka-uuid)
3. [Baka-Cleaner](#baka-cleaner)
4. [Saved Search](#saved-searches)
5. [Baka-Img](#baka-img)

(Sorted by publication date)

# Baka-Jpeg

Sigil plugin to compress images in ePub, with (supposedly) educated decisions.

It tries a few encodings to get the smallest size, with minimal quality loss.
- JPG - good quality/size ratio for photos. Bad for texts. We go with 95% quality for no visible loss or artifact.
- PNG - Quite big size for photos, but best for texts and sharp patterns (smallest and best quality). 

For example, [this image](https://i.imgur.com/6GVYJxC.png) is full of text. If you "compress" it into JPG, you will get a bigger file with worse quality.

For most photos, I can't differentiate between the lossless source and the lossy JPG over 95% quality (I stare at them closely). Well, for e-books, I think 90% quality is sufficient, but 95% quality gives small enough output so I go with it.

To speed things up, it won't try lossless compression with lossy images as it's pointless (JPG with text won't get smaller when it is converted into PNG). It also won't try to further compress PNG images even though it does help, because the difference is usually minimal.

Moreover, it automatically downscales images larger than 1800px (any dimension) to 1600px (and checks if it helps - always). This is on by default but can be turned off and otherwise configured (by editing the source code - excuse me for the lack of GUI).

Finally, only JPG, BMP, and PNG are processed. You might encounter other formats, but I won't risk messing up animated GIF or some strange formats.

# Baka-UUID

It generates a new identifier in UUIDv4 scheme. The new id is applied to both metadata and toc file.

# Baka-Cleaner

For sources with a lot of junk tags like Skythewood Translations. Probably safe for other sources.

Use with care. Save your file before running it. You won't be able to undo.

Very user-unfriendly. Look at the code to see what it actually does. Some experience in plugin development are needed to use it effectively.

1. Fetch the contents with WebToEpub. [Screenshot](https://i.imgur.com/v0fZL8K.png)
2. Run though a batch 50+ saved searches to remove much junk. Search around to search for leftover needless styles. Make more saved searches for later use. [Screenshot](https://i.imgur.com/sJ4z5yp.png)
3. Validate epub with FlightCrew for syntax errors. Ignore all messages about <x> tag not allowed in <y> tag.
4. Run Baka-Cleaner to fix it up and create clean xhtml code. [Screenshot](https://i.imgur.com/ezSbL8O.png)
5. Correcting heading, metadata, illustrations, retructuring texts, and other actions to meet my quality baseline.

# Saved Searches

My saved searches in Sigil.

# Baka-Img

Warp image in svg and div. 

Insert `<div class="svg_outer svg_inner"><img alt="" src="../Images/your_image.jpg"/></div>` in a HTML file. Run Baka-Img and it will be converted to something like this:

`<div class="svg_outer svg_inner"><svg height="98%" preserveAspectRatio="xMidYMid meet" version="1.1" viewBox="0 0 456 640" width="98%" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><image height="640" width="456" xlink:href="../Images/your_image.jpg"/></svg></div>`

There're some options in the code.
