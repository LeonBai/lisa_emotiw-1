import warnings

try:
        import tables
except ImportError:
        warnings.warn("Couldn't import tables, so far SVHN is "
                            "only supported with PyTables")

from theano import config
from pylearn2.datasets import dense_design_matrix
from pylearn2.utils.iteration import SequentialSubsetIterator
import matplotlib.pyplot as plt


class Imagenet(dense_design_matrix.DenseDesignMatrixPyTables):
    mapper = {
        'train': 0,
        'test':  1,
        'valid': 2
    }

    def __init__(self,
            which_set,
            path_org,
            path,
            center,
            scale,
            start,
            stop,
            size_of_receptive_field,
            stride=1,
            imageShape=(256, 256),
            mode='r+',
            axes=('b', 0, 1, 'c'),
            preprocessor=None):

        assert which_set in self.mapper.keys()
        self.which_set = which_set
        self.__dict__.update(locals())

        del self.self

        self.size_of_receptive_field = size_of_receptive_field
        self.stride = stride

        self.mode = mode
        w, h = imageShape

        cout_w = (w - size_of_receptive_field[0]) / stride + 1
        cout_h = (h - size_of_receptive_field[1]) / stride + 1

        if cout_h < 0 or cout_w < 0:
            raise ValueError("Conv output size should not be less than 0.")

        h5file_org = tables.openFile(path_org, mode = 'r')

        assert start != None and stop != None
        if '/Data' in h5file_org.listNodes("/")[0]:
            x_data = h5file_org.getNode("/Data").x
        else:
            x_data = h5file_org.x

        #create new h5file at the specified path
        self.h5file = tables.openFile(path, mode = mode, title = "ImageNet Dataset")

        if self.h5file.__contains__('/Data'):
            self.h5file.removeNode('/', "Data", 1)

        data = self.h5file.createGroup(self.h5file.root, "Data", "Data")
        atom = tables.Float32Atom() if config.floatX == 'float32' else tables.Float64Atom()
        filters = tables.Filters(complib='blosc', complevel=5)

        X = self.h5file.createCArray(data, 'X', atom = atom, shape = ((stop-start, w*h)),
                                title = "Data values", filters = filters)

        y = self.h5file.createCArray(data, 'y', atom = atom, shape = ((stop-start, cout_w*cout_h)),
                                title = "Data targets", filters = filters)

        #copy data from original h5file
        X[:] = x_data[start:stop]
        self.X = X
        self.h5file.flush()

        # rescale or center if permitted
        if center and scale:
            data.X[:] -= 127.5
            data.X[:] /= 127.5
        elif center:
            data.X[:] -= 127.5
        elif scale:
            data.X[:] /= 255.0

        view_converter = dense_design_matrix.DefaultViewConverter((w, h, 1),
                                                                        axes)
        super(Imagenet, self).__init__(X = data.X, y = y,
                                    view_converter = view_converter)

        if preprocessor:
            can_fit =False
            if which_set in ['train']:
                can_fit = True
            preprocessor.apply(self, can_fit)

