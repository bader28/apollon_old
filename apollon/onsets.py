#!/usr/bin/python
# -*- coding: utf-8 -*-


import matplotlib.pyplot as _plt
import mir_eval as _me
import numpy as _np
import scipy.signal as _sps
from typing import Dict, Tuple

from apollon import fractal as _fractal
from apollon import segment as _segment
from apollon import tools as _tools
from apollon.signal.spectral import STFT
from apollon.tools import ztrans as _ztrans


class EnrtopyOnsetDetector:

    __slots__ = ['audio_file_name', 'bins', 'idx', 'm', 'odf', 'order', 'tau',
                 'time_stamp', 'window_length', 'window_hop_size']

    def __init__(self):
        pass

    def detect(self, sig, tau=10, m=3, bins=50, wlen=16, whs=8, order=22):
        """Detect note onsets in (percussive) music as local maxima of information
        entropy.

        Params:
            sig      (array-like) Audio signal.
            tau      (int) Phase-space: delay parameter in samples.
            m        (int) Phase-space: number of dimensions.
            bins     (int) Phase-space: number of boxes per axis.
            wlen     (int) Segmentation: window length in ms.
            whs      (int) Segmentation: window displacement in ms.
            order    (int) Peak-picling: Order of filter in samples.
        """
        # meta
        self.audio_file_name = str(sig.file)
        self.bins = bins
        self.m = m
        self.order = order
        self.tau = tau
        self.time_stamp = _tools.time_stamp()
        self.window_hop_size = whs
        self.window_length = wlen


        # segment audio
        chunks = _segment.by_ms_with_hop(sig, self.window_length,
                                         self.window_hop_size)

        # calculate entropy for each chunk
        H = _np.empty(len(chunks))
        for i, ch in enumerate(chunks):
            em = _fractal.embedding(ch, self.tau, m=self.m, mode='wrap')
            H[i] = _fractal.pps_entropy(em, self.bins)

        # Take imaginary part of the Hilbert transform of the enropy
        self.odf = _np.absolute(_sps.hilbert(H).imag)

        # pick the peaks
        peaks, = _sps.argrelmax(self.odf, order=self.order)

        # calculate onset position to be in the middle of chunks
        self.idx = _np.array( [(i+j)//2
                              for (i, j) in chunks.get_limits()[peaks]])


def peak_picking(odf, w=3, m=3, alpha=.1, delta=.1):

    g = [0]
    out = []

    for n, val in enumerate(odf):

        # set local window
        idx = _np.arange(n-m*w, n+w, 1)
        window = _np.take(odf, idx, mode='clip')

        # check three onset conditions
        #

        # First condition: val must be the biggest value within the local window
        cond1 = _np.all(val >= window)

        # Second condition: val must be bigger then the local windows's mean plus delta
        cond2 = val >= (_np.mean(window) + delta)

        # Third condition: val must be bigger then an adaptive threshold g(n, alpha)
        foo = max(val, alpha*g[n] + (1-alpha)*val)    # ATTENTION: This MUST be built-in max()
        g.append(foo)
        cond3 = val >= foo

        if cond1 and cond2 and cond3:
            out.append(n)

    return _np.array(out)


class FluxOnsetDetector:
    def __init__(self, sig, fs, nseg=2048, hop=441, scale=True, smooth=True):

        self.fs = fs
        self.nseg = nseg
        self.hop = hop

        X = STFT(sig, fs, nseg=nseg, nover=nseg-hop)
        
        rgy = _np.absolute(X).sum(axis=0)
        odf = _np.diff(rgy)
        if scale:
            fval = _np.finfo('float64').eps
            devi = _np.where(rgy[:-1]==0., fval, rgy[:-1])
            odf /= devi
        odf = _np.maximum(odf, 0)
        
        if smooth:
            if isinstance(smooth, int) and smooth > 0:
                k = smooth
            else:
                k = 5
            wh = _np.hamming(k)
            odf = _np.convolve(odf, wh, mode='same')

        self.odf = _tools.ztrans(odf)
        self.peaks = peak_picking(odf)
        self.index = self.peaks * self.hop
        self.times = self.index / self.fs
        

class FluxOnsetDetector2:
    def __init__(self, sig, fs, nseg=2048, hop=441, scale=True, smooth=10):
        fval = _np.finfo('float64').eps    # TODO move definition to apollon.constants
        self.fs = fs
        self.nseg = nseg
        self.hop = hop

        f, t, X = _sps.stft(sig, fs, nperseg=nseg, noverlap=nseg-hop,
                            detrend='constant')
        
        mag_X = _np.absolute(X)
        stdevi = mag_X.std(axis=0)
        stdevi = _np.where(stdevi==0., fval, stdevi)
        d_mag_X = _np.diff(mag_X)
        self.odf = _np.maximum(d_mag_X, 0).sum(axis=0)
    
        if scale:
            sm_X = mag_X[:, :-1].sum(axis=0)

            scale_fact = _np.where(sm_X==0., fval, sm_X)
            self.odf /= scale_fact
        
        if smooth:
            wh = _np.repeat([0., 1., 0.], smooth)
            self.odf = _np.convolve(self.odf, wh, mode='same')

        self.peaks = peak_picking(self.odf)
        self.index = self.peaks * self.hop
        self.times = self.index / self.fs
        
        
def evaluate_onsets(targets:   Dict[str, _np.ndarray],
                    estimates: Dict[str, _np.ndarray]) -> Tuple[float, float,
                                                                float]:
    """Evaluate the performance of an onset detection.

    Params:
        targets    (dict) of ground truth onset times, with
                            keys   == file names, and
                            values == target onset times in ms.

        estimates  (dict) of estimated onsets times, with
                            keys   == file names, and
                            values == estimated onset times in ms.

    Return:
        (p, r, f)    Tupel of precison, recall, f-measure
    """

    out = []
    for name, tvals in targets.items():
        od_eval = _me.onset.evaluate(tvals, estimates[name])
        out.append([i for i in od_eval.values()])

    return _np.array(out)
