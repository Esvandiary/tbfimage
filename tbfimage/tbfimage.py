from __future__ import print_function, division
from . import bitstring
from . import lzw
import math
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
    0b0: wc.Color('#000'),
    0b1: wc.Color('#FFF'),
  },
  FORMAT_RGB: {
    0b000: wc.Color('#000'),
    0b100: wc.Color('#F00'),
    0b110: wc.Color('#FF0'),
    0b101: wc.Color('#F0F'),
    0b010: wc.Color('#0F0'),
    0b011: wc.Color('#0FF'),
    0b001: wc.Color('#00F'),
    0b111: wc.Color('#FFF'),
  },
}


class TBFFrame(object):
  def __init__(self, format, width, height, pixels = None, duration = None):
    if format not in (FORMAT_BW, FORMAT_RGB):
      raise ValueError("invalid format specified when creating TBFFrame")
    self.format = format
    self.width = width
    self.height = height
    self.pixels = pixels if pixels is not None else [DEFAULT_COLOR[self.format]] * (self.width * self.height)
    self.duration = duration

  def set_pixel(self, x, y, pval):
    self.pixels[y*self.width + x] = sum([pval[i] << (len(pval)-(i+1)) for i in range(len(pval))])

  def get_pixel(self, x, y):
    px = self.pixels[y*self.width + x]
    if format == FORMAT_RGB:
      return ((px >> 2) & 1, (px >> 1) & 1, (px >> 0) & 1)
    else:
      return (px & 1)

  def set_raw_pixel(self, x, y, pval):
    self.pixels[y*self.width + x] = pval

  def get_raw_pixel(self, x, y):
    return self.pixels[y*self.width + x]

  def draw(self, img, zoom = 1):
    with wd.Drawing() as draw:
      for y in range(self.height):
        for x in range(self.width):
          draw.fill_color = COLORS[self.format][self.pixels[y*self.width + x]]
          if zoom != 1:
            draw.rectangle(left=x*zoom, top=y*zoom, width=zoom, height=zoom)
          else:
            draw.point(x, y)
      draw(img)


class TBFImage(object):
  def __init__(self, format, width, height):
    if format not in (FORMAT_BW, FORMAT_RGB):
      raise ValueError("invalid format specified when creating TBFImage")
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
          with anim.sequence[-1] as lastframe:
            lastframe.delay = (frame.duration if frame.duration else 0) // 10  # ms --> 1/100s of a second
      anim.type = 'optimize'
      anim.save(filename=filename)

  def to_file(self, filename, use_lzw = False):
    b = bitstring.BitArray()
    b.append('0b1' if self.format == FORMAT_RGB else '0b0')
    b.append('0b1' if use_lzw else '0b0')
    bl = max(math.ceil(math.log2(self.width)), math.ceil(math.log2(self.height)))
    b.append("0b{0:04b}".format(bl - 1))
    b.append("0b{{0:0{0}b}}".format(bl).format(self.width - 1))
    b.append("0b{{0:0{0}b}}".format(bl).format(self.height - 1))

    pixeldata = bitstring.BitArray()
    for frame in self.frames:
      for y in range(0, frame.height):
        for x in range(0, frame.width):
          pixeldata.append(_pack_value(self.format, frame.get_raw_pixel(x, y)))
      if len(self.frames) > 1:
        pixeldata.append("0b{0:08b}".format(frame.duration))

    if use_lzw:
      pdc = list(lzw.compress(pixeldata.tobytes()))
      b.append(bitstring.ConstBitStream(bytes=b''.join(pdc)))
    else:
      b.append(pixeldata)

    with open(filename, "wb") as f:
      f.write(b.tobytes())


def _unpack_value(format, b):
  if format == FORMAT_RGB:
    return b.read('uint:3')
  elif format == FORMAT_BW:
    return b.read('uint:1')
  else:
    raise Exception("tried to unpack a value with an invalid format")


def _pack_value(format, val):
  if format == FORMAT_RGB:
    return bitstring.BitArray('0b{0:b}'.format(val))
  elif format == FORMAT_BW:
    return bitstring.BitArray('0b{0:b}'.format(val))
  else:
    raise Exception("tried to pack a value with an invalid format")


def _transform_value(px, format):
  if format == FORMAT_RGB:
    return (int(round(px[0] / 255.0)), int(round(px[1] / 255.0)), int(round(px[2] / 255.0)))
  else:
    return int(round(math.mean(px) / 255.0))


def _populate_frame_from_image(frame, img, format):
  blob = img.make_blob(format='RGB')
  for y in range(img.height):
    for x in range(img.width):
      base = y*img.width*3 + x*3
      frame.set_pixel(x, y, _transform_value((blob[base], blob[base+1], blob[base+2]), format))


def from_file(filename):
  with open(filename, "rb") as f:
    data = f.read()
    b = bitstring.ConstBitStream(data)
    format = FORMAT_RGB if b.read('bool') else FORMAT_BW
    pixelsize = PIXELSIZE[format]
    uses_lzw = True if b.read('bool') else False
    bl = b.read('uint:4') + 1
    width = b.read('uint:{0}'.format(bl)) + 1
    height = b.read('uint:{0}'.format(bl)) + 1
    framelen = (pixelsize * width * height)
    img = TBFImage(format, width, height)
    pixeldata = b.read(len(b) - b.pos)
    if uses_lzw:
      pdd = list(lzw.decompress(pixeldata.tobytes()))
      pixeldata = bitstring.ConstBitStream(bytes=b''.join(pdd))
    while len(pixeldata) >= pixeldata.pos + framelen:
      frame = img.start_frame()
      for y in range(height):
        for x in range(width):
          val = _unpack_value(format, pixeldata)
          frame.set_raw_pixel(x, y, val)
      if len(pixeldata) >= pixeldata.pos + 8:
        frame.duration = pixeldata.read('uint:8')
    return img


def from_other_image(filename, format = None):
  with wi.Image(filename=filename) as wimg:
    # Auto-detect format if not specified
    if format is None:
      format = FORMAT_RGB if (wimg.colorspace != 'gray') else FORMAT_BW
    img = TBFImage(format, wimg.width, wimg.height)
    if wimg.sequence is not None:
      for i in range(len(wimg.sequence)):
        with wimg.sequence[i] as si:
          with si.clone() as sic:
            f = img.start_frame()
            _populate_frame_from_image(f, sic, format)
            f.duration = si.delay * 10  # 1/100s --> ms
    else:
      f = img.start_frame()
      _populate_frame_from_image(f, wimg, format)
  return img

