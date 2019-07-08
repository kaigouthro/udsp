"""
Built-in signals commonly used in DSP

"""

import math as _math

from .bbase import Builtin1D, Builtin2D
from ..core import mtx as _mtx
from ..core import stat as _stat
from ..core import media as _media


# ---------------------------------------------------------
#                         Mixins
# ---------------------------------------------------------


class RNGMixin:
    """
    Provides RNGs with various p.d.f.

    """
    dist = {
        "uniform": _stat.rng_uniform,
        "normal": _stat.rng_normal,
        "lorentz": _stat.rng_cauchy_lorentz,
        "laplace": _stat.rng_laplace,
    }


# ---------------------------------------------------------
#                       1D signals
# ---------------------------------------------------------


class Const1D(Builtin1D):
    """
    Constant signal

    Attributes
    ----------
    k: float
        The value of the constant

    """
    def __init__(self, k=0, **kwargs):
        super().__init__(**kwargs)
        self.k = k
        self.make()

    def _generate(self, x):

        def f(n):
            return self.k

        return _mtx.vec_new(len(x), f)


class Pulse1D(Builtin1D):
    """
    Pulse (rectangular) signal

    Attributes
    ----------
    xo: float
        The central point of the pulse
    w: float
        The width of the pulse
    a: float
        The amplitude (height) of the pulse

    """
    def __init__(self,
                 xo=0,
                 w=1,
                 a=1,
                 **kwargs):

        super().__init__(**kwargs)
        self.xo = xo
        self.w = w
        self.a = a
        self.make()

    def _generate(self, x):
        x1, x2 = self.xo - self.w / 2, self.xo + self.w / 2

        def f(n):
            return self.a if x1 <= x[n] <= x2 else 0

        return _mtx.vec_new(len(x), f)


class Gaussian1D(Builtin1D):
    """
    Gaussian signal

    Attributes
    ----------
    u: float
        The mean of the Gaussian
    s: float
        The standard deviation of the Gaussian
    k: float
        The normalization factor

    """
    def __init__(self,
                 u=0,
                 s=1,
                 k=1,
                 **kwargs):

        super().__init__(**kwargs)
        self.u = u
        self.s = s
        self.k = k
        self.make()

    def _generate(self, x):

        def f(n):
            return self.k * _math.exp(
                -(x[n] - self.u) ** 2 / (2 * self.s ** 2)
            )

        return _mtx.vec_new(len(x), f)


class Sinewave1D(Builtin1D):
    """
    Sine wave signal

    Attributes
    ----------
    a: float
        The amplitude of the wave
    f: float
        The frequency of the wave
    p: float
        The phase of the wave

    """
    def __init__(self,
                 a=1,
                 f=1,
                 p=0,
                 **kwargs):

        super().__init__(**kwargs)
        self.a = a
        self.f = f
        self.p = p
        self.make()

    def _generate(self, x):

        def f(n):
            return self.a * _math.sin(
                2 * _math.pi * self.f * x[n] + self.p
            )

        return _mtx.vec_new(len(x), f)


class Logistic1D(Builtin1D):
    """
    Logistic signal

    Attributes
    ----------
    a: float
        The amplitude (maximum)
    k: float
        The steepness
    xo: float
        The central point

    """
    def __init__(self,
                 a=1,
                 k=1,
                 xo=0,
                 **kwargs):

        super().__init__(**kwargs)
        self.a = a
        self.k = k
        self.xo = xo
        self.make()

    def _generate(self, x):

        def f(n):
            return self.a / (1 + _math.exp(-self.k * (x[n] - self.xo)))

        return _mtx.vec_new(len(x), f)


class Noise1D(Builtin1D, RNGMixin):

    def __init__(self,
                 pdf="normal",
                 pdf_params=None,
                 **kwargs):
        """
        Creates a noise signal

        Parameters
        ----------
        pdf: {"uniform","normal","lorentz","laplace"}
            A str indicating the p.d.f. from which to draw the samples.
        pdf_params: None, dict
            Optional parameters accepted by the specified p.d.f.
            as key-value entries of a dictionary, as follows:

            p.d.f     parameters
            --------------------------------------------------------
            uniform   "a": <float> - The lower bound of the interval
                      "b": <float> - The upper bound of the interval

            normal    "sigma": <float> - The standard deviation
                      "trunc": (a,b) - Truncates the p.d.f. in (a,b)

            lorentz   "gamma": <float> - The scale of the p.d.f.
                      "trunc": (a,b) - Truncates the p.d.f. in (a,b)

            laplace   "lambd": <float> - The scale of the p.d.f.
                      "trunc": (a,b) - Truncates the p.d.f. in (a,b)

        kwargs: dict
            Optional arguments

        """
        super().__init__(**kwargs)
        self.pdf = pdf
        self.pdf_params = pdf_params
        self.make()

    def _generate(self, x):

        def f(n):
            return self.dist[self.pdf](**self.pdf_params or {})

        return _mtx.vec_new(len(x), f)


class MonoAudio(Builtin1D):
    """
    Mono channel audio

    Attributes
    ----------
    _audio: Audio
        The audio source object
    _bps: int
        The sample resolution in bits per sample

    Properties
    ----------
    sampres: int
        (read-only) The sample resolution

    """
    def __init__(self,
                 path,
                 **kwargs):

        audio = _media.Audio.from_file(path)
        super().__init__(
            length=(audio.metadata.size /
                    audio.metadata.resolution),
            sfreq=audio.metadata.resolution,
            xunits="s"
        )
        self._audio = audio
        self._bps = self._audio.metadata.bps
        self.make()

    def _generate(self, x):

        channels = self._audio.load()
        # Audio is mono
        if len(channels) == 1:
            channel = channels[0]
        # Audio is stereo
        elif len(channels) == 2:
            # Convert to mono
            channel = _mtx.vec_compose(
                channels,
                lambda l, r: round((l + r) / 2)
            )
        else:
            raise RuntimeError("Bug")
        self._audio = None  # we no longer need it
        return channel

    @property
    def sampres(self):
        return self._bps


class AudioChannel(Builtin1D):
    """
    Multi channel audio

    Attributes
    ----------
    _audio: Audio
        The audio source object
    _id: int
        The channel number
    _bps: int
        The sample resolution in bits per sample

    Properties
    ----------
    id: int
        (read-only) The channel number
    sampres: int
        (read-only) The sample resolution


    """
    _audio = None

    def __init__(self, **kwargs):

        super().__init__(**kwargs)
        self._id = None
        self._bps = None

    @classmethod
    def from_file(cls, path):

        audio = _media.Audio.from_file(path)
        cls._audio = audio.load()
        channels = []
        for c, _ in enumerate(cls._audio):
            channel = cls(
                length=(audio.metadata.size /
                        audio.metadata.resolution),
                sfreq=audio.metadata.resolution,
                xunits="s"
            )
            channel._id = c
            channel._bps = audio.metadata.bps
            channel.make()
            channels.append(channel)
        cls._audio = None
        return channels

    def _generate(self, x):
        return self._audio[self._id]

    @property
    def id(self):
        return self._id

    @property
    def sampres(self):
        return self._bps


# ---------------------------------------------------------
#                       2D signals
# ---------------------------------------------------------


class Const2D(Builtin2D):
    """
    Constant signal

    Attributes
    ----------
    k: float
        The value of the constant

    """
    def __init__(self,
                 k=0,
                 **kwargs):

        super().__init__(**kwargs)
        self.k = k
        self.make()

    def _generate(self, x):

        def f(n, m):
            return self.k

        return _mtx.mat_new(len(x), len(x[0]), f)


class Pulse2D(Builtin2D):
    """
    Pulse (rectangular) signal

    Attributes
    ----------
    xo: tuple
        The central point of the pulse
    w: tuple
        The width of the pulse
    a: float
        The amplitude (height) of the pulse

    """
    def __init__(self,
                 xo=(0, 0),
                 w=(1, 1),
                 a=1,
                 **kwargs):

        super().__init__(**kwargs)
        self.xo = xo
        self.w = w
        self.a = a
        self.make()

    def _generate(self, x):

        x1, x2 = self.xo[0] - self.w[0] / 2, self.xo[0] + self.w[0] / 2
        y1, y2 = self.xo[1] - self.w[1] / 2, self.xo[1] + self.w[1] / 2

        def f(n, m):
            def inbox(p):
                return (y1 <= p[0] <= y2) and (x1 <= p[1] <= x2)
            return self.a if inbox(x[n][m]) else 0

        return _mtx.mat_new(len(x), len(x[0]), f)


class Gaussian2D(Builtin2D):
    """
    Gaussian signal

    Attributes
    ----------
    u: tuple
        The mean of the Gaussian
    s: tuple
        The standard deviation of the Gaussian
    k: float
        The normalization factor

    """
    def __init__(self,
                 u=(0, 0),
                 s=(1, 1),
                 k=1,
                 **kwargs):

        super().__init__(**kwargs)
        self.u = u
        self.s = s
        self.k = k
        self.make()

    def _generate(self, x):

        def f(n, m):
            return self.k * _math.exp(
                - (x[n][m][0] - self.u[0]) ** 2 / (2 * self.s[0] ** 2)
                - (x[n][m][1] - self.u[1]) ** 2 / (2 * self.s[1] ** 2)
            )

        return _mtx.mat_new(len(x), len(x[0]), f)


class Noise2D(Builtin2D, RNGMixin):

    def __init__(self,
                 pdf="normal",
                 pdf_params=None,
                 **kwargs):
        """
        Creates a noise signal

        Parameters
        ----------
        pdf: {"uniform","normal","lorentz","laplace"}
            A str indicating the p.d.f. from which to draw the samples.
        pdf_params: None, dict
            Optional parameters accepted by the specified p.d.f.
            as key-value entries of a dictionary, as follows:

            p.d.f     parameters
            --------------------------------------------------------
            uniform   "a": <float> - The lower bound of the interval
                      "b": <float> - The upper bound of the interval

            normal    "sigma": <float> - The standard deviation
                      "trunc": (a,b) - Truncates the p.d.f. in (a,b)

            lorentz   "gamma": <float> - The scale of the p.d.f.
                      "trunc": (a,b) - Truncates the p.d.f. in (a,b)

            laplace   "lambd": <float> - The scale of the p.d.f.
                      "trunc": (a,b) - Truncates the p.d.f. in (a,b)

        kwargs: dict
            Optional arguments

        """
        super().__init__(**kwargs)
        self.pdf = pdf
        self.pdf_params = pdf_params
        self.make()

    def _generate(self, x):

        def f(n, m):
            return self.dist[self.pdf](**self.pdf_params or {})

        return _mtx.mat_new(len(x), len(x[0]), f)


class GrayImage(Builtin2D):
    """
    Grayscale image

    Attributes
    ----------
    _image: Image
        The image source object

    """
    def __init__(self,
                 path,
                 **kwargs):

        image = _media.Image.from_file(path)
        super().__init__(
            length=(*reversed(image.metadata.size),)
        )
        self._image = _media.Image.from_file(path)
        self.make()

    def _generate(self, x):

        planes = self._image.load()
        # Image is L or LA (grayscale)
        if len(planes) in (1, 2):
            yplane = planes[0]
        # Image is RGB or RGBA (colour)
        elif len(planes) in (3, 4):
            cplanes = planes if len(planes) == 3 else planes[:3]
            # Convert to grayscale
            yplane = _mtx.mat_compose(
                cplanes,
                lambda r, g, b: round(0.2126 * r +
                                      0.7152 * g +
                                      0.0722 * b)
            )
        else:
            raise RuntimeError("Bug")
        self._image = None  # we no longer need it
        return yplane


class ImageChannel(Builtin2D):
    """
    Multi channel image

    Attributes
    ----------
    _image: Image
        The image source object
    _id: int
        The channel number

    Properties
    ----------
    id: int
        (read-only) The channel number


    """
    _image = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._id = None

    @classmethod
    def from_file(cls, path):

        image = _media.Image.from_file(path)
        cls._image = image.load()
        channels = []
        for c, _ in enumerate(cls._image):
            channel = cls(
                length=(*reversed(image.metadata.size),)
            )
            channel._id = c
            channel.make()
            channels.append(channel)
        cls._audio = None
        return channels

    def _generate(self, x):
        return self._image[self._id]

    @property
    def id(self):
        return self._id

