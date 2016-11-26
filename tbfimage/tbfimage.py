from __future__ import print_function, division
from . import bitstring
from . import lzw
import sys
import wand.image as wi
import wand.color as wc
import wand.drawing as wd

FORMAT_BW = 'bw'
FORMAT_RGB = 'rgb'
PIXELSIZE = {FORMAT_BW: 1, FORMAT_RGB: 3}
DEFAULT_COLOR = {FORMAT_BW: 0, FORMAT_RGB: (0, 0, 0)}

COLORS = {
  FORMAT_BW: {
    0: wc.Color('#000'),
    1: wc.Color('#FFF'),
  },
  FORMAT_RGB: {
    (0, 0, 0): wc.Color('#000'),
    (1, 0, 0): wc.Color('#F00'),
    (1, 1, 0): wc.Color('#FF0'),
    (1, 0, 1): wc.Color('#F0F'),
    (0, 1, 0): wc.Color('#0F0'),
    (0, 1, 1): wc.Color('#0FF'),
    (0, 0, 1): wc.Color('#00F'),
    (1, 1, 1): wc.Color('#FFF'),
  },
}


class TBFFrame(object):
  def __init__(self, format, width, height, pixels = None, duration = None):
    self.format = format
    self.width = width
    self.height = height
    self.pixels = pixels if pixels is not None else [DEFAULT_COLOR[self.format]] * (self.width * self.height)
    self.duration = duration

  def set_pixel(self, x, y, pval):
    self.pixels[y*self.width + x] = pval

  def draw(self, img, zoom = 1):
    with wd.Drawing() as draw:
      for y in range(self.height):
        for x in range(self.width):
          draw.fill_color = COLORS[self.format][self.pixels[y*self.width + x]]
          draw.rectangle(left=x*zoom, top=y*zoom, width=zoom, height=zoom)
      draw(img)


class TBFImage(object):
  def __init__(self, format, width, height):
    self.format = format
    self.width = width
    self.height = height
    self.frames = []

  def start_frame(self):
    frame = TBFFrame(self.format, self.width, self.height)
    self.frames.append(frame)
    return frame

  def to_image(self, filename, frame_index = 0, zoom = 1):
    if not any(self.frames) or len(self.frames) <= frame_index:
      raise Exception("tried to output non-existent frame to PNG")
    with wi.Image(width=self.width*zoom, height=self.height*zoom) as img:
      self.frames[frame_index].draw(img, zoom)
      img.save(filename=filename)

  def to_animated_gif(self, filename, zoom = 1):
    if not any(self.frames):
      raise Exception("tried to output animated GIF with no frames")
    with wi.Image() as anim:
      for frame in self.frames:
        with wi.Image(width=self.width*zoom, height=self.height*zoom) as img:
          frame.draw(img, zoom)
          anim.sequence.append(img)
          anim.sequence[-1].delay = (frame.duration if frame.duration else 0) // 10  # ms --> 1/100s of a second
      anim.type = 'optimize'
      anim.save(filename=filename)


def _unpack_value(format, b):
  if format == FORMAT_RGB:
    return (int(b[0]), int(b[1]), int(b[2]))
  elif format == FORMAT_BW:
    return int(b[0])
  else:
    raise Exception("tried to unpack a value with an invalid format")


def from_file(filename):
  with open(filename, "rb") as f:
    data = f.read()
    b = bitstring.BitArray(data)
    format = FORMAT_RGB if b[0] else FORMAT_BW
    pixelsize = PIXELSIZE[format]
    uses_lzw = True if b[1] else False
    bl = b[2:6].uint + 1
    pos = 6
    width = b[pos:pos+bl].uint + 1; pos += bl
    height = b[pos:pos+bl].uint + 1; pos += bl
    framelen = (pixelsize * width * height)
    img = TBFImage(format, width, height)
    pixeldata = b[pos:]
    if uses_lzw:
      pdd = list(lzw.decompress(pixeldata.tobytes()))
      pixeldata = bitstring.BitArray('hex=0x{0}'.format("".join(["{0:02X}".format(ord(n)) for n in pdd])))
    pos = 0  # now indexing into pixeldata
    while len(pixeldata) >= pos + framelen:
      frame = img.start_frame()
      for y in range(height):
        for x in range(width):
          val = _unpack_value(format, pixeldata[pos:pos+pixelsize])
          frame.set_pixel(x, y, val)
          pos += pixelsize
      if len(pixeldata) >= pos + 8:
        frame.duration = pixeldata[pos:pos+8].uint; pos += 8
    return img
