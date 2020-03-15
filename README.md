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
