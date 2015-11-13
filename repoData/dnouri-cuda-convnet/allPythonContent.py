__FILENAME__ = convdata
# Copyright (c) 2011, Alex Krizhevsky (akrizhevsky@gmail.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from data import *
import numpy.random as nr
import numpy as n
import random as r

class CIFARDataProvider(LabeledMemoryDataProvider):
    def __init__(self, data_dir, batch_range, init_epoch=1, init_batchnum=None, dp_params={}, test=False):
        LabeledMemoryDataProvider.__init__(self, data_dir, batch_range, init_epoch, init_batchnum, dp_params, test)
        self.data_mean = self.batch_meta['data_mean']
        self.num_colors = 3
        self.img_size = 32
        # Subtract the mean from the data and make sure that both data and
        # labels are in single-precision floating point.
        for d in self.data_dic:
            # This converts the data matrix to single precision and makes sure that it is C-ordered
            d['data'] = n.require((d['data'] - self.data_mean), dtype=n.single, requirements='C')
            d['labels'] = n.require(d['labels'].reshape((1, d['data'].shape[1])), dtype=n.single, requirements='C')

    def get_next_batch(self):
        epoch, batchnum, datadic = LabeledMemoryDataProvider.get_next_batch(self)
        return epoch, batchnum, [datadic['data'], datadic['labels']]

    # Returns the dimensionality of the two data matrices returned by get_next_batch
    # idx is the index of the matrix.
    def get_data_dims(self, idx=0):
        return self.img_size**2 * self.num_colors if idx == 0 else 1

    # Takes as input an array returned by get_next_batch
    # Returns a (numCases, imgSize, imgSize, 3) array which can be
    # fed to pylab for plotting.
    # This is used by shownet.py to plot test case predictions.
    def get_plottable_data(self, data):
        return n.require((data + self.data_mean).T.reshape(data.shape[1], 3, self.img_size, self.img_size).swapaxes(1,3).swapaxes(1,2) / 255.0, dtype=n.single)

class CroppedCIFARDataProvider(LabeledMemoryDataProvider):
    def __init__(self, data_dir, batch_range=None, init_epoch=1, init_batchnum=None, dp_params=None, test=False):
        LabeledMemoryDataProvider.__init__(self, data_dir, batch_range, init_epoch, init_batchnum, dp_params, test)

        self.border_size = dp_params['crop_border']
        self.inner_size = 32 - self.border_size*2
        self.multiview = dp_params['multiview_test'] and test
        self.num_views = 5*2
        self.data_mult = self.num_views if self.multiview else 1
        self.num_colors = 3

        for d in self.data_dic:
            d['data'] = n.require(d['data'], requirements='C')
            d['labels'] = n.require(n.tile(d['labels'].reshape((1, d['data'].shape[1])), (1, self.data_mult)), requirements='C')

        self.cropped_data = [n.zeros((self.get_data_dims(), self.data_dic[0]['data'].shape[1]*self.data_mult), dtype=n.single) for x in xrange(2)]

        self.batches_generated = 0
        self.data_mean = self.batch_meta['data_mean'].reshape((3,32,32))[:,self.border_size:self.border_size+self.inner_size,self.border_size:self.border_size+self.inner_size].reshape((self.get_data_dims(), 1))

    def get_next_batch(self):
        epoch, batchnum, datadic = LabeledMemoryDataProvider.get_next_batch(self)

        cropped = self.cropped_data[self.batches_generated % 2]

        self.__trim_borders(datadic['data'], cropped)
        cropped -= self.data_mean
        self.batches_generated += 1
        return epoch, batchnum, [cropped, datadic['labels']]

    def get_data_dims(self, idx=0):
        return self.inner_size**2 * 3 if idx == 0 else 1

    # Takes as input an array returned by get_next_batch
    # Returns a (numCases, imgSize, imgSize, 3) array which can be
    # fed to pylab for plotting.
    # This is used by shownet.py to plot test case predictions.
    def get_plottable_data(self, data):
        return n.require((data + self.data_mean).T.reshape(data.shape[1], 3, self.inner_size, self.inner_size).swapaxes(1,3).swapaxes(1,2) / 255.0, dtype=n.single)

    def __trim_borders(self, x, target):
        y = x.reshape(3, 32, 32, x.shape[1])

        if self.test: # don't need to loop over cases
            if self.multiview:
                start_positions = [(0,0),  (0, self.border_size*2),
                                   (self.border_size, self.border_size),
                                  (self.border_size*2, 0), (self.border_size*2, self.border_size*2)]
                end_positions = [(sy+self.inner_size, sx+self.inner_size) for (sy,sx) in start_positions]
                for i in xrange(self.num_views/2):
                    pic = y[:,start_positions[i][0]:end_positions[i][0],start_positions[i][1]:end_positions[i][1],:]
                    target[:,i * x.shape[1]:(i+1)* x.shape[1]] = pic.reshape((self.get_data_dims(),x.shape[1]))
                    target[:,(self.num_views/2 + i) * x.shape[1]:(self.num_views/2 +i+1)* x.shape[1]] = pic[:,:,::-1,:].reshape((self.get_data_dims(),x.shape[1]))
            else:
                pic = y[:,self.border_size:self.border_size+self.inner_size,self.border_size:self.border_size+self.inner_size, :] # just take the center for now
                target[:,:] = pic.reshape((self.get_data_dims(), x.shape[1]))
        else:
            for c in xrange(x.shape[1]): # loop over cases
                startY, startX = nr.randint(0,self.border_size*2 + 1), nr.randint(0,self.border_size*2 + 1)
                endY, endX = startY + self.inner_size, startX + self.inner_size
                pic = y[:,startY:endY,startX:endX, c]
                if nr.randint(2) == 0: # also flip the image with 50% probability
                    pic = pic[:,:,::-1]
                target[:,c] = pic.reshape((self.get_data_dims(),))

class DummyConvNetDataProvider(LabeledDummyDataProvider):
    def __init__(self, data_dim):
        LabeledDummyDataProvider.__init__(self, data_dim)

    def get_next_batch(self):
        epoch, batchnum, dic = LabeledDummyDataProvider.get_next_batch(self)

        dic['data'] = n.require(dic['data'].T, requirements='C')
        dic['labels'] = n.require(dic['labels'].T, requirements='C')

        return epoch, batchnum, [dic['data'], dic['labels']]

    # Returns the dimensionality of the two data matrices returned by get_next_batch
    def get_data_dims(self, idx=0):
        return self.batch_meta['num_vis'] if idx == 0 else 1

########NEW FILE########
__FILENAME__ = convnet
# Copyright (c) 2011, Alex Krizhevsky (akrizhevsky@gmail.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import numpy as n
import numpy.random as nr
from util import *
from data import *
from options import *
from gpumodel import *
import sys
import math as m
import layer as lay
from convdata import *
from os import linesep as NL
#import pylab as pl

class ConvNet(IGPUModel):
    def __init__(self, op, load_dic, dp_params={}):
        filename_options = []
        dp_params['multiview_test'] = op.get_value('multiview_test')
        dp_params['crop_border'] = op.get_value('crop_border')
        IGPUModel.__init__(self, "ConvNet", op, load_dic, filename_options, dp_params=dp_params)

    def import_model(self):
        lib_name = "convnet_"
        print "========================="
        print "Importing %s C++ module" % lib_name
        self.libmodel = __import__(lib_name)

    def init_model_lib(self):
        self.libmodel.initModel(self.layers, self.minibatch_size, self.device_ids[0])

    def init_model_state(self):
        ms = self.model_state
        if self.load_file:
            ms['layers'] = lay.LayerParser.parse_layers(self.layer_def, self.layer_params, self, ms['layers'])
        else:
            ms['layers'] = lay.LayerParser.parse_layers(self.layer_def, self.layer_params, self)
        self.layers_dic = dict(zip([l['name'] for l in ms['layers']], ms['layers']))

        logreg_name = self.op.get_value('logreg_name')
        if logreg_name:
            self.logreg_idx = self.get_layer_idx(logreg_name, check_type='cost.logreg')

        # Convert convolutional layers to local
        if len(self.op.get_value('conv_to_local')) > 0:
            for i, layer in enumerate(ms['layers']):
                if layer['type'] == 'conv' and layer['name'] in self.op.get_value('conv_to_local'):
                    lay.LocalLayerParser.conv_to_local(ms['layers'], i)
        # Decouple weight matrices
        if len(self.op.get_value('unshare_weights')) > 0:
            for name_str in self.op.get_value('unshare_weights'):
                if name_str:
                    name = lay.WeightLayerParser.get_layer_name(name_str)
                    if name is not None:
                        name, idx = name[0], name[1]
                        if name not in self.layers_dic:
                            raise ModelStateException("Layer '%s' does not exist; unable to unshare" % name)
                        layer = self.layers_dic[name]
                        lay.WeightLayerParser.unshare_weights(layer, ms['layers'], matrix_idx=idx)
                    else:
                        raise ModelStateException("Invalid layer name '%s'; unable to unshare." % name_str)
        self.op.set_value('conv_to_local', [], parse=False)
        self.op.set_value('unshare_weights', [], parse=False)

    def get_layer_idx(self, layer_name, check_type=None):
        try:
            layer_idx = [l['name'] for l in self.model_state['layers']].index(layer_name)
            if check_type:
                layer_type = self.model_state['layers'][layer_idx]['type']
                if layer_type != check_type:
                    raise ModelStateException("Layer with name '%s' has type '%s'; should be '%s'." % (layer_name, layer_type, check_type))
            return layer_idx
        except ValueError:
            raise ModelStateException("Layer with name '%s' not defined." % layer_name)

    def fill_excused_options(self):
        if self.op.get_value('check_grads'):
            self.op.set_value('save_path', '')
            self.op.set_value('train_batch_range', '0')
            self.op.set_value('test_batch_range', '0')
            self.op.set_value('data_path', '')

    # Make sure the data provider returned data in proper format
    def parse_batch_data(self, batch_data, train=True):
        if max(d.dtype != n.single for d in batch_data[2]):
            raise DataProviderException("All matrices returned by data provider must consist of single-precision floats.")
        return batch_data

    def start_batch(self, batch_data, train=True):
        data = batch_data[2]
        if self.check_grads:
            self.libmodel.checkGradients(data)
        elif not train and self.multiview_test:
            self.libmodel.startMultiviewTest(data, self.train_data_provider.num_views, self.logreg_idx)
        else:
            self.libmodel.startBatch(data, not train)

    def print_iteration(self):
        print "%d.%d..." % (self.epoch, self.batchnum),

    def print_train_time(self, compute_time_py):
        print "(%.3f sec)" % (compute_time_py)

    def print_costs(self, cost_outputs):
        costs, num_cases = cost_outputs[0], cost_outputs[1]
        for errname in costs.keys():
            costs[errname] = [(v/num_cases) for v in costs[errname]]
            print "%s: " % errname,
            print ", ".join("%6f" % v for v in costs[errname]),
            if sum(m.isnan(v) for v in costs[errname]) > 0 or sum(m.isinf(v) for v in costs[errname]):
                print "^ got nan or inf!"
                sys.exit(1)

    def print_train_results(self):
        self.print_costs(self.train_outputs[-1])

    def print_test_status(self):
        pass

    def print_test_results(self):
        print ""
        print "======================Test output======================"
        self.print_costs(self.test_outputs[-1])
        print ""
        print "-------------------------------------------------------",
        for i,l in enumerate(self.layers): # This is kind of hacky but will do for now.
            if 'weights' in l:
                if type(l['weights']) == n.ndarray:
                    print "%sLayer '%s' weights: %e [%e]" % (NL, l['name'], n.mean(n.abs(l['weights'])), n.mean(n.abs(l['weightsInc']))),
                elif type(l['weights']) == list:
                    print ""
                    print NL.join("Layer '%s' weights[%d]: %e [%e]" % (l['name'], i, n.mean(n.abs(w)), n.mean(n.abs(wi))) for i,(w,wi) in enumerate(zip(l['weights'],l['weightsInc']))),
                print "%sLayer '%s' biases: %e [%e]" % (NL, l['name'], n.mean(n.abs(l['biases'])), n.mean(n.abs(l['biasesInc']))),
        print ""

    def conditional_save(self):
        self.save_state()
        print "-------------------------------------------------------"
        print "Saved checkpoint to %s" % os.path.join(self.save_path, self.save_file)
        print "=======================================================",

    def aggregate_test_outputs(self, test_outputs):
        num_cases = sum(t[1] for t in test_outputs)
        for i in xrange(1 ,len(test_outputs)):
            for k,v in test_outputs[i][0].items():
                for j in xrange(len(v)):
                    test_outputs[0][0][k][j] += test_outputs[i][0][k][j]
        return (test_outputs[0][0], num_cases)

    @classmethod
    def get_options_parser(cls):
        op = IGPUModel.get_options_parser()
        op.add_option("mini", "minibatch_size", IntegerOptionParser, "Minibatch size", default=128)
        op.add_option("layer-def", "layer_def", StringOptionParser, "Layer definition file", set_once=True)
        op.add_option("layer-params", "layer_params", StringOptionParser, "Layer parameter file")
        op.add_option("check-grads", "check_grads", BooleanOptionParser, "Check gradients and quit?", default=0, excuses=['data_path','save_path','train_batch_range','test_batch_range'])
        op.add_option("multiview-test", "multiview_test", BooleanOptionParser, "Cropped DP: test on multiple patches?", default=0, requires=['logreg_name'])
        op.add_option("crop-border", "crop_border", IntegerOptionParser, "Cropped DP: crop border size", default=4, set_once=True)
        op.add_option("logreg-name", "logreg_name", StringOptionParser, "Cropped DP: logreg layer name (for --multiview-test)", default="")
        op.add_option("conv-to-local", "conv_to_local", ListOptionParser(StringOptionParser), "Convert given conv layers to unshared local", default=[])
        op.add_option("unshare-weights", "unshare_weights", ListOptionParser(StringOptionParser), "Unshare weight matrices in given layers", default=[])
        op.add_option("conserve-mem", "conserve_mem", BooleanOptionParser, "Conserve GPU memory (slower)?", default=0)

        op.delete_option('max_test_err')
        op.options["max_filesize_mb"].default = 0
        op.options["testing_freq"].default = 50
        op.options["num_epochs"].default = 50000
        op.options['dp_type'].default = None

        DataProvider.register_data_provider('cifar', 'CIFAR', CIFARDataProvider)
        DataProvider.register_data_provider('dummy-cn-n', 'Dummy ConvNet', DummyConvNetDataProvider)
        DataProvider.register_data_provider('cifar-cropped', 'Cropped CIFAR', CroppedCIFARDataProvider)

        return op

if __name__ == "__main__":
    #nr.seed(5)
    op = ConvNet.get_options_parser()

    op, load_dic = IGPUModel.parse_options(op)
    model = ConvNet(op, load_dic)
    model.start()

########NEW FILE########
__FILENAME__ = data
# Copyright (c) 2011, Alex Krizhevsky (akrizhevsky@gmail.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import numpy as n
from numpy.random import randn, rand, random_integers
import os
from util import *

BATCH_META_FILE = "batches.meta"

class DataProvider:
    BATCH_REGEX = re.compile('^data_batch_(\d+)(\.\d+)?$')
    def __init__(self, data_dir, batch_range=None, init_epoch=1, init_batchnum=None, dp_params={}, test=False):
        if batch_range == None:
            batch_range = DataProvider.get_batch_nums(data_dir)
        if init_batchnum is None or init_batchnum not in batch_range:
            init_batchnum = batch_range[0]

        self.data_dir = data_dir
        self.batch_range = batch_range
        self.curr_epoch = init_epoch
        self.curr_batchnum = init_batchnum
        self.dp_params = dp_params
        self.batch_meta = self.get_batch_meta(data_dir)
        self.data_dic = None
        self.test = test
        self.batch_idx = batch_range.index(init_batchnum)

    def get_next_batch(self):
        if self.data_dic is None or len(self.batch_range) > 1:
            self.data_dic = self.get_batch(self.curr_batchnum)
        epoch, batchnum = self.curr_epoch, self.curr_batchnum
        self.advance_batch()

        return epoch, batchnum, self.data_dic

    def __add_subbatch(self, batch_num, sub_batchnum, batch_dic):
        subbatch_path = "%s.%d" % (os.path.join(self.data_dir, self.get_data_file_name(batch_num)), sub_batchnum)
        if os.path.exists(subbatch_path):
            sub_dic = unpickle(subbatch_path)
            self._join_batches(batch_dic, sub_dic)
        else:
            raise IndexError("Sub-batch %d.%d does not exist in %s" % (batch_num,sub_batchnum, self.data_dir))

    def _join_batches(self, main_batch, sub_batch):
        main_batch['data'] = n.r_[main_batch['data'], sub_batch['data']]

    def get_batch(self, batch_num):
        if os.path.exists(self.get_data_file_name(batch_num) + '.1'): # batch in sub-batches
            dic = unpickle(self.get_data_file_name(batch_num) + '.1')
            sb_idx = 2
            while True:
                try:
                    self.__add_subbatch(batch_num, sb_idx, dic)
                    sb_idx += 1
                except IndexError:
                    break
        else:
            dic = unpickle(self.get_data_file_name(batch_num))
        return dic

    def get_data_dims(self):
        return self.batch_meta['num_vis']

    def advance_batch(self):
        self.batch_idx = self.get_next_batch_idx()
        self.curr_batchnum = self.batch_range[self.batch_idx]
        if self.batch_idx == 0: # we wrapped
            self.curr_epoch += 1

    def get_next_batch_idx(self):
        return (self.batch_idx + 1) % len(self.batch_range)

    def get_next_batch_num(self):
        return self.batch_range[self.get_next_batch_idx()]

    # get filename of current batch
    def get_data_file_name(self, batchnum=None):
        if batchnum is None:
            batchnum = self.curr_batchnum
        return os.path.join(self.data_dir, 'data_batch_%d' % batchnum)

    @classmethod
    def get_instance(cls, data_dir, batch_range=None, init_epoch=1, init_batchnum=None, type="default", dp_params={}, test=False):
        # why the fuck can't i reference DataProvider in the original definition?
        #cls.dp_classes['default'] = DataProvider
        type = type or DataProvider.get_batch_meta(data_dir)['dp_type'] # allow data to decide data provider
        if type.startswith("dummy-"):
            name = "-".join(type.split('-')[:-1]) + "-n"
            if name not in dp_types:
                raise DataProviderException("No such data provider: %s" % type)
            _class = dp_classes[name]
            dims = int(type.split('-')[-1])
            return _class(dims)
        elif type in dp_types:
            _class = dp_classes[type]
            return _class(data_dir, batch_range, init_epoch, init_batchnum, dp_params, test)

        raise DataProviderException("No such data provider: %s" % type)

    @classmethod
    def register_data_provider(cls, name, desc, _class):
        if name in dp_types:
            raise DataProviderException("Data provider %s already registered" % name)
        dp_types[name] = desc
        dp_classes[name] = _class

    @staticmethod
    def get_batch_meta(data_dir):
        return unpickle(os.path.join(data_dir, BATCH_META_FILE))

    @staticmethod
    def get_batch_filenames(srcdir):
        return sorted([f for f in os.listdir(srcdir) if DataProvider.BATCH_REGEX.match(f)], key=alphanum_key)

    @staticmethod
    def get_batch_nums(srcdir):
        names = DataProvider.get_batch_filenames(srcdir)
        return sorted(list(set(int(DataProvider.BATCH_REGEX.match(n).group(1)) for n in names)))

    @staticmethod
    def get_num_batches(srcdir):
        return len(DataProvider.get_batch_nums(srcdir))

class DummyDataProvider(DataProvider):
    def __init__(self, data_dim):
        #self.data_dim = data_dim
        self.batch_range = [1]
        self.batch_meta = {'num_vis': data_dim, 'data_in_rows':True}
        self.curr_epoch = 1
        self.curr_batchnum = 1
        self.batch_idx = 0

    def get_next_batch(self):
        epoch,  batchnum = self.curr_epoch, self.curr_batchnum
        self.advance_batch()
        data = rand(512, self.get_data_dims()).astype(n.single)
        return self.curr_epoch, self.curr_batchnum, {'data':data}


class LabeledDummyDataProvider(DummyDataProvider):
    def __init__(self, data_dim, num_classes=10, num_cases=512):
        #self.data_dim = data_dim
        self.batch_range = [1]
        self.batch_meta = {'num_vis': data_dim,
                           'label_names': [str(x) for x in range(num_classes)],
                           'data_in_rows':True}
        self.num_cases = num_cases
        self.num_classes = num_classes
        self.curr_epoch = 1
        self.curr_batchnum = 1
        self.batch_idx=0

    def get_num_classes(self):
        return self.num_classes

    def get_next_batch(self):
        epoch,  batchnum = self.curr_epoch, self.curr_batchnum
        self.advance_batch()
        data = rand(self.num_cases, self.get_data_dims()).astype(n.single) # <--changed to rand
        labels = n.require(n.c_[random_integers(0,self.num_classes-1,self.num_cases)], requirements='C', dtype=n.single)

        return self.curr_epoch, self.curr_batchnum, {'data':data, 'labels':labels}

class MemoryDataProvider(DataProvider):
    def __init__(self, data_dir, batch_range, init_epoch=1, init_batchnum=None, dp_params=None, test=False):
        DataProvider.__init__(self, data_dir, batch_range, init_epoch, init_batchnum, dp_params, test)
        self.data_dic = []
        for i in self.batch_range:
            self.data_dic += [self.get_batch(i)]

    def get_next_batch(self):
        epoch, batchnum = self.curr_epoch, self.curr_batchnum
        self.advance_batch()

        return epoch, batchnum, self.data_dic[batchnum - self.batch_range[0]]

class LabeledDataProvider(DataProvider):
    def __init__(self, data_dir, batch_range=None, init_epoch=1, init_batchnum=None, dp_params={}, test=False):
        DataProvider.__init__(self, data_dir, batch_range, init_epoch, init_batchnum, dp_params, test)

    def get_num_classes(self):
        return len(self.batch_meta['label_names'])

class LabeledMemoryDataProvider(LabeledDataProvider):
    def __init__(self, data_dir, batch_range, init_epoch=1, init_batchnum=None, dp_params={}, test=False):
        LabeledDataProvider.__init__(self, data_dir, batch_range, init_epoch, init_batchnum, dp_params, test)
        self.data_dic = []
        for i in batch_range:
            self.data_dic += [unpickle(self.get_data_file_name(i))]
            self.data_dic[-1]["labels"] = n.c_[n.require(self.data_dic[-1]['labels'], dtype=n.single)]

    def get_next_batch(self):
        epoch, batchnum = self.curr_epoch, self.curr_batchnum
        self.advance_batch()
        bidx = batchnum - self.batch_range[0]
        return epoch, batchnum, self.data_dic[bidx]

dp_types = {"default": "The default data provider; loads one batch into memory at a time",
            "memory": "Loads the entire dataset into memory",
            "labeled": "Returns data and labels (used by classifiers)",
            "labeled-memory": "Combination labeled + memory",
            "dummy-n": "Dummy data provider for n-dimensional data",
            "dummy-labeled-n": "Labeled dummy data provider for n-dimensional data"}
dp_classes = {"default": DataProvider,
              "memory": MemoryDataProvider,
              "labeled": LabeledDataProvider,
              "labeled-memory": LabeledMemoryDataProvider,
              "dummy-n": DummyDataProvider,
              "dummy-labeled-n": LabeledDummyDataProvider}

class DataProviderException(Exception):
    pass

########NEW FILE########
__FILENAME__ = gpumodel
# Copyright (c) 2011, Alex Krizhevsky (akrizhevsky@gmail.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import numpy as n
import os
from time import time, asctime, localtime, strftime
from numpy.random import randn, rand
from numpy import s_, dot, tile, zeros, ones, zeros_like, array, ones_like
from util import *
from data import *
from options import *
from math import ceil, floor, sqrt
from data import DataProvider, dp_types
import sys
import shutil
import platform
from os import linesep as NL

class ModelStateException(Exception):
    pass

# GPU Model interface
class IGPUModel:
    def __init__(self, model_name, op, load_dic, filename_options=None, dp_params={}):
        # these are input parameters
        self.model_name = model_name
        self.op = op
        self.options = op.options
        self.load_dic = load_dic
        self.filename_options = filename_options
        self.dp_params = dp_params
        self.get_gpus()
        self.fill_excused_options()
        #assert self.op.all_values_given()

        for o in op.get_options_list():
            setattr(self, o.name, o.value)

        # these are things that the model must remember but they're not input parameters
        if load_dic:
            self.model_state = load_dic["model_state"]
            self.save_file = self.options["load_file"].value
            if not os.path.isdir(self.save_file):
                self.save_file = os.path.dirname(self.save_file)
        else:
            self.model_state = {}
            if filename_options is not None:
                self.save_file = model_name + "_" + '_'.join(['%s_%s' % (char, self.options[opt].get_str_value()) for opt, char in filename_options]) + '_' + strftime('%Y-%m-%d_%H.%M.%S')
            self.model_state["train_outputs"] = []
            self.model_state["test_outputs"] = []
            self.model_state["epoch"] = 1
            self.model_state["batchnum"] = self.train_batch_range[0]

        self.init_data_providers()
        if load_dic:
            self.train_data_provider.advance_batch()

        # model state often requries knowledge of data provider, so it's initialized after
        try:
            self.init_model_state()
        except ModelStateException, e:
            print e
            sys.exit(1)
        for var, val in self.model_state.iteritems():
            setattr(self, var, val)

        self.import_model()
        self.init_model_lib()

    def import_model(self):
        print "========================="
        print "Importing %s C++ module" % ('_' + self.model_name)
        self.libmodel = __import__('_' + self.model_name)

    def fill_excused_options(self):
        pass

    def init_data_providers(self):
        self.dp_params['convnet'] = self
        try:
            self.test_data_provider = DataProvider.get_instance(self.data_path, self.test_batch_range,
                                                                type=self.dp_type, dp_params=self.dp_params, test=True)
            self.train_data_provider = DataProvider.get_instance(self.data_path, self.train_batch_range,
                                                                     self.model_state["epoch"], self.model_state["batchnum"],
                                                                     type=self.dp_type, dp_params=self.dp_params, test=False)
        except DataProviderException, e:
            print "Unable to create data provider: %s" % e
            self.print_data_providers()
            sys.exit()

    def init_model_state(self):
        pass

    def init_model_lib(self):
        pass

    def start(self):
        if self.test_only:
            self.test_outputs += [self.get_test_error()]
            self.print_test_results()
            sys.exit(0)
        self.train()

    def train(self):
        print "========================="
        print "Training %s" % self.model_name
        self.op.print_values()
        print "========================="
        self.print_model_state()
        print "Running on CUDA device(s) %s" % ", ".join("%d" % d for d in self.device_ids)
        print "Current time: %s" % asctime(localtime())
        print "Saving checkpoints to %s" % os.path.join(self.save_path, self.save_file)
        print "========================="
        next_data = self.get_next_batch()
        while self.epoch <= self.num_epochs:
            data = next_data
            self.epoch, self.batchnum = data[0], data[1]
            self.print_iteration()
            sys.stdout.flush()

            compute_time_py = time()
            self.start_batch(data)

            # load the next batch while the current one is computing
            next_data = self.get_next_batch()

            batch_output = self.finish_batch()
            self.train_outputs += [batch_output]
            self.print_train_results()

            if self.get_num_batches_done() % self.testing_freq == 0:
                self.sync_with_host()
                self.test_outputs += [self.get_test_error()]
                self.print_test_results()
                self.print_test_status()
                self.conditional_save()

            self.print_train_time(time() - compute_time_py)
        self.cleanup()

    def cleanup(self):
        sys.exit(0)

    def sync_with_host(self):
        self.libmodel.syncWithHost()

    def print_model_state(self):
        pass

    def get_num_batches_done(self):
        return len(self.train_batch_range) * (self.epoch - 1) + self.batchnum - self.train_batch_range[0] + 1

    def get_next_batch(self, train=True):
        dp = self.train_data_provider
        if not train:
            dp = self.test_data_provider
        return self.parse_batch_data(dp.get_next_batch(), train=train)

    def parse_batch_data(self, batch_data, train=True):
        return batch_data[0], batch_data[1], batch_data[2]['data']

    def start_batch(self, batch_data, train=True):
        self.libmodel.startBatch(batch_data[2], not train)

    def finish_batch(self):
        return self.libmodel.finishBatch()

    def print_iteration(self):
        print "\t%d.%d..." % (self.epoch, self.batchnum),

    def print_train_time(self, compute_time_py):
        print "(%.3f sec)" % (compute_time_py)

    def print_train_results(self):
        batch_error = self.train_outputs[-1][0]
        if not (batch_error > 0 and batch_error < 2e20):
            print "Crazy train error: %.6f" % batch_error
            self.cleanup()

        print "Train error: %.6f " % (batch_error),

    def print_test_results(self):
        batch_error = self.test_outputs[-1][0]
        print "%s\t\tTest error: %.6f" % (NL, batch_error),

    def print_test_status(self):
        status = (len(self.test_outputs) == 1 or self.test_outputs[-1][0] < self.test_outputs[-2][0]) and "ok" or "WORSE"
        print status,

    def conditional_save(self):
        batch_error = self.test_outputs[-1][0]
        if batch_error > 0 and batch_error < self.max_test_err:
            self.save_state()
        else:
            print "\tTest error > %g, not saving." % self.max_test_err,

    def aggregate_test_outputs(self, test_outputs):
        test_error = tuple([sum(t[r] for t in test_outputs) / (1 if self.test_one else len(self.test_batch_range)) for r in range(len(test_outputs[-1]))])
        return test_error

    def get_test_error(self):
        next_data = self.get_next_batch(train=False)
        test_outputs = []
        while True:
            data = next_data
            self.start_batch(data, train=False)
            load_next = not self.test_one and data[1] < self.test_batch_range[-1]
            if load_next: # load next batch
                next_data = self.get_next_batch(train=False)
            test_outputs += [self.finish_batch()]
            if self.test_only: # Print the individual batch results for safety
                print "batch %d: %s" % (data[1], str(test_outputs[-1]))
            if not load_next:
                break
            sys.stdout.flush()

        return self.aggregate_test_outputs(test_outputs)

    def set_var(self, var_name, var_val):
        setattr(self, var_name, var_val)
        self.model_state[var_name] = var_val
        return var_val

    def get_var(self, var_name):
        return self.model_state[var_name]

    def has_var(self, var_name):
        return var_name in self.model_state

    def save_state(self):
        for att in self.model_state:
            if hasattr(self, att):
                self.model_state[att] = getattr(self, att)

        dic = {"model_state": self.model_state,
               "op": self.op}

        checkpoint_dir = os.path.join(self.save_path, self.save_file)
        checkpoint_file = "%d.%d" % (self.epoch, self.batchnum)
        checkpoint_file_full_path = os.path.join(checkpoint_dir, checkpoint_file)
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)

        pickle(checkpoint_file_full_path, dic,compress=self.zip_save)

        for f in sorted(os.listdir(checkpoint_dir), key=alphanum_key):
            if sum(os.path.getsize(os.path.join(checkpoint_dir, f2)) for f2 in os.listdir(checkpoint_dir)) > self.max_filesize_mb*1024*1024 and f != checkpoint_file:
                os.remove(os.path.join(checkpoint_dir, f))
            else:
                break

    @staticmethod
    def load_checkpoint(load_dir):
        if os.path.isdir(load_dir):
            return unpickle(os.path.join(load_dir, sorted(os.listdir(load_dir), key=alphanum_key)[-1]))
        return unpickle(load_dir)

    @staticmethod
    def get_options_parser():
        op = OptionsParser()
        op.add_option("f", "load_file", StringOptionParser, "Load file", default="", excuses=OptionsParser.EXCLUDE_ALL)
        op.add_option("train-range", "train_batch_range", RangeOptionParser, "Data batch range: training")
        op.add_option("test-range", "test_batch_range", RangeOptionParser, "Data batch range: testing")
        op.add_option("data-provider", "dp_type", StringOptionParser, "Data provider", default="default")
        op.add_option("test-freq", "testing_freq", IntegerOptionParser, "Testing frequency", default=25)
        op.add_option("epochs", "num_epochs", IntegerOptionParser, "Number of epochs", default=500)
        op.add_option("data-path", "data_path", StringOptionParser, "Data path")
        op.add_option("save-path", "save_path", StringOptionParser, "Save path")
        op.add_option("max-filesize", "max_filesize_mb", IntegerOptionParser, "Maximum save file size (MB)", default=5000)
        op.add_option("max-test-err", "max_test_err", FloatOptionParser, "Maximum test error for saving")
        op.add_option("num-gpus", "num_gpus", IntegerOptionParser, "Number of GPUs", default=1)
        op.add_option("test-only", "test_only", BooleanOptionParser, "Test and quit?", default=0)
        op.add_option("zip-save", "zip_save", BooleanOptionParser, "Compress checkpoints?", default=0)
        op.add_option("test-one", "test_one", BooleanOptionParser, "Test on one batch at a time?", default=1)
        op.add_option("gpu", "gpu", ListOptionParser(IntegerOptionParser), "GPU override", default=OptionExpression("[-1] * num_gpus"))
        return op

    @staticmethod
    def print_data_providers():
        print "Available data providers:"
        for dp, desc in dp_types.iteritems():
            print "    %s: %s" % (dp, desc)

    def get_gpus(self):
        self.device_ids = [get_gpu_lock(g) for g in self.op.get_value('gpu')]
        if GPU_LOCK_NO_LOCK in self.device_ids:
            print "Not enough free GPUs!"
            sys.exit()

    @staticmethod
    def parse_options(op):
        try:
            load_dic = None
            options = op.parse()
            if options["load_file"].value_given:
                load_dic = IGPUModel.load_checkpoint(options["load_file"].value)
                old_op = load_dic["op"]
                old_op.merge_from(op)
                op = old_op
            op.eval_expr_defaults()
            return op, load_dic
        except OptionMissingException, e:
            print e
            op.print_usage()
        except OptionException, e:
            print e
        except UnpickleError, e:
            print "Error loading checkpoint:"
            print e
        sys.exit()


########NEW FILE########
__FILENAME__ = layer
# Copyright (c) 2011, Alex Krizhevsky (akrizhevsky@gmail.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# 
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from math import exp
import sys
import ConfigParser as cfg
import os
import numpy as n
import numpy.random as nr
from math import ceil, floor
from ordereddict import OrderedDict
from os import linesep as NL
from options import OptionsParser
import re

class LayerParsingError(Exception):
    pass

# A neuron that doesn't take parameters
class NeuronParser:
    def __init__(self, type, func_str, uses_acts=True, uses_inputs=True):
        self.type = type
        self.func_str = func_str
        self.uses_acts = uses_acts  
        self.uses_inputs = uses_inputs
        
    def parse(self, type):
        if type == self.type:
            return {'type': self.type,
                    'params': {},
                    'usesActs': self.uses_acts,
                    'usesInputs': self.uses_inputs}
        return None
    
# A neuron that takes parameters
class ParamNeuronParser(NeuronParser):
    neuron_regex = re.compile(r'^\s*(\w+)\s*\[\s*(\w+(\s*,\w+)*)\s*\]\s*$')
    def __init__(self, type, func_str, uses_acts=True, uses_inputs=True):
        NeuronParser.__init__(self, type, func_str, uses_acts, uses_inputs)
        m = self.neuron_regex.match(type)
        self.base_type = m.group(1)
        self.param_names = m.group(2).split(',')
        assert len(set(self.param_names)) == len(self.param_names)
        
    def parse(self, type):
        m = re.match(r'^%s\s*\[([\d,\.\s\-e]*)\]\s*$' % self.base_type, type)
        if m:
            try:
                param_vals = [float(v.strip()) for v in m.group(1).split(',')]
                if len(param_vals) == len(self.param_names):
                    return {'type': self.base_type,
                            'params': dict(zip(self.param_names, param_vals)),
                            'usesActs': self.uses_acts,
                            'usesInputs': self.uses_inputs}
            except TypeError:
                pass
        return None

class AbsTanhNeuronParser(ParamNeuronParser):
    def __init__(self):
        ParamNeuronParser.__init__(self, 'abstanh[a,b]', 'f(x) = a * |tanh(b * x)|')
        
    def parse(self, type):
        dic = ParamNeuronParser.parse(self, type)
        # Make b positive, since abs(tanh(bx)) = abs(tanh(-bx)) and the C++ code
        # assumes b is positive.
        if dic:
            dic['params']['b'] = abs(dic['params']['b'])
        return dic

# Subclass that throws more convnet-specific exceptions than the default
class MyConfigParser(cfg.SafeConfigParser):
    def safe_get(self, section, option, f=cfg.SafeConfigParser.get, typestr=None, default=None):
        try:
            return f(self, section, option)
        except cfg.NoOptionError, e:
            if default is not None:
                return default
            raise LayerParsingError("Layer '%s': required parameter '%s' missing" % (section, option))
        except ValueError, e:
            if typestr is None:
                raise e
            raise LayerParsingError("Layer '%s': parameter '%s' must be %s" % (section, option, typestr))
        
    def safe_get_list(self, section, option, f=str, typestr='strings', default=None):
        v = self.safe_get(section, option, default=default)
        if type(v) == list:
            return v
        try:
            return [f(x.strip()) for x in v.split(',')]
        except:
            raise LayerParsingError("Layer '%s': parameter '%s' must be ','-delimited list of %s" % (section, option, typestr))
        
    def safe_get_int(self, section, option, default=None):
        return self.safe_get(section, option, f=cfg.SafeConfigParser.getint, typestr='int', default=default)
        
    def safe_get_float(self, section, option, default=None):
        return self.safe_get(section, option, f=cfg.SafeConfigParser.getfloat, typestr='float', default=default)
    
    def safe_get_bool(self, section, option, default=None):
        return self.safe_get(section, option, f=cfg.SafeConfigParser.getboolean, typestr='bool', default=default)
    
    def safe_get_float_list(self, section, option, default=None):
        return self.safe_get_list(section, option, float, typestr='floats', default=default)
    
    def safe_get_int_list(self, section, option, default=None):
        return self.safe_get_list(section, option, int, typestr='ints', default=default)
    
    def safe_get_bool_list(self, section, option, default=None):
        return self.safe_get_list(section, option, lambda x: x.lower() in ('true', '1'), typestr='bools', default=default)

# A class that implements part of the interface of MyConfigParser
class FakeConfigParser(object):
    def __init__(self, dic):
        self.dic = dic

    def safe_get(self, section, option, default=None):
        return self.dic[option]
        

class LayerParser:
    def __init__(self):
        self.dic = {}
        self.set_defaults()
        
    # Post-processing step -- this is called after all layers have been initialized
    def optimize(self, layers):
        self.dic['actsTarget'] = -1
        self.dic['actsGradTarget'] = -1
    
    # Add parameters from layer parameter file
    def add_params(self, mcp):
        dic, name = self.dic, self.dic['name']
        dic['dropout'] = 0.0
        if name in mcp.sections():
            dic['dropout'] = mcp.safe_get_float(name, 'dropout', default=0.0)
    
    def init(self, dic):
        self.dic = dic
        return self
    
    def set_defaults(self):
        self.dic['outputs'] = 0
        self.dic['parser'] = self
        self.dic['requiresParams'] = False
        # Does this layer use its own activity matrix
        # for some purpose other than computing its output?
        # Usually, this will only be true for layers that require their
        # own activity matrix for gradient computations. For example, layers
        # with logistic units must compute the gradient y * (1 - y), where y is 
        # the activity matrix.
        # 
        # Layers that do not not use their own activity matrix should advertise
        # this, since this will enable memory-saving matrix re-use optimizations.
        #
        # The default value of this property is True, for safety purposes.
        # If a layer advertises that it does not use its own activity matrix when
        # in fact it does, bad things will happen.
        self.dic['usesActs'] = True
        
        # Does this layer use the activity matrices of its input layers
        # for some purpose other than computing its output?
        #
        # Again true by default for safety
        self.dic['usesInputs'] = True
        
        # Force this layer to use its own activity gradient matrix,
        # instead of borrowing one from one of its inputs.
        # 
        # This should be true for layers where the mapping from output
        # gradient to input gradient is non-elementwise.
        self.dic['forceOwnActs'] = True
        
        # Does this layer need the gradient at all?
        # Should only be true for layers with parameters (weights).
        self.dic['gradConsumer'] = False
        
    def parse(self, name, mcp, prev_layers, model=None):
        self.prev_layers = prev_layers
        self.dic['name'] = name
        self.dic['type'] = mcp.safe_get(name, 'type')

        return self.dic  

    def verify_float_range(self, v, param_name, _min, _max):
        self.verify_num_range(v, param_name, _min, _max, strconv=lambda x: '%.3f' % x)

    def verify_num_range(self, v, param_name, _min, _max, strconv=lambda x:'%d' % x):
        if type(v) == list:
            for i,vv in enumerate(v):
                self._verify_num_range(vv, param_name, _min, _max, i, strconv=strconv)
        else:
            self._verify_num_range(v, param_name, _min, _max, strconv=strconv)
    
    def _verify_num_range(self, v, param_name, _min, _max, input=-1, strconv=lambda x:'%d' % x):
        layer_name = self.dic['name'] if input < 0 else '%s[%d]' % (self.dic['name'], input)
        if _min is not None and _max is not None and (v < _min or v > _max):
            raise LayerParsingError("Layer '%s': parameter '%s' must be in the range %s-%s" % (layer_name, param_name, strconv(_min), strconv(_max)))
        elif _min is not None and v < _min:
            raise LayerParsingError("Layer '%s': parameter '%s' must be greater than or equal to %s" % (layer_name, param_name,  strconv(_min)))
        elif _max is not None and v > _max:
            raise LayerParsingError("Layer '%s': parameter '%s' must be smaller than or equal to %s" % (layer_name, param_name,  strconv(_max)))
    
    def verify_divisible(self, value, div, value_name, div_name=None, input_idx=0):
        layer_name = self.dic['name'] if len(self.dic['inputs']) == 0 else '%s[%d]' % (self.dic['name'], input_idx)
        if value % div != 0:
            raise LayerParsingError("Layer '%s': parameter '%s' must be divisible by %s" % (layer_name, value_name, str(div) if div_name is None else "'%s'" % div_name))
        
    def verify_str_in(self, value, lst):
        if value not in lst:
            raise LayerParsingError("Layer '%s': parameter '%s' must be one of %s" % (self.dic['name'], value, ", ".join("'%s'" % s for s in lst)))
        
    def verify_int_in(self, value, lst):
        if value not in lst:
            raise LayerParsingError("Layer '%s': parameter '%s' must be one of %s" % (self.dic['name'], value, ", ".join("'%d'" % s for s in lst)))

    # This looks for neuron=x arguments in various layers, and creates
    # separate layer definitions for them.
    @staticmethod
    def detach_neuron_layers(layers):
        layers_new = []
        for i, l in enumerate(layers):
            layers_new += [l]
            if l['type'] != 'neuron' and 'neuron' in l and l['neuron']:
                NeuronLayerParser().detach_neuron_layer(i, layers, layers_new)
        return layers_new
                
    @staticmethod
    def parse_layers(layer_cfg_path, param_cfg_path, model, layers=[]):
        try:
            if not os.path.exists(layer_cfg_path):
                raise LayerParsingError("Layer definition file '%s' does not exist" % layer_cfg_path)
            if not os.path.exists(param_cfg_path):
                raise LayerParsingError("Layer parameter file '%s' does not exist" % param_cfg_path)
            if len(layers) == 0:
                mcp = MyConfigParser(dict_type=OrderedDict)
                mcp.read([layer_cfg_path])
                for name in mcp.sections():
                    if not mcp.has_option(name, 'type'):
                        raise LayerParsingError("Layer '%s': no type given" % name)
                    ltype = mcp.safe_get(name, 'type')
                    if ltype not in layer_parsers:
                        raise LayerParsingError("Layer '%s': Unknown layer type: '%s'" % (name, ltype))
                    layers += [layer_parsers[ltype]().parse(name, mcp, layers, model)]
                
                layers = LayerParser.detach_neuron_layers(layers)
                for l in layers:
                    lp = layer_parsers[l['type']]()
                    l['parser'].optimize(layers)
                    del l['parser']
                    
                for l in layers:
                    if not l['type'].startswith('cost.'):
                        found = max(l['name'] in [layers[n]['name'] for n in l2['inputs']] for l2 in layers if 'inputs' in l2)
                        if not found:
                            raise LayerParsingError("Layer '%s' of type '%s' is unused" % (l['name'], l['type']))
            
            mcp = MyConfigParser(dict_type=OrderedDict)
            mcp.read([param_cfg_path])
            
            for l in layers:
                if not mcp.has_section(l['name']) and l['requiresParams']:
                    raise LayerParsingError("Layer '%s' of type '%s' requires extra parameters, but none given in file '%s'." % (l['name'], l['type'], param_cfg_path))
                lp = layer_parsers[l['type']]().init(l)
                lp.add_params(mcp)
                lp.dic['conserveMem'] = model.op.get_value('conserve_mem')
        except LayerParsingError, e:
            print e
            sys.exit(1)
        return layers
        
    @staticmethod
    def register_layer_parser(ltype, cls):
        if ltype in layer_parsers:
            raise LayerParsingError("Layer type '%s' already registered" % ltype)
        layer_parsers[ltype] = cls

# Any layer that takes an input (i.e. non-data layer)
class LayerWithInputParser(LayerParser):
    def __init__(self, num_inputs=-1):
        LayerParser.__init__(self)
        self.num_inputs = num_inputs

    def verify_num_params(self, params):
        for param in params:
            if len(self.dic[param]) != len(self.dic['inputs']):
                raise LayerParsingError("Layer '%s': %s list length does not match number of inputs" % (self.dic['name'], param))        
    
    def optimize(self, layers):
        LayerParser.optimize(self, layers)
        dic = self.dic
        # Check if I have an input that no one else uses.
        if not dic['forceOwnActs']:
            for i, inp in enumerate(dic['inputs']):
                l = layers[inp]
                if l['outputs'] == dic['outputs'] and sum('inputs' in ll and inp in ll['inputs'] for ll in layers) == 1:
                    # I can share my activity matrix with this layer
                    # if it does not use its activity matrix, and I 
                    # do not need to remember my inputs.
                    if not l['usesActs'] and not dic['usesInputs']:
                        dic['actsTarget'] = i
#                        print "Layer '%s' sharing activity matrix with layer '%s'" % (dic['name'], l['name'])
                    # I can share my gradient matrix with this layer.
                    dic['actsGradTarget'] = i
#                    print "Layer '%s' sharing activity gradient matrix with layer '%s'" % (dic['name'], l['name'])
            
    def parse(self, name, mcp, prev_layers, model=None):
        dic = LayerParser.parse(self, name, mcp, prev_layers, model)
        
        dic['inputs'] = [inp.strip() for inp in mcp.safe_get(name, 'inputs').split(',')]
        prev_names = [p['name'] for p in prev_layers]
        for inp in dic['inputs']:
            if inp not in prev_names:
                raise LayerParsingError("Layer '%s': input layer '%s' not defined" % (name, inp))
        dic['inputs'] = [prev_names.index(inp) for inp in dic['inputs']]
        dic['inputLayers'] = [prev_layers[inp] for inp in dic['inputs']]
        for inp in dic['inputs']:
            if prev_layers[inp]['outputs'] == 0:
                raise LayerParsingError("Layer '%s': input layer '%s' does not produce any output" % (name, prev_names[inp]))
        dic['numInputs'] = [prev_layers[i]['outputs'] for i in dic['inputs']]
        
        # Layers can declare a neuron activation function to apply to their output, as a shortcut
        # to avoid declaring a separate neuron layer above themselves.
        dic['neuron'] = mcp.safe_get(name, 'neuron', default="")
        if self.num_inputs > 0 and len(dic['numInputs']) != self.num_inputs:
            raise LayerParsingError("Layer '%s': number of inputs must be %d", name, self.num_inputs)
        
#        input_layers = [prev_layers[i] for i in dic['inputs']]
#        dic['gradConsumer'] = any(l['gradConsumer'] for l in dic['inputLayers'])
#        dic['usesActs'] = dic['gradConsumer'] # A conservative setting by default for layers with input
        return dic
    
    def verify_img_size(self):
        dic = self.dic
        if dic['numInputs'][0] % dic['imgPixels'] != 0 or dic['imgSize'] * dic['imgSize'] != dic['imgPixels']:
            raise LayerParsingError("Layer '%s': has %-d dimensional input, not interpretable as %d-channel images" % (dic['name'], dic['numInputs'][0], dic['channels']))
    
    @staticmethod
    def grad_consumers_below(dic):
        if dic['gradConsumer']:
            return True
        if 'inputLayers' in dic:
            return any(LayerWithInputParser.grad_consumers_below(l) for l in dic['inputLayers'])
        
    def verify_no_grads(self):
        if LayerWithInputParser.grad_consumers_below(self.dic):
            raise LayerParsingError("Layer '%s': layers of type '%s' cannot propagate gradient and must not be placed over layers with parameters." % (self.dic['name'], self.dic['type']))

class NailbedLayerParser(LayerWithInputParser):
    def __init__(self):
        LayerWithInputParser.__init__(self, num_inputs=1)
        
    def parse(self, name, mcp, prev_layers, model=None):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['forceOwnActs'] = False
        dic['usesActs'] = False
        dic['usesInputs'] = False
        
        dic['channels'] = mcp.safe_get_int(name, 'channels')
        dic['stride'] = mcp.safe_get_int(name, 'stride')

        self.verify_num_range(dic['channels'], 'channels', 1, None)
        
        # Computed values
        dic['imgPixels'] = dic['numInputs'][0] / dic['channels']
        dic['imgSize'] = int(n.sqrt(dic['imgPixels']))
        dic['outputsX'] = (dic['imgSize'] + dic['stride'] - 1) / dic['stride']
        dic['start'] = (dic['imgSize'] - dic['stride'] * (dic['outputsX'] - 1)) / 2
        dic['outputs'] = dic['channels'] * dic['outputsX']**2
        
        self.verify_num_range(dic['outputsX'], 'outputsX', 0, None)
        
        self.verify_img_size()
        
        print "Initialized bed-of-nails layer '%s', producing %dx%d %d-channel output" % (name, dic['outputsX'], dic['outputsX'], dic['channels'])
        return dic
    
class GaussianBlurLayerParser(LayerWithInputParser):
    def __init__(self):
        LayerWithInputParser.__init__(self, num_inputs=1)
        
    def parse(self, name, mcp, prev_layers, model=None):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['forceOwnActs'] = False
        dic['usesActs'] = False
        dic['usesInputs'] = False
        dic['outputs'] = dic['numInputs'][0]
        
        dic['channels'] = mcp.safe_get_int(name, 'channels')
        dic['filterSize'] = mcp.safe_get_int(name, 'filterSize')
        dic['stdev'] = mcp.safe_get_float(name, 'stdev')

        self.verify_num_range(dic['channels'], 'channels', 1, None)
        self.verify_int_in(dic['filterSize'], [3, 5, 7, 9])
        
        # Computed values
        dic['imgPixels'] = dic['numInputs'][0] / dic['channels']
        dic['imgSize'] = int(n.sqrt(dic['imgPixels']))
        dic['filter'] = n.array([exp(-(dic['filterSize']/2 - i)**2 / float(2 * dic['stdev']**2)) 
                                 for i in xrange(dic['filterSize'])], dtype=n.float32).reshape(1, dic['filterSize'])
        dic['filter'] /= dic['filter'].sum()

        self.verify_img_size()
        
        if dic['filterSize'] > dic['imgSize']:
            raise LayerParsingError("Later '%s': filter size (%d) must be smaller than image size (%d)." % (dic['name'], dic['filterSize'], dic['imgSize']))
        
        print "Initialized Gaussian blur layer '%s', producing %dx%d %d-channel output" % (name, dic['imgSize'], dic['imgSize'], dic['channels'])
        
        return dic
    
class ResizeLayerParser(LayerWithInputParser):
    def __init__(self):
        LayerWithInputParser.__init__(self, num_inputs=1)
        
    def parse(self, name, mcp, prev_layers, model=None):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['forceOwnActs'] = False
        dic['usesActs'] = False
        dic['usesInputs'] = False
        
        dic['channels'] = mcp.safe_get_int(name, 'channels')
        dic['imgPixels'] = dic['numInputs'][0] / dic['channels']
        dic['imgSize'] = int(n.sqrt(dic['imgPixels']))
        
        dic['scale'] = mcp.safe_get_float(name, 'scale')
        dic['tgtSize'] = int(floor(dic['imgSize'] / dic['scale']))
        dic['tgtPixels'] = dic['tgtSize']**2
        self.verify_num_range(dic['channels'], 'channels', 1, None)
        # Really not recommended to use this for such severe scalings
        self.verify_float_range(dic['scale'], 'scale', 0.5, 2) 

        dic['outputs'] = dic['channels'] * dic['tgtPixels']
        
        self.verify_img_size()
        self.verify_no_grads()
        
        print "Initialized resize layer '%s', producing %dx%d %d-channel output" % (name, dic['tgtSize'], dic['tgtSize'], dic['channels'])
        
        return dic
    
class RandomScaleLayerParser(LayerWithInputParser):
    def __init__(self):
        LayerWithInputParser.__init__(self, num_inputs=1)
        
    def parse(self, name, mcp, prev_layers, model=None):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['forceOwnActs'] = False
        dic['usesActs'] = False
        dic['usesInputs'] = False
        
        dic['channels'] = mcp.safe_get_int(name, 'channels')
        self.verify_num_range(dic['channels'], 'channels', 1, None)
        
        # Computed values
        dic['imgPixels'] = dic['numInputs'][0] / dic['channels']
        dic['imgSize'] = int(n.sqrt(dic['imgPixels']))
        
        dic['maxScale'] = mcp.safe_get_float(name, 'maxScale')
        dic['tgtSize'] = int(floor(dic['imgSize'] / dic['maxScale']))
        dic['tgtPixels'] = dic['tgtSize']**2
        
        self.verify_float_range(dic['maxScale'], 'maxScale', 1, 2) 

        dic['outputs'] = dic['channels'] * dic['tgtPixels']
        
        self.verify_img_size()
        self.verify_no_grads()
        
        print "Initialized random scale layer '%s', producing %dx%d %d-channel output" % (name, dic['tgtSize'], dic['tgtSize'], dic['channels'])
        
        return dic
    
class ColorTransformLayerParser(LayerWithInputParser):
    def __init__(self):
        LayerWithInputParser.__init__(self, num_inputs=1)
    
    def parse(self, name, mcp, prev_layers, model=None):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['forceOwnActs'] = False
        dic['usesActs'] = False
        dic['usesInputs'] = False

        # Computed values
        dic['imgPixels'] = dic['numInputs'][0] / 3
        dic['imgSize'] = int(n.sqrt(dic['imgPixels']))
        dic['channels'] = 3
        dic['outputs'] = dic['numInputs'][0]
        
        self.verify_img_size()
        self.verify_no_grads()
        
        return dic
    
class RGBToYUVLayerParser(ColorTransformLayerParser):
    def __init__(self):
        ColorTransformLayerParser.__init__(self)
        
    def parse(self, name, mcp, prev_layers, model=None):
        dic = ColorTransformLayerParser.parse(self, name, mcp, prev_layers, model)
        print "Initialized RGB --> YUV layer '%s', producing %dx%d %d-channel output" % (name, dic['imgSize'], dic['imgSize'], dic['channels'])
        return dic
    
class RGBToLABLayerParser(ColorTransformLayerParser):
    def __init__(self):
        ColorTransformLayerParser.__init__(self)
        
    def parse(self, name, mcp, prev_layers, model=None):
        dic = ColorTransformLayerParser.parse(self, name, mcp, prev_layers, model)
        dic['center'] = mcp.safe_get_bool(name, 'center', default=False)
        print "Initialized RGB --> LAB layer '%s', producing %dx%d %d-channel output" % (name, dic['imgSize'], dic['imgSize'], dic['channels'])
        return dic

class NeuronLayerParser(LayerWithInputParser):
    def __init__(self):
        LayerWithInputParser.__init__(self, num_inputs=1)
    
    @staticmethod
    def get_unused_layer_name(layers, wish):
        layer_names = set([l['name'] for l in layers])
        if wish not in layer_names:
            return wish
        for i in xrange(1, 100):
            name = '%s.%d' % (wish, i)
            if name not in layer_names:
                return name
        raise LayerParsingError("This is insane.")
    
    def parse_neuron(self, neuron_str):
        for n in neuron_parsers:
            p = n.parse(neuron_str)
            if p: # Successfully parsed neuron, return it
                self.dic['neuron'] = p
                self.dic['usesActs'] = self.dic['neuron']['usesActs']
                self.dic['usesInputs'] = self.dic['neuron']['usesInputs']
                
                return
        # Could not parse neuron
        # Print available neuron types
        colnames = ['Neuron type', 'Function']
        m = max(len(colnames[0]), OptionsParser._longest_value(neuron_parsers, key=lambda x:x.type)) + 2
        ntypes = [OptionsParser._bold(colnames[0].ljust(m))] + [n.type.ljust(m) for n in neuron_parsers]
        fnames = [OptionsParser._bold(colnames[1])] + [n.func_str for n in neuron_parsers]
        usage_lines = NL.join(ntype + fname for ntype,fname in zip(ntypes, fnames))
        
        raise LayerParsingError("Layer '%s': unable to parse neuron type '%s'. Valid neuron types: %sWhere neurons have parameters, they must be floats." % (self.dic['name'], neuron_str, NL + usage_lines + NL))
    
    def detach_neuron_layer(self, idx, layers, layers_new):
        dic = self.dic
        self.set_defaults()
        dic['name'] = NeuronLayerParser.get_unused_layer_name(layers, '%s_neuron' % layers[idx]['name'])
        dic['type'] = 'neuron'
        dic['inputs'] = layers[idx]['name']
        dic['neuron'] = layers[idx]['neuron']

        dic = self.parse(dic['name'], FakeConfigParser(dic), layers_new)
        
        # Link upper layers to this new one
        for l in layers[idx+1:]:
            if 'inputs' in l:
                l['inputs'] = [i + (i >= len(layers_new) - 1) for i in l['inputs']]
            if 'weightSourceLayerIndices' in l:
                l['weightSourceLayerIndices'] = [i + (i >= len(layers_new)) for i in l['weightSourceLayerIndices']]
        layers_new += [dic]
        
#        print "Initialized implicit neuron layer '%s', producing %d outputs" % (dic['name'], dic['outputs'])
    
    def parse(self, name, mcp, prev_layers, model=None):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['outputs'] = dic['numInputs'][0]
        self.parse_neuron(dic['neuron'])
        dic['forceOwnActs'] = False
        print "Initialized neuron layer '%s', producing %d outputs" % (name, dic['outputs'])
        return dic

class EltwiseSumLayerParser(LayerWithInputParser):
    def __init__(self):
        LayerWithInputParser.__init__(self)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        
        if len(set(dic['numInputs'])) != 1:
            raise LayerParsingError("Layer '%s': all inputs must have the same dimensionality. Got dimensionalities: %s" % (name, ", ".join(str(s) for s in dic['numInputs'])))
        dic['outputs'] = dic['numInputs'][0]
        dic['usesInputs'] = False
        dic['usesActs'] = False
        dic['forceOwnActs'] = False
        
        dic['coeffs'] = mcp.safe_get_float_list(name, 'coeffs', default=[1.0] * len(dic['inputs']))
        
        print "Initialized elementwise sum layer '%s', producing %d outputs" % (name, dic['outputs'])
        return dic
    
class EltwiseMaxLayerParser(LayerWithInputParser):
    def __init__(self):
        LayerWithInputParser.__init__(self)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        if len(dic['inputs']) < 2:
            raise LayerParsingError("Layer '%s': elementwise max layer must have at least 2 inputs, got %d." % (name, len(dic['inputs'])))
        if len(set(dic['numInputs'])) != 1:
            raise LayerParsingError("Layer '%s': all inputs must have the same dimensionality. Got dimensionalities: %s" % (name, ", ".join(str(s) for s in dic['numInputs'])))
        dic['outputs'] = dic['numInputs'][0]

        print "Initialized elementwise max layer '%s', producing %d outputs" % (name, dic['outputs'])
        return dic

class WeightLayerParser(LayerWithInputParser):
    LAYER_PAT = re.compile(r'^\s*([^\s\[]+)(?:\[(\d+)\])?\s*$') # matches things like layername[5], etc
    
    def __init__(self):
        LayerWithInputParser.__init__(self)
    
    @staticmethod
    def get_layer_name(name_str):
        m = WeightLayerParser.LAYER_PAT.match(name_str)
        if not m:
            return None
        return m.group(1), m.group(2)
    
    def add_params(self, mcp):
        LayerWithInputParser.add_params(self, mcp)

        dic, name = self.dic, self.dic['name']
        dic['epsW'] = mcp.safe_get_float_list(name, 'epsW')
        dic['epsB'] = mcp.safe_get_float(name, 'epsB')
        dic['momW'] = mcp.safe_get_float_list(name, 'momW')
        dic['momB'] = mcp.safe_get_float(name, 'momB')
        dic['wc'] = mcp.safe_get_float_list(name, 'wc')
        
        self.verify_num_params(['epsW', 'momW', 'wc'])
        
        dic['gradConsumer'] = dic['epsB'] > 0 or any(w > 0 for w in dic['epsW'])
        
    @staticmethod
    def unshare_weights(layer, layers, matrix_idx=None):
        def unshare(layer, layers, indices):
            for i in indices:
                if layer['weightSourceLayerIndices'][i] >= 0:
                    src_name = layers[layer['weightSourceLayerIndices'][i]]['name']
                    src_matrix_idx = layer['weightSourceMatrixIndices'][i]
                    layer['weightSourceLayerIndices'][i] = -1
                    layer['weightSourceMatrixIndices'][i] = -1
                    layer['weights'][i] = layer['weights'][i].copy()
                    layer['weightsInc'][i] = n.zeros_like(layer['weights'][i])
                    print "Unshared weight matrix %s[%d] from %s[%d]." % (layer['name'], i, src_name, src_matrix_idx)
                else:
                    print "Weight matrix %s[%d] already unshared." % (layer['name'], i)
        if 'weightSourceLayerIndices' in layer:
            unshare(layer, layers, range(len(layer['inputs'])) if matrix_idx is None else [matrix_idx])

    # Load weight/biases initialization module
    def call_init_func(self, param_name, shapes, input_idx=-1):
        dic = self.dic
        func_pat = re.compile('^([^\.]+)\.([^\(\)]+)\s*(?:\(([^,]+(?:,[^,]+)*)\))?$')
        m = func_pat.match(dic[param_name])
        if not m:
            raise LayerParsingError("Layer '%s': '%s' parameter must have format 'moduleName.functionName(param1,param2,...)'; got: %s." % (dic['name'], param_name, dic['initWFunc']))
        module, func = m.group(1), m.group(2)
        params = m.group(3).split(',') if m.group(3) is not None else []
        try:
            mod = __import__(module)
            return getattr(mod, func)(dic['name'], input_idx, shapes, params=params) if input_idx >= 0 else getattr(mod, func)(dic['name'], shapes, params=params)
        except (ImportError, AttributeError, TypeError), e:
            raise LayerParsingError("Layer '%s': %s." % (dic['name'], e))
        
    def make_weights(self, initW, rows, cols, order='C'):
        dic = self.dic
        dic['weights'], dic['weightsInc'] = [], []
        if dic['initWFunc']: # Initialize weights from user-supplied python function
            # Initialization function is supplied in the format
            # module.func
            for i in xrange(len(dic['inputs'])):
                dic['weights'] += [self.call_init_func('initWFunc', (rows[i], cols[i]), input_idx=i)]

                if type(dic['weights'][i]) != n.ndarray:
                    raise LayerParsingError("Layer '%s[%d]': weight initialization function %s must return numpy.ndarray object. Got: %s." % (dic['name'], i, dic['initWFunc'], type(dic['weights'][i])))
                if dic['weights'][i].dtype != n.float32:
                    raise LayerParsingError("Layer '%s[%d]': weight initialization function %s must weight matrices consisting of single-precision floats. Got: %s." % (dic['name'], i, dic['initWFunc'], dic['weights'][i].dtype))
                if dic['weights'][i].shape != (rows[i], cols[i]):
                    raise LayerParsingError("Layer '%s[%d]': weight matrix returned by weight initialization function %s has wrong shape. Should be: %s; got: %s." % (dic['name'], i, dic['initWFunc'], (rows[i], cols[i]), dic['weights'][i].shape))
                # Convert to desired order
                dic['weights'][i] = n.require(dic['weights'][i], requirements=order)
                dic['weightsInc'] += [n.zeros_like(dic['weights'][i])]
                print "Layer '%s[%d]' initialized weight matrices from function %s" % (dic['name'], i, dic['initWFunc'])
        else:
            for i in xrange(len(dic['inputs'])):
                if dic['weightSourceLayerIndices'][i] >= 0: # Shared weight matrix
                    src_layer = self.prev_layers[dic['weightSourceLayerIndices'][i]] if dic['weightSourceLayerIndices'][i] < len(self.prev_layers) else dic
                    dic['weights'] += [src_layer['weights'][dic['weightSourceMatrixIndices'][i]]]
                    dic['weightsInc'] += [src_layer['weightsInc'][dic['weightSourceMatrixIndices'][i]]]
                    if dic['weights'][i].shape != (rows[i], cols[i]):
                        raise LayerParsingError("Layer '%s': weight sharing source matrix '%s' has shape %dx%d; should be %dx%d." 
                                                % (dic['name'], dic['weightSource'][i], dic['weights'][i].shape[0], dic['weights'][i].shape[1], rows[i], cols[i]))
                    print "Layer '%s' initialized weight matrix %d from %s" % (dic['name'], i, dic['weightSource'][i])
                else:
                    dic['weights'] += [n.array(initW[i] * nr.randn(rows[i], cols[i]), dtype=n.single, order=order)]
                    dic['weightsInc'] += [n.zeros_like(dic['weights'][i])]
        
    def make_biases(self, rows, cols, order='C'):
        dic = self.dic
        if dic['initBFunc']:
            dic['biases'] = self.call_init_func('initBFunc', (rows, cols))
            if type(dic['biases']) != n.ndarray:
                raise LayerParsingError("Layer '%s': bias initialization function %s must return numpy.ndarray object. Got: %s." % (dic['name'], dic['initBFunc'], type(dic['biases'])))
            if dic['biases'].dtype != n.float32:
                raise LayerParsingError("Layer '%s': bias initialization function %s must return numpy.ndarray object consisting of single-precision floats. Got: %s." % (dic['name'], dic['initBFunc'], dic['biases'].dtype))
            if dic['biases'].shape != (rows, cols):
                raise LayerParsingError("Layer '%s': bias vector returned by bias initialization function %s has wrong shape. Should be: %s; got: %s." % (dic['name'], dic['initBFunc'], (rows, cols), dic['biases'].shape))

            dic['biases'] = n.require(dic['biases'], requirements=order)
            print "Layer '%s' initialized bias vector from function %s" % (dic['name'], dic['initBFunc'])
        else:
            dic['biases'] = dic['initB'] * n.ones((rows, cols), order='C', dtype=n.single)
        dic['biasesInc'] = n.zeros_like(dic['biases'])
        
    def parse(self, name, mcp, prev_layers, model):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['requiresParams'] = True
        dic['gradConsumer'] = True
        dic['initW'] = mcp.safe_get_float_list(name, 'initW', default=0.01)
        dic['initB'] = mcp.safe_get_float(name, 'initB', default=0)
        dic['initWFunc'] = mcp.safe_get(name, 'initWFunc', default="")
        dic['initBFunc'] = mcp.safe_get(name, 'initBFunc', default="")
        # Find shared weight matrices
        
        dic['weightSource'] = mcp.safe_get_list(name, 'weightSource', default=[''] * len(dic['inputs']))
        self.verify_num_params(['initW', 'weightSource'])
        
        prev_names = map(lambda x: x['name'], prev_layers)
        dic['weightSourceLayerIndices'] = []
        dic['weightSourceMatrixIndices'] = []
        for i, src_name in enumerate(dic['weightSource']):
            src_layer_idx = src_layer_matrix_idx = -1
            if src_name != '':
                src_layer_match = WeightLayerParser.get_layer_name(src_name)
                if src_layer_match is None:
                    raise LayerParsingError("Layer '%s': unable to parse weight sharing source '%s'. Format is layer[idx] or just layer, in which case idx=0 is used." % (name, src_name))
                src_layer_name = src_layer_match[0]
                src_layer_matrix_idx = int(src_layer_match[1]) if src_layer_match[1] is not None else 0

                if prev_names.count(src_layer_name) == 0 and src_layer_name != name:
                    raise LayerParsingError("Layer '%s': weight sharing source layer '%s' does not exist." % (name, src_layer_name))
                
                src_layer_idx = prev_names.index(src_layer_name) if src_layer_name != name else len(prev_names)
                src_layer = prev_layers[src_layer_idx] if src_layer_name != name else dic
                if src_layer['type'] != dic['type']:
                    raise LayerParsingError("Layer '%s': weight sharing source layer '%s' is of type '%s'; should be '%s'." % (name, src_layer_name, src_layer['type'], dic['type']))
                if src_layer_name != name and len(src_layer['weights']) <= src_layer_matrix_idx:
                    raise LayerParsingError("Layer '%s': weight sharing source layer '%s' has %d weight matrices, but '%s[%d]' requested." % (name, src_layer_name, len(src_layer['weights']), src_name, src_layer_matrix_idx))
                if src_layer_name == name and src_layer_matrix_idx >= i:
                    raise LayerParsingError("Layer '%s': weight sharing source '%s[%d]' not defined yet." % (name, name, src_layer_matrix_idx))

            dic['weightSourceLayerIndices'] += [src_layer_idx]
            dic['weightSourceMatrixIndices'] += [src_layer_matrix_idx]
                
        return dic
        
class FCLayerParser(WeightLayerParser):
    def __init__(self):
        WeightLayerParser.__init__(self)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = WeightLayerParser.parse(self, name, mcp, prev_layers, model)
        
        dic['usesActs'] = False
        dic['outputs'] = mcp.safe_get_int(name, 'outputs')
        
        self.verify_num_range(dic['outputs'], 'outputs', 1, None)
        self.make_weights(dic['initW'], dic['numInputs'], [dic['outputs']] * len(dic['numInputs']), order='F')
        self.make_biases(1, dic['outputs'], order='F')
        print "Initialized fully-connected layer '%s', producing %d outputs" % (name, dic['outputs'])
        return dic

class LocalLayerParser(WeightLayerParser):
    def __init__(self):
        WeightLayerParser.__init__(self)
        
    # Convert convolutional layer to unshared, locally-connected layer
    @staticmethod
    def conv_to_local(layers, idx):
        layer = layers[idx]
        if layer['type'] == 'conv':
            layer['type'] = 'local'
            for inp in xrange(len(layer['inputs'])):
                src_layer_idx = layer['weightSourceLayerIndices'][inp]
                if layer['weightSourceLayerIndices'][inp] >= 0:
                    src_layer = layers[src_layer_idx]
                    src_matrix_idx = layer['weightSourceMatrixIndices'][inp]
                    LocalLayerParser.conv_to_local(layers, src_layer_idx)
                    for w in ('weights', 'weightsInc'):
                        layer[w][inp] = src_layer[w][src_matrix_idx]
                else:
                    layer['weights'][inp] = n.require(n.reshape(n.tile(n.reshape(layer['weights'][inp], (1, n.prod(layer['weights'][inp].shape))), (layer['modules'], 1)),
                                                        (layer['modules'] * layer['filterChannels'][inp] * layer['filterPixels'][inp], layer['filters'])),
                                                      requirements='C')
                    layer['weightsInc'][inp] = n.zeros_like(layer['weights'][inp])
            if layer['sharedBiases']:
                layer['biases'] = n.require(n.repeat(layer['biases'], layer['modules'], axis=0), requirements='C')
                layer['biasesInc'] = n.zeros_like(layer['biases'])
            
            print "Converted layer '%s' from convolutional to unshared, locally-connected" % layer['name']
            
            # Also call this function on any layers sharing my weights
            for i, l in enumerate(layers):
                if 'weightSourceLayerIndices' in l and idx in l['weightSourceLayerIndices']:
                    LocalLayerParser.conv_to_local(layers, i)
        return layer
        
    # Returns (groups, filterChannels) array that represents the set
    # of image channels to which each group is connected
    def gen_rand_conns(self, groups, channels, filterChannels, inputIdx):
        dic = self.dic
        overSample = groups * filterChannels / channels
        filterConns = [x for i in xrange(overSample) for x in nr.permutation(range(channels))]
        
        if dic['initCFunc']: # Initialize connectivity from outside source
            filterConns = self.call_init_func('initCFunc', (groups, channels, filterChannels), input_idx=inputIdx)
            if len(filterConns) != overSample * channels:
                raise LayerParsingError("Layer '%s[%d]': random connectivity initialization function %s must return list of length <groups> * <filterChannels> = %d; got: %d" % (dic['name'], inputIdx, dic['initCFunc'], len(filterConns)))
            if any(c not in range(channels) for c in filterConns):
                raise LayerParsingError("Layer '%s[%d]': random connectivity initialization function %s must return list of channel indices in the range 0-<channels-1> = 0-%d." % (dic['name'], inputIdx, dic['initCFunc'], channels-1))
            # Every "channels" sub-slice should be a permutation of range(channels)
            if any(len(set(c)) != len(c) for c in [filterConns[o*channels:(o+1)*channels] for o in xrange(overSample)]):
                raise LayerParsingError("Layer '%s[%d]': random connectivity initialization function %s must return list of channel indices such that every non-overlapping sub-list of <channels> = %d elements is a permutation of the integers 0-<channels-1> = 0-%d." % (dic['name'], inputIdx, dic['initCFunc'], channels, channels-1))

        elif dic['weightSourceLayerIndices'][inputIdx] >= 0: # Shared weight matrix
            src_layer = self.prev_layers[dic['weightSourceLayerIndices'][inputIdx]] if dic['weightSourceLayerIndices'][inputIdx] < len(self.prev_layers) else dic
            src_inp = dic['weightSourceMatrixIndices'][inputIdx]
            if 'randSparse' not in src_layer or not src_layer['randSparse']:
                raise LayerParsingError("Layer '%s[%d]': randSparse is true in this layer but false in weight sharing source layer '%s[%d]'." % (dic['name'], inputIdx, src_layer['name'], src_inp))
            if (groups, channels, filterChannels) != (src_layer['groups'][src_inp], src_layer['channels'][src_inp], src_layer['filterChannels'][src_inp]):
                raise LayerParsingError("Layer '%s[%d]': groups, channels, filterChannels set to %d, %d, %d, respectively. Does not match setting in weight sharing source layer '%s[%d]': %d, %d, %d." % (dic['name'], inputIdx, groups, channels, filterChannels, src_layer['name'], src_inp, src_layer['groups'][src_inp], src_layer['channels'][src_inp], src_layer['filterChannels'][src_inp]))
            filterConns = src_layer['filterConns'][src_inp]
        return filterConns
        
    def parse(self, name, mcp, prev_layers, model):
        dic = WeightLayerParser.parse(self, name, mcp, prev_layers, model)
        dic['requiresParams'] = True
        dic['usesActs'] = False
        # Supplied values
        dic['channels'] = mcp.safe_get_int_list(name, 'channels')
        dic['padding'] = mcp.safe_get_int_list(name, 'padding', default=[0]*len(dic['inputs']))
        dic['stride'] = mcp.safe_get_int_list(name, 'stride', default=[1]*len(dic['inputs']))
        dic['filterSize'] = mcp.safe_get_int_list(name, 'filterSize')
        dic['filters'] = mcp.safe_get_int_list(name, 'filters')
        dic['groups'] = mcp.safe_get_int_list(name, 'groups', default=[1]*len(dic['inputs']))
        dic['randSparse'] = mcp.safe_get_bool_list(name, 'randSparse', default=[False]*len(dic['inputs']))
        dic['initW'] = mcp.safe_get_float_list(name, 'initW')
        dic['initCFunc'] = mcp.safe_get(name, 'initCFunc', default='')
        
        self.verify_num_params(['channels', 'padding', 'stride', 'filterSize', \
                                                     'filters', 'groups', 'randSparse', 'initW'])
        
        self.verify_num_range(dic['stride'], 'stride', 1, None)
        self.verify_num_range(dic['filterSize'],'filterSize', 1, None)  
        self.verify_num_range(dic['padding'], 'padding', 0, None)
        self.verify_num_range(dic['channels'], 'channels', 1, None)
        self.verify_num_range(dic['groups'], 'groups', 1, None)
        
        # Computed values
        dic['imgPixels'] = [numInputs/channels for numInputs,channels in zip(dic['numInputs'], dic['channels'])]
        dic['imgSize'] = [int(n.sqrt(imgPixels)) for imgPixels in dic['imgPixels']]
        self.verify_num_range(dic['imgSize'], 'imgSize', 1, None)
        dic['filters'] = [filters*groups for filters,groups in zip(dic['filters'], dic['groups'])]
        dic['filterPixels'] = [filterSize**2 for filterSize in dic['filterSize']]
        dic['modulesX'] = [1 + int(ceil((2 * padding + imgSize - filterSize) / float(stride))) for padding,imgSize,filterSize,stride in zip(dic['padding'], dic['imgSize'], dic['filterSize'], dic['stride'])]

        dic['filterChannels'] = [channels/groups for channels,groups in zip(dic['channels'], dic['groups'])]
        if max(dic['randSparse']): # When randSparse is turned on for any input, filterChannels must be given for all of them
            dic['filterChannels'] = mcp.safe_get_int_list(name, 'filterChannels', default=dic['filterChannels'])
            self.verify_num_params(['filterChannels'])
        
        if len(set(dic['modulesX'])) != 1 or len(set(dic['filters'])) != 1:
            raise LayerParsingError("Layer '%s': all inputs must produce equally-dimensioned output. Dimensions are: %s." % (name, ", ".join("%dx%dx%d" % (filters, modulesX, modulesX) for filters,modulesX in zip(dic['filters'], dic['modulesX']))))

        dic['modulesX'] = dic['modulesX'][0]
        dic['modules'] = dic['modulesX']**2
        dic['filters'] = dic['filters'][0]
        dic['outputs'] = dic['modules'] * dic['filters']
        dic['filterConns'] = [[]] * len(dic['inputs'])
        for i in xrange(len(dic['inputs'])):
            if dic['numInputs'][i] % dic['imgPixels'][i] != 0 or dic['imgSize'][i] * dic['imgSize'][i] != dic['imgPixels'][i]:
                raise LayerParsingError("Layer '%s[%d]': has %-d dimensional input, not interpretable as square %d-channel images" % (name, i, dic['numInputs'][i], dic['channels'][i]))
            if dic['channels'][i] > 3 and dic['channels'][i] % 4 != 0:
                raise LayerParsingError("Layer '%s[%d]': number of channels must be smaller than 4 or divisible by 4" % (name, i))
            if dic['filterSize'][i] > 2 * dic['padding'][i] + dic['imgSize'][i]:
                raise LayerParsingError("Layer '%s[%d]': filter size (%d) greater than image size + 2 * padding (%d)" % (name, i, dic['filterSize'][i], 2 * dic['padding'][i] + dic['imgSize'][i]))
        
            if dic['randSparse'][i]: # Random sparse connectivity requires some extra checks
                if dic['groups'][i] == 1:
                    raise LayerParsingError("Layer '%s[%d]': number of groups must be greater than 1 when using random sparse connectivity" % (name, i))
                self.verify_divisible(dic['channels'][i], dic['filterChannels'][i], 'channels', 'filterChannels', input_idx=i)
                self.verify_divisible(dic['filterChannels'][i], 4, 'filterChannels', input_idx=i)
                self.verify_divisible( dic['groups'][i]*dic['filterChannels'][i], dic['channels'][i], 'groups * filterChannels', 'channels', input_idx=i)
                dic['filterConns'][i] = self.gen_rand_conns(dic['groups'][i], dic['channels'][i], dic['filterChannels'][i], i)
            else:
                if dic['groups'][i] > 1:
                    self.verify_divisible(dic['channels'][i], 4*dic['groups'][i], 'channels', '4 * groups', input_idx=i)
                self.verify_divisible(dic['channels'][i], dic['groups'][i], 'channels', 'groups', input_idx=i)

            self.verify_divisible(dic['filters'], 16*dic['groups'][i], 'filters * groups', input_idx=i)
        
            dic['padding'][i] = -dic['padding'][i]
        dic['overSample'] = [groups*filterChannels/channels for groups,filterChannels,channels in zip(dic['groups'], dic['filterChannels'], dic['channels'])]

        return dic    

class ConvLayerParser(LocalLayerParser):
    def __init__(self):
        LocalLayerParser.__init__(self)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = LocalLayerParser.parse(self, name, mcp, prev_layers, model)
        
        dic['partialSum'] = mcp.safe_get_int(name, 'partialSum')
        dic['sharedBiases'] = mcp.safe_get_bool(name, 'sharedBiases', default=True)

        if dic['partialSum'] != 0 and dic['modules'] % dic['partialSum'] != 0:
            raise LayerParsingError("Layer '%s': convolutional layer produces %dx%d=%d outputs per filter, but given partialSum parameter (%d) does not divide this number" % (name, dic['modulesX'], dic['modulesX'], dic['modules'], dic['partialSum']))

        num_biases = dic['filters'] if dic['sharedBiases'] else dic['modules']*dic['filters']

        eltmult = lambda list1, list2: [l1 * l2 for l1,l2 in zip(list1, list2)]
        self.make_weights(dic['initW'], eltmult(dic['filterPixels'], dic['filterChannels']), [dic['filters']] * len(dic['inputs']), order='C')
        self.make_biases(num_biases, 1, order='C')

        print "Initialized convolutional layer '%s', producing %dx%d %d-channel output" % (name, dic['modulesX'], dic['modulesX'], dic['filters'])
        return dic    
    
class LocalUnsharedLayerParser(LocalLayerParser):
    def __init__(self):
        LocalLayerParser.__init__(self)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = LocalLayerParser.parse(self, name, mcp, prev_layers, model)

        eltmult = lambda list1, list2: [l1 * l2 for l1,l2 in zip(list1, list2)]
        scmult = lambda x, lst: [x * l for l in lst]
        self.make_weights(dic['initW'], scmult(dic['modules'], eltmult(dic['filterPixels'], dic['filterChannels'])), [dic['filters']] * len(dic['inputs']), order='C')
        self.make_biases(dic['modules'] * dic['filters'], 1, order='C')
        
        print "Initialized locally-connected layer '%s', producing %dx%d %d-channel output" % (name, dic['modulesX'], dic['modulesX'], dic['filters'])
        return dic  
    
class DataLayerParser(LayerParser):
    def __init__(self):
        LayerParser.__init__(self)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = LayerParser.parse(self, name, mcp, prev_layers, model)
        dic['dataIdx'] = mcp.safe_get_int(name, 'dataIdx')
        dic['outputs'] = model.train_data_provider.get_data_dims(idx=dic['dataIdx'])
        
        print "Initialized data layer '%s', producing %d outputs" % (name, dic['outputs'])
        return dic

class SoftmaxLayerParser(LayerWithInputParser):
    def __init__(self):
        LayerWithInputParser.__init__(self, num_inputs=1)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['outputs'] = prev_layers[dic['inputs'][0]]['outputs']
        print "Initialized softmax layer '%s', producing %d outputs" % (name, dic['outputs'])
        return dic

class PoolLayerParser(LayerWithInputParser):
    def __init__(self):
        LayerWithInputParser.__init__(self, num_inputs=1)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['channels'] = mcp.safe_get_int(name, 'channels')
        dic['sizeX'] = mcp.safe_get_int(name, 'sizeX')
        dic['start'] = mcp.safe_get_int(name, 'start', default=0)
        dic['stride'] = mcp.safe_get_int(name, 'stride')
        dic['outputsX'] = mcp.safe_get_int(name, 'outputsX', default=0)
        dic['pool'] = mcp.safe_get(name, 'pool')
        
        # Avg pooler does not use its acts or inputs
        dic['usesActs'] = 'pool' != 'avg'
        dic['usesInputs'] = 'pool' != 'avg'
        
        dic['imgPixels'] = dic['numInputs'][0] / dic['channels']
        dic['imgSize'] = int(n.sqrt(dic['imgPixels']))
        
        self.verify_num_range(dic['sizeX'], 'sizeX', 1, dic['imgSize'])
        self.verify_num_range(dic['stride'], 'stride', 1, dic['sizeX'])
        self.verify_num_range(dic['outputsX'], 'outputsX', 0, None)
        self.verify_num_range(dic['channels'], 'channels', 1, None)
        
        if LayerWithInputParser.grad_consumers_below(dic):
            self.verify_divisible(dic['channels'], 16, 'channels')
        self.verify_str_in(dic['pool'], ['max', 'avg'])
        
        self.verify_img_size()

        if dic['outputsX'] <= 0:
            dic['outputsX'] = int(ceil((dic['imgSize'] - dic['start'] - dic['sizeX']) / float(dic['stride']))) + 1;
        dic['outputs'] = dic['outputsX']**2 * dic['channels']
        
        print "Initialized %s-pooling layer '%s', producing %dx%d %d-channel output" % (dic['pool'], name, dic['outputsX'], dic['outputsX'], dic['channels'])
        return dic
    
class NormLayerParser(LayerWithInputParser):
    RESPONSE_NORM = 'response'
    CONTRAST_NORM = 'contrast'
    CROSSMAP_RESPONSE_NORM = 'cross-map response'
    
    def __init__(self, norm_type):
        LayerWithInputParser.__init__(self, num_inputs=1)
        self.norm_type = norm_type
        
    def add_params(self, mcp):
        LayerWithInputParser.add_params(self, mcp)

        dic, name = self.dic, self.dic['name']
        dic['scale'] = mcp.safe_get_float(name, 'scale')
        dic['scale'] /= dic['size'] if self.norm_type == self.CROSSMAP_RESPONSE_NORM else dic['size']**2
        dic['pow'] = mcp.safe_get_float(name, 'pow')
        
    def parse(self, name, mcp, prev_layers, model):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['requiresParams'] = True
        dic['channels'] = mcp.safe_get_int(name, 'channels')
        dic['size'] = mcp.safe_get_int(name, 'size')
        dic['blocked'] = mcp.safe_get_bool(name, 'blocked', default=False)
        
        dic['imgPixels'] = dic['numInputs'][0] / dic['channels']
        dic['imgSize'] = int(n.sqrt(dic['imgPixels']))
        
        # Contrast normalization layer does not use its inputs
        dic['usesInputs'] = self.norm_type != self.CONTRAST_NORM
        
        self.verify_num_range(dic['channels'], 'channels', 1, None)
        if self.norm_type == self.CROSSMAP_RESPONSE_NORM: 
            self.verify_num_range(dic['size'], 'size', 2, dic['channels'])
            if dic['channels'] % 16 != 0:
                raise LayerParsingError("Layer '%s': number of channels must be divisible by 16 when using crossMap" % name)
        else:
            self.verify_num_range(dic['size'], 'size', 1, dic['imgSize'])
        
        if self.norm_type != self.CROSSMAP_RESPONSE_NORM and dic['channels'] > 3 and dic['channels'] % 4 != 0:
            raise LayerParsingError("Layer '%s': number of channels must be smaller than 4 or divisible by 4" % name)

        self.verify_img_size()

        dic['outputs'] = dic['imgPixels'] * dic['channels']
        print "Initialized %s-normalization layer '%s', producing %dx%d %d-channel output" % (self.norm_type, name, dic['imgSize'], dic['imgSize'], dic['channels'])
        return dic

class CostParser(LayerWithInputParser):
    def __init__(self, num_inputs=-1):
        LayerWithInputParser.__init__(self, num_inputs=num_inputs)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = LayerWithInputParser.parse(self, name, mcp, prev_layers, model)
        dic['requiresParams'] = True
        del dic['neuron']
        return dic

    def add_params(self, mcp):
        LayerWithInputParser.add_params(self, mcp)

        dic, name = self.dic, self.dic['name']
        dic['coeff'] = mcp.safe_get_float(name, 'coeff')
            
class LogregCostParser(CostParser):
    def __init__(self):
        CostParser.__init__(self, num_inputs=2)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = CostParser.parse(self, name, mcp, prev_layers, model)
        if dic['numInputs'][0] != 1: # first input must be labels
            raise LayerParsingError("Layer '%s': dimensionality of first input must be 1" % name)
        if prev_layers[dic['inputs'][1]]['type'] != 'softmax':
            raise LayerParsingError("Layer '%s': second input must be softmax layer" % name)
        if dic['numInputs'][1] != model.train_data_provider.get_num_classes():
            raise LayerParsingError("Layer '%s': softmax input '%s' must produce %d outputs, because that is the number of classes in the dataset" \
                                    % (name, prev_layers[dic['inputs'][1]]['name'], model.train_data_provider.get_num_classes()))
        
        print "Initialized logistic regression cost '%s'" % name
        return dic
    
class SumOfSquaresCostParser(CostParser):
    def __init__(self):
        CostParser.__init__(self, num_inputs=1)
        
    def parse(self, name, mcp, prev_layers, model):
        dic = CostParser.parse(self, name, mcp, prev_layers, model)
        print "Initialized sum-of-squares cost '%s'" % name
        return dic

# All the layer parsers
layer_parsers = {'data': lambda : DataLayerParser(),
                 'fc': lambda : FCLayerParser(),
                 'conv': lambda : ConvLayerParser(),
                 'local': lambda : LocalUnsharedLayerParser(),
                 'softmax': lambda : SoftmaxLayerParser(),
                 'eltsum': lambda : EltwiseSumLayerParser(),
                 'eltmax': lambda : EltwiseMaxLayerParser(),
                 'neuron': lambda : NeuronLayerParser(),
                 'pool': lambda : PoolLayerParser(),
                 'rnorm': lambda : NormLayerParser(NormLayerParser.RESPONSE_NORM),
                 'cnorm': lambda : NormLayerParser(NormLayerParser.CONTRAST_NORM),
                 'cmrnorm': lambda : NormLayerParser(NormLayerParser.CROSSMAP_RESPONSE_NORM),
                 'nailbed': lambda : NailbedLayerParser(),
                 'blur': lambda : GaussianBlurLayerParser(),
                 'resize': lambda : ResizeLayerParser(),
                 'rgb2yuv': lambda : RGBToYUVLayerParser(),
                 'rgb2lab': lambda : RGBToLABLayerParser(),
                 'rscale': lambda : RandomScaleLayerParser(),
                 'cost.logreg': lambda : LogregCostParser(),
                 'cost.sum2': lambda : SumOfSquaresCostParser()}
 
# All the neuron parsers
# This isn't a name --> parser mapping as the layer parsers above because neurons don't have fixed names.
# A user may write tanh[0.5,0.25], etc.
neuron_parsers = sorted([NeuronParser('ident', 'f(x) = x', uses_acts=False, uses_inputs=False),
                         NeuronParser('logistic', 'f(x) = 1 / (1 + e^-x)', uses_acts=True, uses_inputs=False),
                         NeuronParser('abs', 'f(x) = |x|', uses_acts=False, uses_inputs=True),
                         NeuronParser('relu', 'f(x) = max(0, x)', uses_acts=True, uses_inputs=False),
                         NeuronParser('softrelu', 'f(x) = log(1 + e^x)', uses_acts=True, uses_inputs=False),
                         NeuronParser('square', 'f(x) = x^2', uses_acts=False, uses_inputs=True),
                         NeuronParser('sqrt', 'f(x) = sqrt(x)', uses_acts=True, uses_inputs=False),
                         ParamNeuronParser('tanh[a,b]', 'f(x) = a * tanh(b * x)', uses_acts=True, uses_inputs=False),
                         ParamNeuronParser('brelu[a]', 'f(x) = min(a, max(0, x))', uses_acts=True, uses_inputs=False),
                         ParamNeuronParser('linear[a,b]', 'f(x) = a * x + b', uses_acts=True, uses_inputs=False)],
                        key=lambda x:x.type)

########NEW FILE########
__FILENAME__ = options
# Copyright (c) 2011, Alex Krizhevsky (akrizhevsky@gmail.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
from getopt import getopt
import os
import re
#import types

TERM_BOLD_START = "\033[1m"
TERM_BOLD_END = "\033[0m"

class Option:
    def __init__(self, letter, name, desc, parser, set_once, default, excuses, requires, save):
        assert not name is None
        self.letter = letter
        self.name = name
        self.desc = desc
        self.parser = parser
        self.set_once = set_once
        self.default = default
        self.excuses = excuses
        self.requires = requires
        self.save = save

        self.value = None
        self.value_given = False
        self.prefixed_letter = min(2, len(letter)) * '-' + letter

    def set_value(self, value, parse=True):
        try:
            self.value = self.parser.parse(value) if parse else value
            self.value_given = True
        except OptionException, e:
            raise OptionException("Unable to parse option %s (%s): %s" % (self.prefixed_letter, self.desc, e))

    def set_default(self):
        if not self.default is None:
            self.value = self.default

    def eval_expr_default(self, env):
        try:
            if isinstance(self.default, OptionExpression) and not self.value_given:
                self.value = self.default.evaluate(env)
                if not self.parser.is_type(self.value):
                    raise OptionException("expression result %s is not of right type (%s)" % (self.value, self.parser.get_type_str()))
        except Exception, e:
            raise OptionException("Unable to set default value for option %s (%s): %s" % (self.prefixed_letter, self.desc, e))

    def get_str_value(self, get_default_str=False):
        val = self.value
        if get_default_str: val = self.default
        if val is None: return ""
        if isinstance(val, OptionExpression):
            return val.expr
        return self.parser.to_string(val)

class OptionsParser:
    """An option parsing class. All options without default values are mandatory, unless a excuses
    option (usually a load file) is given.
    Does not support options without arguments."""
    SORT_LETTER = 1
    SORT_DESC = 2
    SORT_EXPR_LAST = 3
    EXCLUDE_ALL = "all"
    def __init__(self):
        self.options = {}

    def add_option(self, letter, name, parser, desc, set_once=False, default=None, excuses=[], requires=[], save=True):
        """
        The letter parameter is the actual parameter that the user will have to supply on the command line.
        The name parameter is some name to be given to this option and must be a valid python variable name.

        An explanation of the "default" parameter:
        The default value, if specified, should have the same type as the option.
        You can also specify an expression as the default value. In this case, the default value of the parameter
        will be the output of the expression. The expression may assume all other option names
        as local variables. For example, you can define the hidden bias
        learning rate to be 10 times the weight learning rate by setting this default:

        default=OptionExpression("eps_w * 10") (assuming an option named eps_w exists).

        However, it is up to you to make sure you do not make any circular expression definitions.

        Note that the order in which the options are parsed is arbitrary.
        In particular, expression default values that depend on other expression default values
        will often raise errors (depending on the order in which they happen to be parsed).
        Therefore it is best not to make the default value of one variable depend on the value
        of another if the other variable's default value is itself an expression.

        An explanation of the excuses parameter:
        All options are mandatory, but certain options can exclude other options from being mandatory.
        For example, if the excuses parameter for option "load_file" is ["num_hid", "num_vis"],
        then the options num_hid and num_vis are not mandatory as long as load_file is specified.
        Use the special flag EXCLUDE_ALL to allow an option to make all other options optional.
        """

        assert name not in self.options
        self.options[name] = Option(letter, name, desc, parser, set_once, default, excuses, requires, save)

    def set_value(self, name, value, parse=True):
        self.options[name].set_value(value, parse=parse)

    def get_value(self, name):
        return self.options[name].value

    def delete_option(self, name):
        if name in self.options:
            del self.options[name]

    def parse(self, eval_expr_defaults=False):
        """Parses the options in sys.argv based on the options added to this parser. The
        default behavior is to leave any expression default options as OptionExpression objects.
        Set eval_expr_defaults=True to circumvent this."""
        short_opt_str = ''.join(["%s:" % self.options[name].letter for name in self.options if len(self.options[name].letter) == 1])
        long_opts = ["%s=" % self.options[name].letter for name in self.options if len(self.options[name].letter) > 1]
        (go, ga) = getopt(sys.argv[1:], short_opt_str, longopts=long_opts)
        dic = dict(go)

        for o in self.get_options_list(sort_order=self.SORT_EXPR_LAST):
            if o.prefixed_letter in dic:
                o.set_value(dic[o.prefixed_letter])
            else:
                # check if excused or has default
                excused = max([o2.prefixed_letter in dic for o2 in self.options.values() if o2.excuses == self.EXCLUDE_ALL or o.name in o2.excuses])
                if not excused and o.default is None:
                    raise OptionMissingException("Option %s (%s) not supplied" % (o.prefixed_letter, o.desc))
                o.set_default()
            # check requirements
            if o.prefixed_letter in dic:
                for o2 in self.get_options_list(sort_order=self.SORT_LETTER):
                    if o2.name in o.requires and o2.prefixed_letter not in dic:
                        raise OptionMissingException("Option %s (%s) requires option %s (%s)" % (o.prefixed_letter, o.desc,
                                                                                                 o2.prefixed_letter, o2.desc))
        if eval_expr_defaults:
            self.eval_expr_defaults()
        return self.options

    def merge_from(self, op2):
        """Merges the options in op2 into this instance, but does not overwrite
        this instances's SET options with op2's default values."""
        for name, o in self.options.iteritems():
            if name in op2.options and (op2.options[name].value_given or not op2.options[name].save):
                if op2.options[name].set_once:
                    print "Option %s (%s) cannot be changed" % (op2.options[name].prefixed_letter, op2.options[name].desc)
                    continue
                self.options[name] = op2.options[name]
        for name in op2.options:
            if name not in self.options:
                self.options[name] = op2.options[name]

    def eval_expr_defaults(self):
        env = dict([(name, o.value) for name, o in self.options.iteritems()])
        for o in self.options.values():
            o.eval_expr_default(env)

    def all_values_given(self):
        return max([o.value_given for o in self.options.values() if o.default is not None])

    def get_options_list(self, sort_order=SORT_LETTER):
        """ Returns the list of Option objects in this OptionParser,
        sorted as specified"""

        cmp = lambda x, y: (x.desc < y.desc and -1 or 1)
        if sort_order == self.SORT_LETTER:
            cmp = lambda x, y: (x.letter < y.letter and -1 or 1)
        elif sort_order == self.SORT_EXPR_LAST:
            cmp = lambda x, y: (type(x.default) == OptionExpression and 1 or -1)
        return sorted(self.options.values(), cmp=cmp)

    def print_usage(self, print_constraints=False):
        print "%s usage:" % os.path.basename(sys.argv[0])
        opslist = self.get_options_list()

        usage_strings = []
        num_def = 0
        for o in opslist:
            excs = ' '
            if o.default is None:
                excs = ', '.join(sorted([o2.prefixed_letter for o2 in self.options.values() if o2.excuses == self.EXCLUDE_ALL or o.name in o2.excuses]))
            reqs = ', '.join(sorted([o2.prefixed_letter for o2 in self.options.values() if o2.name in o.requires]))
            usg = (OptionsParser._bold(o.prefixed_letter) + " <%s>" % o.parser.get_type_str(), o.desc, ("[%s]" % o.get_str_value(get_default_str=True)) if not o.default is None else None, excs, reqs)
            if o.default is None:
                usage_strings += [usg]
            else:
                usage_strings.insert(num_def, usg)
                num_def += 1

        col_widths = [self._longest_value(usage_strings, key=lambda x:x[i]) for i in range(len(usage_strings[0]) - 1)]

        col_names = ["    Option", "Description", "Default"]
        if print_constraints:
            col_names += ["Excused by", "Requires"]
        for i, s in enumerate(col_names):
            print self._bold(s.ljust(col_widths[i])),

        print ""
        for l, d, de, ex, req in usage_strings:
            if de is None:
                de = ' '
                print ("     %s  -" % l.ljust(col_widths[0])), d.ljust(col_widths[1]), de.ljust(col_widths[2]),
            else:
                print ("    [%s] -" % l.ljust(col_widths[0])), d.ljust(col_widths[1]), de.ljust(col_widths[2]),
            if print_constraints:
                print ex.ljust(col_widths[3]), req
            else:
                print ""

    def print_values(self):
        longest_desc = self._longest_value(self.options.values(), key=lambda x:x.desc)
        longest_def_value = self._longest_value([v for v in self.options.values() if not v.value_given and not v.default is None],
                                                 key=lambda x:x.get_str_value())
        for o in self.get_options_list(sort_order=self.SORT_DESC):
            print "%s: %s %s" % (o.desc.ljust(longest_desc), o.get_str_value().ljust(longest_def_value), (not o.value_given and not o.default is None) and "[DEFAULT]" or "")

    @staticmethod
    def _longest_value(values, key=lambda x:x):
        mylen = lambda x: 0 if x is None else len(x)
        return mylen(key(max(values, key=lambda x:mylen(key(x)))))

    @staticmethod
    def _bold(str):
        return TERM_BOLD_START + str + TERM_BOLD_END

class OptionException(Exception):
    pass

class OptionMissingException(OptionException):
    pass

class OptionParser:
    @staticmethod
    def parse(value):
        return str(value)

    @staticmethod
    def to_string(value):
        return str(value)

    @staticmethod
    def get_type_str():
        pass

class IntegerOptionParser(OptionParser):
    @staticmethod
    def parse(value):
        try:
            return int(value)
        except:
            raise OptionException("argument is not an integer")

    @staticmethod
    def get_type_str():
        return "int"

    @staticmethod
    def is_type(value):
        return type(value) == int

class BooleanOptionParser(OptionParser):
    @staticmethod
    def parse(value):
        try:
            v = int(value)
            if not v in (0,1):
                raise OptionException
            return v
        except:
            raise OptionException("argument is not a boolean")

    @staticmethod
    def get_type_str():
        return "0/1"

    @staticmethod
    def is_type(value):
        return type(value) == int and value in (0, 1)

class StringOptionParser(OptionParser):
    @staticmethod
    def get_type_str():
        return "string"

    @staticmethod
    def is_type(value):
        return type(value) == str

class FloatOptionParser(OptionParser):
    @staticmethod
    def parse(value):
        try:
            return float(value)
        except:
            raise OptionException("argument is not a float")

    @staticmethod
    def to_string(value):
        return "%.6g" % value

    @staticmethod
    def get_type_str():
        return "float"

    @staticmethod
    def is_type(value):
        return type(value) == float

class RangeOptionParser(OptionParser):
    @staticmethod
    def parse(value):
        m = re.match("^(\d+)\-(\d+)$", value)
        try:
            if m: return range(int(m.group(1)), int(m.group(2)) + 1)
            return [int(value)]
        except:
            raise OptionException("argument is neither an integer nor a range")

    @staticmethod
    def to_string(value):
        return "%d-%d" % (value[0], value[-1])

    @staticmethod
    def get_type_str():
        return "int[-int]"

    @staticmethod
    def is_type(value):
        return type(value) == list

class ListOptionParser(OptionParser):
    """
    A parser that parses a delimited list of items. If the "parsers"
    argument is a list of parsers, then the list of items must have the form and length
    specified by that list.

    Example:
    ListOptionParser([FloatOptionParser, IntegerOptionParser])

    would parse "0.5,3" but not "0.5,3,0.6" or "0.5" or "3,0.5".

    If the "parsers" argument is another parser, then the list of items may be of
    arbitrary length, but each item must be parseable by the given parser.

    Example:
    ListOptionParser(FloatOptionParser)

    would parse "0.5" and "0.5,0.3" and "0.5,0.3,0.6", etc.
    """
    def __init__(self, parsers, sepchar=','):
        self.parsers = parsers
        self.sepchar = sepchar

    def parse(self, value):
        values = value.split(self.sepchar)
        if type(self.parsers) == list and len(values) != len(self.parsers):
            raise OptionException("requires %d arguments, given %d" % (len(self.parsers), len(values)))

        try:
            if type(self.parsers) == list:
                return [p.parse(v) for p, v in zip(self.parsers, values)]
            return [self.parsers.parse(v) for v in values]
        except:
            raise OptionException("argument is not of the form %s" % self.get_type_str())

    def to_string(self, value):
        if type(self.parsers) == list:
            return self.sepchar.join([p.to_string(v) for p, v in zip(self.parsers, value)])
        return self.sepchar.join([self.parsers.to_string(v) for v in value])

    def get_type_str(self):
        if type(self.parsers) == list:
            return self.sepchar.join([p.get_type_str() for p in self.parsers])
        return "%s%s..." % (self.parsers.get_type_str(), self.sepchar)

    @staticmethod
    def is_type(value):
        return type(value) == list

class OptionExpression:
    """
    This allows you to specify option values in terms of other option values.
    Example:
    op.add_option("eps-w", "eps_w", ListOptionParser(FloatOptionParser), "Weight learning rates for each layer")
    op.add_option("eps-b", "eps_b", ListOptionParser(FloatOptionParser), "Bias learning rates for each layer", default=OptionExpression("[o * 10 for o in eps_w]"))

    This says: the default bias learning rate for each layer (of a neural net) is 10
    times the weight learning rate for that layer.
    """
    def __init__(self, expr):
        self.expr = expr

    def evaluate(self, options):
        locals().update(options)
        try:
            return eval(self.expr)
        except Exception, e:
            raise OptionException("expression '%s': unable to parse: %s" % (self.expr, e))

########NEW FILE########
__FILENAME__ = ordereddict
# Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
# Passes Python2.7's test suite and incorporates all the latest updates.

try:
    from thread import get_ident as _get_ident
except ImportError:
    from dummy_thread import get_ident as _get_ident

try:
    from _abcoll import KeysView, ValuesView, ItemsView
except ImportError:
    pass


class OrderedDict(dict):
    'Dictionary that remembers insertion order'
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as for regular dictionaries.

    # The internal self.__map dictionary maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

    def __init__(self, *args, **kwds):
        '''Initialize an ordered dictionary.  Signature is the same as for
        regular dictionaries, but keyword arguments are not recommended
        because their insertion order is arbitrary.

        '''
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__root = root = []                     # sentinel node
            root[:] = [root, root, None]
            self.__map = {}
        self.__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link which goes at the end of the linked
        # list, and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            root = self.__root
            last = root[0]
            last[1] = root[0] = self.__map[key] = [last, root, key]
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which is
        # then removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link_prev, link_next, key = self.__map.pop(key)
        link_prev[1] = link_next
        link_next[0] = link_prev

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        root = self.__root
        curr = root[1]
        while curr is not root:
            yield curr[2]
            curr = curr[1]

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        root = self.__root
        curr = root[0]
        while curr is not root:
            yield curr[2]
            curr = curr[0]

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        try:
            for node in self.__map.itervalues():
                del node[:]
            root = self.__root
            root[:] = [root, root, None]
            self.__map.clear()
        except AttributeError:
            pass
        dict.clear(self)

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        if not self:
            raise KeyError('dictionary is empty')
        root = self.__root
        if last:
            link = root[0]
            link_prev = link[0]
            link_prev[1] = root
            root[0] = link_prev
        else:
            link = root[1]
            link_next = link[1]
            root[1] = link_next
            link_next[0] = root
        key = link[2]
        del self.__map[key]
        value = dict.pop(self, key)
        return key, value

    # -- the following methods do not depend on the internal structure --

    def keys(self):
        'od.keys() -> list of keys in od'
        return list(self)

    def values(self):
        'od.values() -> list of values in od'
        return [self[key] for key in self]

    def items(self):
        'od.items() -> list of (key, value) pairs in od'
        return [(key, self[key]) for key in self]

    def iterkeys(self):
        'od.iterkeys() -> an iterator over the keys in od'
        return iter(self)

    def itervalues(self):
        'od.itervalues -> an iterator over the values in od'
        for k in self:
            yield self[k]

    def iteritems(self):
        'od.iteritems -> an iterator over the (key, value) items in od'
        for k in self:
            yield (k, self[k])

    def update(*args, **kwds):
        '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

        If E is a dict instance, does:           for k in E: od[k] = E[k]
        If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
        Or if E is an iterable of items, does:   for k, v in E: od[k] = v
        In either case, this is followed by:     for k, v in F.items(): od[k] = v

        '''
        if len(args) > 2:
            raise TypeError('update() takes at most 2 positional '
                            'arguments (%d given)' % (len(args),))
        elif not args:
            raise TypeError('update() takes at least 1 argument (0 given)')
        self = args[0]
        # Make progressively weaker assumptions about "other"
        other = ()
        if len(args) == 2:
            other = args[1]
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, 'keys'):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    __update = update  # let subclasses override update without breaking __init__

    __marker = object()

    def pop(self, key, default=__marker):
        '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.

        '''
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        if key in self:
            return self[key]
        self[key] = default
        return default

    def __repr__(self, _repr_running={}):
        'od.__repr__() <==> repr(od)'
        call_key = id(self), _get_ident()
        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())
        finally:
            del _repr_running[call_key]

    def __reduce__(self):
        'Return state information for pickling'
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
        and values equal to v (which defaults to None).

        '''
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # -- the following methods are only used in Python 2.7 --

    def viewkeys(self):
        "od.viewkeys() -> a set-like object providing a view on od's keys"
        return KeysView(self)

    def viewvalues(self):
        "od.viewvalues() -> an object providing a view on od's values"
        return ValuesView(self)

    def viewitems(self):
        "od.viewitems() -> a set-like object providing a view on od's items"
        return ItemsView(self)

########NEW FILE########
__FILENAME__ = shownet
# Copyright (c) 2011, Alex Krizhevsky (akrizhevsky@gmail.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import numpy
import sys
import getopt as opt
from util import *
from math import sqrt, ceil, floor
import os
from gpumodel import IGPUModel
import random as r
import numpy.random as nr
from convnet import ConvNet
from options import *

try:
    import pylab as pl
except:
    print "This script requires the matplotlib python library (Ubuntu/Fedora package name python-matplotlib). Please install it."
    sys.exit(1)

class ShowNetError(Exception):
    pass

class ShowConvNet(ConvNet):
    def __init__(self, op, load_dic):
        ConvNet.__init__(self, op, load_dic)

    def get_gpus(self):
        self.need_gpu = self.op.get_value('show_preds') or self.op.get_value('write_features')
        if self.need_gpu:
            ConvNet.get_gpus(self)

    def init_data_providers(self):
        class Dummy:
            def advance_batch(self):
                pass
        if self.need_gpu:
            ConvNet.init_data_providers(self)
        else:
            self.train_data_provider = self.test_data_provider = Dummy()

    def import_model(self):
        if self.need_gpu:
            ConvNet.import_model(self)

    def init_model_state(self):
        #ConvNet.init_model_state(self)
        if self.op.get_value('show_preds'):
            self.sotmax_idx = self.get_layer_idx(self.op.get_value('show_preds'), check_type='softmax')
        if self.op.get_value('write_features'):
            self.ftr_layer_idx = self.get_layer_idx(self.op.get_value('write_features'))

    def init_model_lib(self):
        if self.need_gpu:
            ConvNet.init_model_lib(self)

    def plot_cost(self):
        if self.show_cost not in self.train_outputs[0][0]:
            raise ShowNetError("Cost function with name '%s' not defined by given convnet." % self.show_cost)
        train_errors = [o[0][self.show_cost][self.cost_idx] for o in self.train_outputs]
        test_errors = [o[0][self.show_cost][self.cost_idx] for o in self.test_outputs]

        numbatches = len(self.train_batch_range)
        test_errors = numpy.row_stack(test_errors)
        test_errors = numpy.tile(test_errors, (1, self.testing_freq))
        test_errors = list(test_errors.flatten())
        test_errors += [test_errors[-1]] * max(0,len(train_errors) - len(test_errors))
        test_errors = test_errors[:len(train_errors)]

        numepochs = len(train_errors) / float(numbatches)
        pl.figure(1)
        x = range(0, len(train_errors))
        pl.plot(x, train_errors, 'k-', label='Training set')
        pl.plot(x, test_errors, 'r-', label='Test set')
        pl.legend()
        ticklocs = range(numbatches, len(train_errors) - len(train_errors) % numbatches + 1, numbatches)
        epoch_label_gran = int(ceil(numepochs / 20.)) # aim for about 20 labels
        epoch_label_gran = int(ceil(float(epoch_label_gran) / 10) * 10) # but round to nearest 10
        ticklabels = map(lambda x: str((x[1] / numbatches)) if x[0] % epoch_label_gran == epoch_label_gran-1 else '', enumerate(ticklocs))

        pl.xticks(ticklocs, ticklabels)
        pl.xlabel('Epoch')
#        pl.ylabel(self.show_cost)
        pl.title(self.show_cost)

    def make_filter_fig(self, filters, filter_start, fignum, _title, num_filters, combine_chans):
        FILTERS_PER_ROW = 16
        MAX_ROWS = 16
        MAX_FILTERS = FILTERS_PER_ROW * MAX_ROWS
        num_colors = filters.shape[0]
        f_per_row = int(ceil(FILTERS_PER_ROW / float(1 if combine_chans else num_colors)))
        filter_end = min(filter_start+MAX_FILTERS, num_filters)
        filter_rows = int(ceil(float(filter_end - filter_start) / f_per_row))

        filter_size = int(sqrt(filters.shape[1]))
        fig = pl.figure(fignum)
        fig.text(.5, .95, '%s %dx%d filters %d-%d' % (_title, filter_size, filter_size, filter_start, filter_end-1), horizontalalignment='center')
        num_filters = filter_end - filter_start
        if not combine_chans:
            bigpic = n.zeros((filter_size * filter_rows + filter_rows + 1, filter_size*num_colors * f_per_row + f_per_row + 1), dtype=n.single)
        else:
            bigpic = n.zeros((3, filter_size * filter_rows + filter_rows + 1, filter_size * f_per_row + f_per_row + 1), dtype=n.single)

        for m in xrange(filter_start,filter_end ):
            filter = filters[:,:,m]
            y, x = (m - filter_start) / f_per_row, (m - filter_start) % f_per_row
            if not combine_chans:
                for c in xrange(num_colors):
                    filter_pic = filter[c,:].reshape((filter_size,filter_size))
                    bigpic[1 + (1 + filter_size) * y:1 + (1 + filter_size) * y + filter_size,
                           1 + (1 + filter_size*num_colors) * x + filter_size*c:1 + (1 + filter_size*num_colors) * x + filter_size*(c+1)] = filter_pic
            else:
                filter_pic = filter.reshape((3, filter_size,filter_size))
                bigpic[:,
                       1 + (1 + filter_size) * y:1 + (1 + filter_size) * y + filter_size,
                       1 + (1 + filter_size) * x:1 + (1 + filter_size) * x + filter_size] = filter_pic

        pl.xticks([])
        pl.yticks([])
        if not combine_chans:
            pl.imshow(bigpic, cmap=pl.cm.gray, interpolation='nearest')
        else:
            bigpic = bigpic.swapaxes(0,2).swapaxes(0,1)
            pl.imshow(bigpic, interpolation='nearest')

    def plot_filters(self):
        filter_start = 0 # First filter to show
        layer_names = [l['name'] for l in self.layers]
        if self.show_filters not in layer_names:
            raise ShowNetError("Layer with name '%s' not defined by given convnet." % self.show_filters)
        layer = self.layers[layer_names.index(self.show_filters)]
        filters = layer['weights'][self.input_idx]
        if layer['type'] == 'fc': # Fully-connected layer
            num_filters = layer['outputs']
            channels = self.channels
        elif layer['type'] in ('conv', 'local'): # Conv layer
            num_filters = layer['filters']
            channels = layer['filterChannels'][self.input_idx]
            if layer['type'] == 'local':
                filters = filters.reshape((layer['modules'], layer['filterPixels'][self.input_idx] * channels, num_filters))
                filter_start = r.randint(0, layer['modules']-1)*num_filters # pick out some random modules
                filters = filters.swapaxes(0,1).reshape(channels * layer['filterPixels'][self.input_idx], num_filters * layer['modules'])
                num_filters *= layer['modules']

        filters = filters.reshape(channels, filters.shape[0]/channels, filters.shape[1])
        # Convert YUV filters to RGB
        if self.yuv_to_rgb and channels == 3:
            R = filters[0,:,:] + 1.28033 * filters[2,:,:]
            G = filters[0,:,:] + -0.21482 * filters[1,:,:] + -0.38059 * filters[2,:,:]
            B = filters[0,:,:] + 2.12798 * filters[1,:,:]
            filters[0,:,:], filters[1,:,:], filters[2,:,:] = R, G, B
        combine_chans = not self.no_rgb and channels == 3

        # Make sure you don't modify the backing array itself here -- so no -= or /=
        filters = filters - filters.min()
        filters = filters / filters.max()

        self.make_filter_fig(filters, filter_start, 2, 'Layer %s' % self.show_filters, num_filters, combine_chans)

    def plot_predictions(self):
        data = self.get_next_batch(train=False)[2] # get a test batch
        num_classes = self.test_data_provider.get_num_classes()
        NUM_ROWS = 2
        NUM_COLS = 4
        NUM_IMGS = NUM_ROWS * NUM_COLS
        NUM_TOP_CLASSES = min(num_classes, 4) # show this many top labels

        label_names = self.test_data_provider.batch_meta['label_names']
        if self.only_errors:
            preds = n.zeros((data[0].shape[1], num_classes), dtype=n.single)
        else:
            preds = n.zeros((NUM_IMGS, num_classes), dtype=n.single)
            rand_idx = nr.randint(0, data[0].shape[1], NUM_IMGS)
            data[0] = n.require(data[0][:,rand_idx], requirements='C')
            data[1] = n.require(data[1][:,rand_idx], requirements='C')
        data += [preds]

        # Run the model
        self.libmodel.startFeatureWriter(data, self.sotmax_idx)
        self.finish_batch()

        fig = pl.figure(3)
        fig.text(.4, .95, '%s test case predictions' % ('Mistaken' if self.only_errors else 'Random'))
        if self.only_errors:
            err_idx = nr.permutation(n.where(preds.argmax(axis=1) != data[1][0,:])[0])[:NUM_IMGS] # what the net got wrong
            data[0], data[1], preds = data[0][:,err_idx], data[1][:,err_idx], preds[err_idx,:]

        data[0] = self.test_data_provider.get_plottable_data(data[0])
        for r in xrange(NUM_ROWS):
            for c in xrange(NUM_COLS):
                img_idx = r * NUM_COLS + c
                if data[0].shape[0] <= img_idx:
                    break
                pl.subplot(NUM_ROWS*2, NUM_COLS, r * 2 * NUM_COLS + c + 1)
                pl.xticks([])
                pl.yticks([])
                try:
                    img = data[0][img_idx,:,:,:]
                except IndexError:
                    # maybe greyscale?
                    img = data[0][img_idx,:,:]
                pl.imshow(img, interpolation='nearest')
                true_label = int(data[1][0,img_idx])

                img_labels = sorted(zip(preds[img_idx,:], label_names), key=lambda x: x[0])[-NUM_TOP_CLASSES:]
                pl.subplot(NUM_ROWS*2, NUM_COLS, (r * 2 + 1) * NUM_COLS + c + 1, aspect='equal')

                ylocs = n.array(range(NUM_TOP_CLASSES)) + 0.5
                height = 0.5
                width = max(ylocs)
                pl.barh(ylocs, [l[0]*width for l in img_labels], height=height, \
                        color=['r' if l[1] == label_names[true_label] else 'b' for l in img_labels])
                pl.title(label_names[true_label])
                pl.yticks(ylocs + height/2, [l[1] for l in img_labels])
                pl.xticks([width/2.0, width], ['50%', ''])
                pl.ylim(0, ylocs[-1] + height*2)

    def do_write_features(self):
        if not os.path.exists(self.feature_path):
            os.makedirs(self.feature_path)
        next_data = self.get_next_batch(train=False)
        b1 = next_data[1]
        num_ftrs = self.layers[self.ftr_layer_idx]['outputs']
        while True:
            batch = next_data[1]
            data = next_data[2]
            ftrs = n.zeros((data[0].shape[1], num_ftrs), dtype=n.single)
            self.libmodel.startFeatureWriter(data + [ftrs], self.ftr_layer_idx)

            # load the next batch while the current one is computing
            next_data = self.get_next_batch(train=False)
            self.finish_batch()
            path_out = os.path.join(self.feature_path, 'data_batch_%d' % batch)
            pickle(path_out, {'data': ftrs, 'labels': data[1]})
            print "Wrote feature file %s" % path_out
            if next_data[1] == b1:
                break
        pickle(os.path.join(self.feature_path, 'batches.meta'), {'source_model':self.load_file,
                                                                 'num_vis':num_ftrs})

    def start(self):
        self.op.print_values()
        if self.show_cost:
            self.plot_cost()
        if self.show_filters:
            self.plot_filters()
        if self.show_preds:
            self.plot_predictions()
        if self.write_features:
            self.do_write_features()
        pl.show()
        sys.exit(0)

    @classmethod
    def get_options_parser(cls):
        op = ConvNet.get_options_parser()
        for option in list(op.options):
            if option not in ('gpu', 'load_file', 'train_batch_range', 'test_batch_range'):
                op.delete_option(option)
        op.add_option("show-cost", "show_cost", StringOptionParser, "Show specified objective function", default="")
        op.add_option("show-filters", "show_filters", StringOptionParser, "Show learned filters in specified layer", default="")
        op.add_option("input-idx", "input_idx", IntegerOptionParser, "Input index for layer given to --show-filters", default=0)
        op.add_option("cost-idx", "cost_idx", IntegerOptionParser, "Cost function return value index for --show-cost", default=0)
        op.add_option("no-rgb", "no_rgb", BooleanOptionParser, "Don't combine filter channels into RGB in layer given to --show-filters", default=False)
        op.add_option("yuv-to-rgb", "yuv_to_rgb", BooleanOptionParser, "Convert RGB filters to YUV in layer given to --show-filters", default=False)
        op.add_option("channels", "channels", IntegerOptionParser, "Number of channels in layer given to --show-filters (fully-connected layers only)", default=0)
        op.add_option("show-preds", "show_preds", StringOptionParser, "Show predictions made by given softmax on test set", default="")
        op.add_option("only-errors", "only_errors", BooleanOptionParser, "Show only mistaken predictions (to be used with --show-preds)", default=False, requires=['show_preds'])
        op.add_option("write-features", "write_features", StringOptionParser, "Write test data features from given layer", default="", requires=['feature-path'])
        op.add_option("feature-path", "feature_path", StringOptionParser, "Write test data features to this path (to be used with --write-features)", default="")

        op.options['load_file'].default = None
        return op

if __name__ == "__main__":
    try:
        op = ShowConvNet.get_options_parser()
        op, load_dic = IGPUModel.parse_options(op)
        model = ShowConvNet(op, load_dic)
        model.start()
    except (UnpickleError, ShowNetError, opt.GetoptError), e:
        print "----------------"
        print "Error:"
        print e

########NEW FILE########
__FILENAME__ = util
# Copyright (c) 2011, Alex Krizhevsky (akrizhevsky@gmail.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import cPickle
import os
import numpy as n
from math import sqrt

import gzip
import zipfile

class UnpickleError(Exception):
    pass

VENDOR_ID_REGEX = re.compile('^vendor_id\s+: (\S+)')
GPU_LOCK_NO_SCRIPT = -2
GPU_LOCK_NO_LOCK = -1

try:
    import magic
    ms = magic.open(magic.MAGIC_NONE)
    ms.load()
except ImportError: # no magic module
    ms = None

def get_gpu_lock(id=-1):
    import imp
    lock_script_path = '/u/tang/bin/gpu_lock2.py'
    if os.path.exists(lock_script_path):
        locker = imp.load_source("", lock_script_path)
        if id == -1:
            return locker.obtain_lock_id()
        print id
        got_id = locker._obtain_lock(id)
        return id if got_id else GPU_LOCK_NO_LOCK
    return GPU_LOCK_NO_SCRIPT if id < 0 else id

def pickle(filename, data, compress=False):
    if compress:
        fo = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
        fo.writestr('data', cPickle.dumps(data, -1))
    else:
        fo = open(filename, "wb")
        cPickle.dump(data, fo, protocol=cPickle.HIGHEST_PROTOCOL)
    fo.close()

def unpickle(filename):
    if not os.path.exists(filename):
        raise UnpickleError("Path '%s' does not exist." % filename)
    if ms is not None and ms.file(filename).startswith('gzip'):
        fo = gzip.open(filename, 'rb')
        dict = cPickle.load(fo)
    elif ms is not None and ms.file(filename).startswith('Zip'):
        fo = zipfile.ZipFile(filename, 'r', zipfile.ZIP_DEFLATED)
        dict = cPickle.loads(fo.read('data'))
    else:
        fo = open(filename, 'rb')
        dict = cPickle.load(fo)

    fo.close()
    return dict

def tryint(s):
    try:
        return int(s)
    except:
        return s

def alphanum_key(s):
    return [tryint(c) for c in re.split('([0-9]+)', s)]

def is_intel_machine():
    f = open('/proc/cpuinfo')
    for line in f:
        m = VENDOR_ID_REGEX.match(line)
        if m:
            f.close()
            return m.group(1) == 'GenuineIntel'
    f.close()
    return False

def get_cpu():
    if is_intel_machine():
        return 'intel'
    return 'amd'

def is_windows_machine():
    return os.name == 'nt'

########NEW FILE########
