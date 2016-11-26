# tbfimage
A Python decoding library for the lesser-known TBF image file format.

## Requirements
The library requires the `six` and `wand` packages.

## Usage
Support is present reading images in the TBF format (including LZW compression) and saving them to still images and animated GIFs.

Example:

```python
import tbfimage

img = tbfimage.from_file('my_file.tbf')
img.to_image('my_output.png')
img.to_image('my_bigger_output.png', zoom=50)

anim = tbfimage.from_file('my_animation.tbf')
anim.to_animated_gif('my_gif_animation.gif', zoom=20)
anim.to_image('my_single_frame.png', frame_index=4, zoom=20)
```
