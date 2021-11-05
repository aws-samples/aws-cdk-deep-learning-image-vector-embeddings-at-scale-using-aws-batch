import mxnet as mx
from mxnet import gluon, nd
from mxnet.gluon.model_zoo import vision
import numpy as np


class Image2Vec:
    '''
    Encapsulates all the logic to transform a Pillo image file to a vector
    representation based on the used model.
    '''
    def __init__(self):
        self._ctx = mx.cpu()
        self._net = vision.resnet18_v2(pretrained=True, ctx=self._ctx).features
        self.MEAN_IMAGE = mx.nd.array([0.485, 0.456, 0.406])
        self.STD_IMAGE = mx.nd.array([0.229, 0.224, 0.225])

    def preprocess_image(self, image):
        '''
        Preprocess an input Pillow image object.
        '''
        image_nd = self.correct_channel(nd.array(image))
        target_shape = (224, 244)
        resized = mx.image.resize_short(image_nd,
                                        target_shape[0]).astype('float32')
        cropped, crop_info = mx.image.center_crop(resized, target_shape)
        cropped /= 255.
        normalized = mx.image.color_normalize(cropped,
                                              mean=self.MEAN_IMAGE,
                                              std=self.STD_IMAGE)
        transposed = nd.transpose(normalized, (2, 0, 1))
        return transposed

    def correct_channel(self, image):
        if (len(image.shape) == 2):
            # Correct one channel (black-write) image to three channel (RGB) image by stacking
            image = nd.stack(image, image, image, axis=2)

        assert len(image.shape) == 3
        assert image.shape[2] == 3
        return image

    def to_vector(self, image):
        '''
        Vectorize an input Pillow image object.
        '''
        image_t = self.preprocess_image(image)
        output = self._net(image_t.expand_dims(axis=0).as_in_context(self._ctx))
        return output.asnumpy().reshape(-1, )
