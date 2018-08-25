#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""make_hmm.py

(c) Michael Blaß, 2016

Train a PoissonHmm of one single .wav file.
"""

import sys
from optparse import OptionParser
import pathlib

from numpy import hamming
from numpy import round as _round

from apollon.extract import spectral_centroid
from apollon.hmm.poisson_hmm import PoissonHmm
from apollon.signal.audio import loadwav
from apollon.io import save
from apollon.onsets import FluxOnsetDetector2
from apollon.segment import from_onsets


def main():

    def verbose_msg(s):
        if opts.verbose:
            print(s)

    usage = 'usage: %prog [OPTIONS] path_to_wav'
    parser = OptionParser(usage=usage)
    parser.add_option('-v', '--verbose', action='store_true',
                      help='enable verbose mode')
    (opts, args) = parser.parse_args()

    if len(args) == 0:
        print('Path to .wav-file not specified.')
        sys.exit(1)

    wfile = pathlib.Path(args[0])

    if wfile.exists():
        if wfile.is_file():
            verbose_msg('Loading file <{}> ...'.format(args[0]))
            sig = loadwav(str(wfile))
        else:
            raise FileExistsError('<{}> is not a file.\n'.format(args[0]))
    else:
        raise FileNotFoundError('File <{}> could not be found.\n'
                                .format(args[0]))

    # onset detection
    verbose_msg('detecting onsets ...')
    ons = FluxOnsetDetector2(sig, sig.fs)

    # segmentation
    verbose_msg('segmentation ...')
    chunks = from_onsets(sig, ons.index, 2**11)

    # feature extraction
    verbose_msg('extracting features ...')
    feat = spectral_centroid(chunks, 'hamming', sig.fs)
    feat = _round(feat).astype(int)

    # hmm
    verbose_msg('training hmm ...')
    mod = PoissonHmm(feat, 4, verbose=False)
    mod.fit()

    # saving
    ofile = wfile.stem + '.hmm'
    verbose_msg('saving to <{}>'.format(ofile))
    save(mod.gamma_, ofile)

    verbose_msg('DONE.\n')


if __name__ == "__main__":
    sys.exit(main())
