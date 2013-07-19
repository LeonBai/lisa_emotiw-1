"""
This files defines a Pylearn2 Dataset holding facetubes.
"""
# Basic Python packages
import functools

# External dependencies
import numpy as np

# In-house dependencies
import theano
from theano import config
from theano.gof.op import get_debug_values
from theano.sandbox.cuda.type import CudaNdarrayType
from theano.tensor import TensorType

from pylearn2.datasets import Dataset
from pylearn2.utils import safe_zip
from pylearn2.utils.data_specs import is_flat_specs
from pylearn2.utils.iteration import (FiniteDatasetIterator,
                                      resolve_iterator_class)
from pylearn2.space import CompositeSpace, Space, VectorSpace, Conv2DSpace
#from emotiw.scripts.mirzamom.conv3d.space import Conv3DSpace
# Current project


class FaceTubeSpace(Space):
    """Space for variable-length sequences of images.

    All the images in all sequences have the same dimensions and number
    of channels, but the length of different sequences may be different.
    Hence, this space is restricted to batch sizes of 1.
    """
    def __init__(self, shape, num_channels, axes=None):
        if axes is None:
            # 'b' indicates batch size, should always be 1
            # 't' indicates time steps
            # 0 is the image height,
            # 1 is the image width,
            # 'c' is the channel (for instance, R G or B)
            axes = ('b', 't', 0, 1, 'c')

        self.shape = tuple(shape)
        self.num_channels = num_channels
        self.axes = tuple(axes)

    def __str__(self):
        return 'FaceTubeSpace{shape=%s,num_channels=%s}' % (
                str(self.shape), str(self.num_channels))

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.shape == other.shape and
                self.num_channels == other.num_channels and
                self.axes == other.axes)

    def __hash__(self):
        return hash((type(self), self.shape, self.num_channels, self.axes))

    @functools.wraps(Space.get_origin)
    def get_origin(self):
        # the length of 't' will vary among examples, we use 1 here,
        # but it could change
        dims = {0: self.shape[0],
                1: self.shape[1],
                'c': self.num_channels,
                't': 1}
        shape = [dims[elem] for elem in self.axes if elem != 'b']
        return np.zeros(shape)

    @functools.wraps(Space.get_origin_batch)
    def get_origin_batch(self, n, dtype = None):
        if dtype is None:
            dtype = config.floatX

        assert n == 1, "batch processing not supported for face tubes"
        # the length of 't' will vary among examples, we use 1 here,
        # but it could change
        dims = {0: self.shape[0],
                1: self.shape[1],
                'c': self.num_channels,
                't': 1,
                'b': 1}
        shape = [dims[elem] for elem in self.axes]
        return np.zeros(shape, dtype = dtype)

    @functools.wraps(Space.make_theano_batch)
    def make_theano_batch(self, name=None, dtype=None, batch_size=None):
        if dtype is None:
            dtype = config.floatX

        broadcastable = [False] * 5
        broadcastable[self.axes.index('c')] = (self.num_channels == 1)
        broadcastable[self.axes.index('b')] = True
        broadcastable = tuple(broadcastable)

        rval = TensorType(dtype=dtype,
                          broadcastable=broadcastable)(name=name)
        if config.compute_test_value != 'off':
            rval.tag.test_value = self.get_origin_batch(n=1)

        return rval

    @functools.wraps(Space.batch_size)
    def batch_size(self, batch):
        self.validate(batch)
        return 1

    @functools.wraps(Space.np_batch_size)
    def np_batch_size(self, batch):
        self.np_validate(batch)
        return 1

    @functools.wraps(Space.validate)
    def validate(self, batch):
        if not isinstance(batch, theano.gof.Variable):
            raise TypeError("%s batches must be Theano Variables, got %s"
                            % (str(type(self)), str(type(batch))))
        if not isinstance(batch.type, (theano.tensor.TensorType,
                                       CudaNdarrayType)):
            raise TypeError()
        if batch.ndim != 5:
            raise ValueError()
        if not batch.broadcastable[self.axes.index('b')]:
            raise ValueError("%s batches should be broadcastable along the "
                             "'b' (batch size) dimension." % str(type(self)))
        for val in get_debug_values(batch):
            self.np_validate(val)

    @functools.wraps(Space.np_validate)
    def np_validate(self, batch):
        if (not isinstance(batch, np.ndarray)
                and type(batch) != 'CudaNdarray'):
            raise TypeError("The value of a %s batch should be a "
                            "numpy.ndarray, or CudaNdarray, but is %s."
                            % (str(type(self)), str(type(batch))))
        if batch.ndim != 5:
            raise ValueError("The value of a %s batch must be "
                             "5D, got %d dimensions for %s."
                             % (str(type(self)), batch.ndim, batch))

        d = self.axes.index('c')
        actual_channels = batch.shape[d]
        if actual_channels != self.num_channels:
            raise ValueError("Expected axis %d to be number of channels (%d) "
                             "but it is %d"
                             % (d, self.num_channels, actual_channels))
        assert batch.shape[self.axes.index('c')] == self.num_channels

        assert batch.shape[self.axes.index('b')] == 1

        for coord in [0, 1]:
            d = self.axes.index(coord)
            actual_shape = batch.shape[d]
            expected_shape = self.shape[coord]
            if actual_shape != expected_shape:
                raise ValueError(
                    "%s with shape %s and axes %s "
                    "expected dimension %s of a batch (%s) to have "
                    "length %s but it has %s"
                    % (str(type(self)), str(self.shape), str(self.axes),
                       str(d), str(batch), str(expected_shape),
                       str(actual_shape)))

    @functools.wraps(Space.np_format_as)
    def np_format_as(self, batch, space):
        self.np_validate(batch)

        if isinstance(space, FaceTubeSpace):
            assert len(self.axes) == 5
            assert len(space.axes) == 5
            if self.axes == space.axes:
                return batch
            new_axes = [self.axes.index(e) for e in space.axes]
            return batch.transpose(*new_axes)

        if isinstance(space, VectorSpace):
            # space.dim has to have the right size for current batch,
            # or be None
            prod_batch_shape = np.prod(batch.shape)
            if space.dim not in (None, prod_batch_shape):
                raise TypeError(
                    "%s cannot convert to a VectorSpace of a "
                    "different size (space.dim=%s, should be None or %s)"
                    % (str(type(self)), space.dim, prod_batch_shape))
            if self.axes[0] != 'b':
                # We need to ensure that the batch index goes on the first axis
                # before the reshape
                new_axes = ['b'] + [axis for axis in self.axes if axis != 'b']
                batch = batch.transpose(*[self.axes.index(axis)
                                          for axis in new_axes])
                #return batch.reshape((batch.shape[0], -1))
            return batch.reshape((batch.shape[0], np.prod(batch.shape)/batch.shape[0]))

        raise NotImplementedError("%s doesn't know how to format as %s"
                                  % (str(type(self)), str(type(space))))

    @functools.wraps(Space._format_as)
    def _format_as(self, batch, space):
        self.validate(batch)

        if isinstance(space, FaceTubeSpace):
            assert len(self.axes) == 5
            assert len(space.axes) == 5
            if self.axes == space.axes:
                return batch
            new_axes = [self.axes.index(e) for e in space.axes]
            return batch.transpose(*new_axes)

        if isinstance(space, VectorSpace):
            if self.axes[0] != 'b':
                # We need to ensure that the batch index goes on the first axis
                # before the reshape
                new_axes = ['b'] + [axis for axis in self.axes if axis != 'b']
                batch = batch.transpose(*[self.axes.index(axis)
                                          for axis in new_axes])
            # since batch size is one, we make t the batchsize
            if self.axes[1] != 't':
                # We need to ensure that the batch index goes on the first axis
                # before the reshape
                new_axes = ['b', 't'] + [axis for axis in self.axes if axis != 'b']
                batch = batch.transpose(*[self.axes.index(axis)
                                          for axis in new_axes])

                #return batch.reshape((batch.shape[1], -1))
            return batch.reshape((batch.shape[1], np.prod(batch.shape)/batch.shape[1]))

        if isinstance(space, Conv2DSpace):
            if self.axes[0] != 'b' or self.axes[1] != 't':
                new_axes = ['b', 't'] + [axis for axis in self.axes if axis not in ['b', 't']]
                batch = batch.transpose(*[self.axes.index(axis)
                                        for axis in new_axes])

            dims = {'b' : batch.shape[1], 'c' : space.num_channels, 0 : space.shape[0], 1 : space.shape[1]}
            if space.axes != space.default_axes:
                shape = [dims[ax] for ax in space.default_axes]
                batch = batch.reshape(shape)
                batch = batch.transpose(*[space.default_axes.index(ax) for ax in space.axes])
            return batch

        if isinstance(space, Conv3DSpace):
            if self.axes[0] != 'b' or self.axes[1] != 't':
                new_axes = ['b', 't'] + [axis for axis in self.axes if axis not in ['b', 't']]
                batch = batch.transpose(*[self.axes.index(axis)
                                        for axis in new_axes])

            if batch.shape[1] % space.sequence_length !=0:
                raise ValueError("Whole sequence length {} should be divisible by time steps {}".format(batch.shape[1], space.sequence_length))
            dims = {'b' : batch.shape[1] / space.sequence_length,
                    't': space.sequence_length,
                    'c' : space.num_channels,
                    0 : space.shape[0],
                    1 : space.shape[1]}
            if space.axes != space.default_axes:
                shape = [dims[ax] for ax in space.default_axes]
                batch = batch.reshape(shape)
                batch = batch.transpose(*[space.default_axes.index(ax) for ax in space.axes])
            return batch



        raise NotImplementedError("%s doesn't know how to format as %s"
                                  % (str(type(self)), str(type(space))))

    @functools.wraps(Space.get_total_dimension)
    def get_total_dimension(self):

        return self.shape[0] * self.shape[1] * self.num_channels

class FaceTubeDataset(Dataset):
    def get_data(self):
        return self.data

    def get_data_specs(self):
        return self.data_specs

    def iterator(self, mode=None, batch_size=None, num_batches=None,
                 rng=None, data_specs=None, return_tuple=False):
        if mode is None:
            if hasattr(self, '_iter_subset_class'):
                mode = self._iter_subset_class
            raise ValueError('iteration mode not provided and no default '
                             'mode set for %s' % str(self))
        else:
            mode = resolve_iterator_class(mode)

        if batch_size is None:
            batch_size = getattr(self, '_iter_batch_size', None)
        if num_batches is None:
            num_batches = getattr(self, '_iter_num_batches', None)
        if rng is None and mode.stochastic:
            rng = self.rng
        if data_specs is None:
            data_specs = getattr(self, '_iter_data_specs', None)

        # TODO: figure out where to to the scaling more cleanly.
        def list_to_scaled_array(batch):
            # batch is either a 4D ndarray, or a list of length 1
            # containing a 4D ndarray. Make it a 5D ndarray,
            # with shape 1 on the first dimension.
            # Also scale it from [0, 255] to [0, 1]
            if isinstance(batch, list):
                assert len(batch) == 1
                batch = batch[0]
            batch = batch.astype(config.floatX)
            batch /= 255.
            return batch[np.newaxis]

        convert_fns = []
        for space in data_specs[0].components:
            if (isinstance(space, FaceTubeSpace) and
                    space.axes[0] == 'b'):
                convert_fns.append(list_to_scaled_array)
            else:
                convert_fns.append(None)

        return FiniteDatasetIteratorVariableSize(
                self,
                mode(self.n_samples,
                     batch_size,
                     num_batches,
                     rng),
                data_specs=data_specs,
                return_tuple=return_tuple,
                convert_fns=convert_fns)


class FiniteDatasetIteratorVariableSize(FiniteDatasetIterator):
    def __init__(self, dataset, subset_iterator, data_specs=None,
                 return_tuple=False, convert_fns=None):
        """
        convert_fns: function or tuple of function, organized as
            in data_specs, to be applied on the raw batches of
            data. "None" can be used as placeholder for the identity.
        """
        self._deprecated_interface = False
        if data_specs is None:
            raise TypeError("data_specs not provided")
        self._data_specs = data_specs
        self._dataset = dataset
        self._subset_iterator = subset_iterator
        self._return_tuple = return_tuple

        # Keep only the needed sources in self._raw_data.
        # Remember what source they correspond to in self._source
        assert is_flat_specs(data_specs)

        dataset_space, dataset_source = self._dataset.get_data_specs()
        assert is_flat_specs((dataset_space, dataset_source))

        # the dataset's data spec is either a single (space, source) pair,
        # or a pair of (non-nested CompositeSpace, non-nested tuple).
        # We could build a mapping and call flatten(..., return_tuple=True)
        # but simply putting spaces, sources and data in tuples is simpler.
        if not isinstance(dataset_source, tuple):
            dataset_source = (dataset_source,)

        if not isinstance(dataset_space, CompositeSpace):
            dataset_sub_spaces = (dataset_space,)
        else:
            dataset_sub_spaces = dataset_space.components
        assert len(dataset_source) == len(dataset_sub_spaces)

        all_data = self._dataset.get_data()
        if not isinstance(all_data, tuple):
            all_data = (all_data,)

        space, source = data_specs
        if not isinstance(source, tuple):
            source = (source,)
        if not isinstance(space, CompositeSpace):
            sub_spaces = (space,)
        else:
            sub_spaces = space.components
        assert len(source) == len(sub_spaces)

        self._raw_data = tuple(all_data[dataset_source.index(s)]
                               for s in source)
        self._source = source

        if convert_fns is None:
            self._convert = [None for s in source]
        else:
            if not isinstance(convert_fns, (list, tuple)):
                convert_fns = (convert_fns,)
            assert len(convert_fns) == len(source)
            self._convert = list(convert_fns)

        for i, (so, sp) in enumerate(safe_zip(source, sub_spaces)):
            idx = dataset_source.index(so)
            dspace = dataset_sub_spaces[idx]

            # Compose the functions
            fn = self._convert[i]
            needs_cast = not (self._raw_data[i][0].dtype == config.floatX)
            if needs_cast:
                if fn is None:
                    fn = lambda batch: np.cast[config.floatX](batch)
                else:
                    fn = (lambda batch, prev_fn=fn:
                          np.cast[config.floatX](prev_fn(batch)))

            needs_format = not sp == dspace
            if needs_format:
                # "dspace" and "sp" have to be passed as parameters
                # to lambda, in order to capture their current value,
                # otherwise they would change in the next iteration
                # of the loop.
                if fn is None:
                    fn = (lambda batch, dspace=dspace, sp=sp:
                          dspace.np_format_as(batch, sp))
                else:
                    fn = (lambda batch, dspace=dspace, sp=sp, fn_=fn:
                          dspace.np_format_as(fn_(batch), sp))

            self._convert[i] = fn
