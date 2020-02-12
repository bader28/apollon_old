"""apollon/io.py -- General I/O functionallity.

Licensed under the terms of the BSD-3-Clause license.
Copyright (C) 2019 Michael Blaß, mblass@posteo.net

Classes:
    ArrayEncoder            Serialize numpy array to JSON.
    FileAccessControl       Descriptor for file name attributes.

Functions:
    array_print_opt         Set format for printing numpy arrays.
    decode_ndarray          Decode numpy array from JSON.
    dump_json               Serialize objects to JSON.
    encode_ndarray          Encode numpy array to JSON.
    files_in_folder         Iterate over all files in given folder.
    generate_outpath        Compute path for feature output.
    load                    Load pickled data.
    load_json               Load JSON data including numpy arrays.
    repath                  Change path but keep file name.
    save                    Pickle some data.
"""
from contextlib import contextmanager as _contextmanager
import json as _json
import jsonschema as _jsonschema
import pathlib as _pathlib
import pickle
from typing import Any, Union

import numpy as _np

from . import types as _types
from . import container


ndarray = {
    'type': 'object',
    'properties': {
        '__ndarray__': {'type': 'boolean'},
        '__dtype__': {'type': 'string'},
        'data': {'type': 'array'}
    }
}


class ArrayEncoder(_json.JSONEncoder):
    # pylint: disable=E0202
    # Issue: False positive for E0202 (method-hidden) #414
    # https://github.com/PyCQA/pylint/issues/414
    """Encode np.ndarrays to JSON.

    Simply set the ``cls`` parameter of the dump method to this class.
    """
    def default(self, inp):
        """Custon SON encoder for numpy arrays. Other types are passed
        on to ``JSONEncoder.default``.

        Args:
            inp:  Object to encode.

        Returns:
            JSON-serializable dictionary.
        """
        if isinstance(obj, _np.ndarray):
            return encode_ndarray(obj)
        return _json.JSONEncoder.default(self, obj)


def decode_ndarray(arr: dict) -> _np.ndarray:
    """Decode numerical numpy arrays from a JSON data stream.

    Args:
        arr:  dict adhering ``ndarray`` schema.

    Returns:
        Numpy array.
    """
    _jsonschema.validate(arr, ndarray, _jsonschema.Draft7Validator)
    return _np.array(arr['data'], dtype=arr['__dtype__'])


def encode_ndarray(arr: _np.ndarray) -> dict:
    """Transform an numpy array to a JSON-serializable dict.

    Array must have a numerical dtype. Datetime objects are currently
    not supported.

    Args:
        arr:  Numpy ndarray.

    Returns:
        JSON-serializable dict adhering the ``ndarray`` schema.
    """
    return {'__ndarray__': True, '__dtype__': arr.dtype.str,
            'data': arr.tolist()}



def generate_outpath(in_path: str, out_path: str = None,
                     suffix: str = None) -> str:
    """Generates file paths for feature und HMM output files.

    If ``out_path`` is ``None``, the basename of ``in_path`` is taken
    with the extension replaced by ``suffix``.

    Args:
        in_path:   Path to file under analysis.
        out_path:  Commandline argument.
        suffix:    File extension.

    Returns:
        Valid output path.
    """
    in_path = _pathlib.Path(in_path)
    if suffix is None:
        default_fname = '{}'.format(in_path.stem)
    else:
        default_fname = '{}.{}'.format(in_path.stem, suffix)

    if out_path is None:
        out_path = _pathlib.Path(default_fname)
    else:
        out_path = _pathlib.Path(out_path)
        if not out_path.suffix:
            out_path = out_path.joinpath(default_fname)
        if not out_path.parent.is_dir():
            print('Error. Path "{!s}" does not exist.'.format(out_path.parent))
            exit(10)
    return out_path


class PoissonHmmEncoder(ArrayEncoder):
    """JSON encoder for PoissonHmm.
    """
    def default(self, o):
        """Custon default JSON encoder. Properly handles <class 'PoissonHMM'>.

        Note: Falls back to ``ArrayEncoder`` for all types that do not implement
        a ``to_dict()`` method.

        Params:
            o (any)  Object to encode.

        Returns:
            (dict)
        """
        if isinstance(o, HMM):
            items = {}
            for attr in o.__slots__:
                try:
                    items[attr] = getattr(o, attr).to_dict()
                except AttributeError:
                    items[attr] = getattr(o, attr)
            return items
        return ArrayEncoder.default(self, o)


def dump_json(obj, path: _types.PathType = None) -> None:
    """Write ``obj`` to JSON.

    This function can handel numpy arrays.

    If ``path`` is None, this fucntion writes to stdout.  Otherwise, encoded
    object is written to ``path``.

    Args:
        obj  (any)         Object to be encoded.
        path (PathType)    Output file path.
    """
    if path is None:
        return _json.dumps(obj, cls=ArrayEncoder)
    else:
        path = _pathlib.Path(path)
        with path.open('w') as json_file:
            _json.dump(obj, json_file, cls=ArrayEncoder)


def load_json(path: _types.PathType = None) -> None:
    """Load JSON file.

    Args:
        path: Path to file.

    Returns:
        JSON file as FeatureSpace.
    """
    path = _pathlib.Path(path)
    with path.open('r') as fobj:
        data = _json.load(fobj, object_hook=_ndarray_hook)
    return container.FeatureSpace(**data)


class WavFileAccessControl:
    """Control initialization and access to the ``file`` attribute of class:``AudioData``.

    This assures that the path indeed points to a file, which has to be a .wav file. Otherwise
    an error is raised. The path to the file is saved as absolute path and the attribute is
    read-only.
    """

    def __init__(self):
        """Hi there!"""
        self.__attribute = {}

    def __get__(self, obj, objtype):
        return self.__attribute[obj]

    def __set__(self, obj, file_name):
        if obj not in self.__attribute.keys():
            _path = _pathlib.Path(file_name).resolve()
            if _path.exists():
                if _path.is_file():
                    if _path.suffix == '.wav':
                        self.__attribute[obj] = _path
                    else:
                        raise IOError('`{}` is not a .wav file.'
                                      .format(file_name))
                else:
                    raise IOError('`{}` is not a file.'.format(file_name))
            else:
                raise FileNotFoundError('`{}` does not exists.'
                                        .format(file_name))
        else:
            raise AttributeError('File name cannot be changed.')

    def __delete__(self, obj):
        del self.__attribute[obj]


@_contextmanager
def array_print_opt(*args, **kwargs):
    """Set print format for numpy arrays.

    Thanks to unutbu:
    https://stackoverflow.com/questions/2891790/how-to-pretty-print-a-
    numpy-array-without-scientific-notation-and-with-given-pre
    """
    std_options = _np.get_printoptions()
    _np.set_printoptions(*args, **kwargs)
    try:
        yield
    finally:
        _np.set_printoptions(**std_options)


def load(path: _types.PathType) -> Any:
    """Load a pickled file.

    Args:
        path    (str) Path to file.

    Returns:
        (object) unpickled object
    """
    path = _pathlib.Path(path)
    with path.open('rb') as file:
        data = pickle.load(file)
    return data

def repath(current_path: _types.PathType, new_path: _types.PathType,
           ext: str = None) -> _types.PathType:
    """Change the path and keep the file name. Optinally change the extension, too.

    Args:
        current_path:  The path to change.
        new_path:      The new path.
        ext:           Change file extension if ``ext`` is not None.

    Returns:
        New path.
    """
    current_path = _pathlib.Path(current_path)
    new_path = _pathlib.Path(new_path)
    stem = current_path.stem

    if ext is None:
        new_path = new_path.joinpath(current_path.name)
    else:
        ext = ext if ext.startswith('.') else '.' + ext
        new_path = new_path.joinpath(current_path.stem + ext)
    return new_path


def save(data: Any, path: _types.PathType):
    """Pickles data to path.

    Args:
        data    (Any)         Pickleable object.
        path    (str or Path) Path to safe the file.
    """
    path = _pathlib.Path(path)
    with path.open('wb') as file:
        pickle.dump(data, file)


def _ndarray_hook(inp: dict) -> Union[_np.ndarray, dict]:
    try:
        arr = decode_ndarray(inp)
        return arr
    except _jsonschema.ValidationError:
        return dict
