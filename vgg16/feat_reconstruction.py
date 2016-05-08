import os
import numpy as np
import json

from keras import backend as K

from vgg16.model import VGG_16_mean 
from vgg16.model_headless import *

from utils.imutils import *
from utils.lossutils import *


dir = os.path.dirname(os.path.realpath(__file__))
vgg16Dir = dir
resultsDir = dir + '/../models/results'
dataDir = dir + '/../data'

print('Loading a cat image')
X_train = load_image(dataDir + '/overfit/000.jpg')
print("X_train shape:", X_train.shape)

print('Loading Van Gogh')
vanGoghPath = dataDir + '/paintings/vangogh.jpg'
X_train_paint = np.array([load_image(vanGoghPath)])
print("X_train_paint shape:", X_train_paint.shape)

print('Building white noise image')
input_style_data = create_noise_tensor(3, 256, 256)
input_feat_data = create_noise_tensor(3, 256, 256)
print("input_style_data shape:", input_style_data.shape)

print('Loading mean')
meanPath = vgg16Dir + '/vgg-16_mean.npy'
mean = VGG_16_mean(path=meanPath)

print('Loading VGG headless 5')
modelWeights = vgg16Dir + '/vgg-16_headless_5_weights.hdf5'
model = VGG_16_headless_5(modelWeights, trainable=False)
layer_dict = dict([(layer.name, layer) for layer in model.layers])
input_img = layer_dict['input'].input

# http://blog.keras.io/how-convolutional-neural-networks-see-the-world.html

layer_name = 'conv_1_1'
print('Creating labels for ' + layer_name)
out = layer_dict[layer_name].output
predict = K.function([input_img], [out])

out_plabels = predict([X_train_paint - mean])
out_ilabels = predict([X_train - mean])

print('Compiling VGG headless 1 for ' + layer_name + ' style reconstruction')
loss_style = grams_frobenius_error(out_plabels[0], out)
grads_style = K.gradients(loss_style, input_img)[0]
grads_style /= (K.sqrt(K.mean(K.square(grads_style))) + 1e-5)
iterate_style = K.function([input_img], [loss_style, grads_style])

print('Compiling VGG headless 1 for ' + layer_name + ' feature reconstruction')
loss_feat = euclidian_error(out_ilabels[0], out)
grads_feat = K.gradients(loss_feat, input_img)[0]
grads_feat /= (K.sqrt(K.mean(K.square(grads_feat))) + 1e-5)
iterate_feat = K.function([input_img], [loss_feat, grads_feat])

print('Training the image')
input_style_data -= mean
input_feat_data -= mean
step = 1e-00
loss_style_val = 1000000000
loss_feat_val = 1000000000
for i in range(50000):
    # Need to implement Adam
    if i == 100:
        step = 5e-01
    if i == 200:
        step = 1e-01

    # Style
    previous_loss_style_val = loss_style_val
    loss_style_val, grads_style_val = iterate_style([input_style_data])
    input_style_data -= grads_style_val * step

    # Feat
    previous_loss_feat_val = loss_feat_val
    loss_feat_val, grads_feat_val = iterate_feat([input_feat_data])
    input_feat_data -= grads_feat_val * step

    print(str(i) + ':', loss_style_val, loss_feat_val)

    if (np.abs(loss_style_val - previous_loss_style_val) < 0.01 or loss_style_val < 1) \
        and (np.abs(loss_feat_val - previous_loss_feat_val) < 0.01 or loss_feat_val < 1):
        break

print("Dumping final image")
fullOutPath = resultsDir + '/style_' + layer_name + ".png"
im = deprocess_image(input_style_data[0], fullOutPath)

fullOutPath = resultsDir + '/feat_' + layer_name + ".png"
im = deprocess_image(input_feat_data[0], fullOutPath)

