# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""
Compile YOLO-V2 and YOLO-V3 in DarkNet Models
=============================================
**Author**: `Siju Samuel <https://siju-samuel.github.io/>`_

This article is an introductory tutorial to deploy darknet models with TVM.
All the required models and libraries will be downloaded from the internet by the script.
This script runs the YOLO-V2 and YOLO-V3 Model with the bounding boxes
Darknet parsing have dependancy with CFFI and CV2 library
Please install CFFI and CV2 before executing this script

.. code-block:: bash

  pip install cffi
  pip install opencv-python
"""

# numpy and matplotlib
import numpy as np
import matplotlib.pyplot as plt
import sys, pdb

# tvm, relay
import tvm
from tvm import relay
from ctypes import *
from tvm.contrib.download import download_testdata
from tvm.relay.testing.darknet import __darknetffi__
import tvm.relay.testing.yolo_detection
import tvm.relay.testing.darknet

######################################################################
# Choose the model
# -----------------------
# Models are: 'yolov2', 'yolov3' or 'yolov3-tiny'

# Model name
MODEL_NAME = 'resnext50'

######################################################################
# Download required files
# -----------------------
# Download cfg and weights file if first time.

# Download and Load darknet library
cfg_path = '/data/base_model/darknet/resnext50.cfg'
weights_path = '/data/base_model/darknet/resnext50.weights'
lib_path = '/data/tvm/libdarknet2.0.so'

DARKNET_LIB = __darknetffi__.dlopen(lib_path)
net = DARKNET_LIB.load_network(cfg_path.encode('utf-8'), weights_path.encode('utf-8'), 0)
dtype = 'float32'
batch_size = 1

data = np.empty([batch_size, net.c, net.h, net.w], dtype)
shape_dict = {'data': data.shape}
print("Converting darknet to relay functions...")
mod, params = relay.frontend.from_darknet(net, dtype=dtype, shape=data.shape)

######################################################################
# Import the graph to Relay
# -------------------------
# compile the model
target = 'llvm'
target_host = 'llvm'
ctx = tvm.cpu(0)
data = np.empty([batch_size, net.c, net.h, net.w], dtype)
shape = {'data': data.shape}
print("Compiling the model...")
with relay.build_config(opt_level=3):
    graph, lib, params = relay.build(mod,
                                     target=target,
                                     target_host=target_host,
                                     params=params)

[neth, netw] = shape['data'][2:] # Current image shape is 608x608
######################################################################
# Load a test image
# -----------------
img_path = '/data/tvm/eagle.jpg'

data = tvm.relay.testing.darknet.load_image(img_path, netw, neth)
######################################################################
# Execute on TVM Runtime
# ----------------------
# The process is no different from other examples.
from tvm.contrib import graph_runtime

m = graph_runtime.create(graph, lib, ctx)

# set inputs
m.set_input('data', tvm.nd.array(data.astype(dtype)))
m.set_input(**params)
# execute
print("Running the test image...")
m.run()
# get outputs
output = m.get_output(0).asnumpy()
index = np.argmax(output)
conf = output[0, index]

short_name_list = '/data/tvm/imagenet.shortnames.list'
with open(short_name_list) as fp:
    labels = fp.readlines()
print(index, conf, labels[index])
