#!/usr/bin/python
# -*- coding: utf-8 -*-


import matplotlib.pyplot as _plt
import numpy as _np
import scipy.signal as _sps

from apollon import aplot as _aplot
from apollon import fractal as _fractal
from apollon import segment as _segment


class OnsetDetector:

    __slots__ = ['audio_file_name', 'bins', 'H', 'idx', 'm', 'order',
                 'tau', 'time_stamp', 'window_length', 'window_hop_size']

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

        Return:
            (tuple) array of indices, list of entropy values
        """
        # meta
        self.audio_file_name = str(sig.file)
        self.bins = bins
        self.m = m
        self.order = order
        self.tau = tau
        self.time_stamp = _tools.time_stamp()
        self.window_hop_size = wlen
        self.window_length = whs


        # segment audio
        chunks = _segment.by_ms_with_hop(sig, self.window_length, self.window_hop_size)

        # calculate entropy for each chunk
        self.H = _np.empty(len(chunks))
        for i, ch in enumerate(chunks):
            em = _fractal.embedding(ch, self.tau, m=self.m, mode='wrap')
            self.H[i] = _fractal.pps_entropy(em, self.bins)

        # Take imaginary part of the Hilbert transform of the enropy
        self.H = _sps.hilbert(self.H).imag

        # pick the peaks
        odf = _np.absolute(self.H)    # use magnitude to consider negative peaks, too
        peaks, = _sps.argrelmax(odf, order=self.order)

        # calculate onset position to be in the middle of chunks
        self.idx = [(i+j)//2 for (i, j) in chunks.get_limits()[peaks]]
