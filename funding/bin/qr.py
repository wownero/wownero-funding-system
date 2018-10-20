import os
from io import BytesIO

import pyqrcode
from PIL import Image, ImageDraw

import settings


class QrCodeGenerator:
    def __init__(self):
        self.base = 'funding/static/qr'
        self.image_size = (300, 300)
        self.pil_save_options = {
            'quality': 25,
            'optimize': True
        }

        if not os.path.exists(self.base):
            os.mkdir(self.base)

    def exists(self, address):
        if not os.path.exists(self.base):
            os.mkdir(self.base)
        if os.path.exists(os.path.join(self.base, '%s.png' % address)):
            return True

    def create(self, address, dest=None, color_from=(210, 83, 200), color_to=(255, 169, 62)):
        """
        Create QR code image. Optionally a gradient.
        :param address:
        :param dest:
        :param color_from: gradient from color
        :param color_to:  gradient to color
        :return:
        """
        if len(address) != settings.COIN_ADDRESS_LENGTH:
            raise Exception('faulty address length')

        if not dest:
            dest = os.path.join(self.base, '%s.png' % address)

        created = pyqrcode.create(address, error='L')
        buffer = BytesIO()
        created.png(buffer, scale=14, quiet_zone=2)

        im = Image.open(buffer)
        im = im.convert("RGBA")
        im.thumbnail(self.image_size)

        im_data = im.getdata()

        # make black color transparent
        im_transparent = []
        for color_point in im_data:
            if sum(color_point[:3]) == 255 * 3:
                im_transparent.append(color_point)
            else:
                # get rid of the subtle grey borders
                alpha = 0 if color_from and color_to else 1
                im_transparent.append((0, 0, 0, alpha))
                continue

        if not color_from and not color_to:
            im.save(dest, **self.pil_save_options)
            return dest

        # turn QR into a gradient
        im.putdata(im_transparent)

        gradient = Image.new('RGBA', im.size, color=0)
        draw = ImageDraw.Draw(gradient)

        for i, color in enumerate(QrCodeGenerator.gradient_interpolate(color_from, color_to, im.width * 2)):
            draw.line([(i, 0), (0, i)], tuple(color), width=1)

        im_gradient = Image.alpha_composite(gradient, im)
        im_gradient.save(dest, **self.pil_save_options)

        return dest

    @staticmethod
    def gradient_interpolate(color_from, color_to, interval):
        det_co = [(t - f) / interval for f, t in zip(color_from, color_to)]
        for i in range(interval):
            yield [round(f + det * i) for f, det in zip(color_from, det_co)]
