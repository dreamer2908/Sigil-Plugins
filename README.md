# Baka-Jpeg
Sigil plugin to compress images in ePub, with (supposedly) educated decisions.

It tries a few encodings to get the smallest size, with minimal quality loss.
- JPG - good quality/size ratio for photos. Bad for texts. We go with 95% quality for no visible loss or artifact.
- PNG - Quite big size for photos, but best for texts and sharp patterns (smallest and best quality). 

For example, [this image](https://i.imgur.com/6GVYJxC.png) is full of text. If you "compress" it into JPG, you will get a bigger file with worse quality.

For most photos, I can't differentiate between the lossless source and the lossy JPG over 95% quality (I stare at them closely). Well, for e-books, I think 90% quality is sufficient, but 95% quality gives small enough output so I go with it.
