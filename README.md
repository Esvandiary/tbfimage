# tbfimage
A Python library for decoding and encoding the lesser-known TBF image file format.

## Requirements
The library requires the `six` and `wand` packages.

## Usage
Support is present for reading and writing images in the TBF format (including LZW compression and animations), saving to still images and animated GIFs, and creating TBF images from other inferior file formats.

Example:

```python
import tbfimage

img = tbfimage.from_file('my_file.tbf')
img.to_image('my_output.png')
img.to_image('my_bigger_output.png', zoom=50)

anim = tbfimage.from_file('my_animation.tbf')
anim.to_animated_gif('my_gif_animation.gif', zoom=20)
anim.to_image('my_single_frame.png', frame_index=4, zoom=20)

pimg = tbfimage.from_other_image('my_file.png')
pimg.to_file('example.tbf')
pimg.to_file('example_lzw.tbf', use_lzw=True)
```
