import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow import keras
from PIL import Image as Image
from keras.models import load_model

# Display
from IPython.display import Image, display
import matplotlib.pyplot as plt
import matplotlib.cm as cm


def make_heatmap(img_array, model, last_conv_layer_name="conv2d_5", pred_index=None):
    # First, we create a model that maps the input image to the activations
    # of the last conv layer as well as the output predictions
    grad_model = tf.keras.models.Model(
        [model.inputs], [model.get_layer(last_conv_layer_name).output, model.output]
    )

    # Then, we compute the gradient of the top predicted class for our input image
    # with respect to the activations of the last conv layer
    with tf.GradientTape() as tape:
        last_conv_layer_output, preds = grad_model(img_array)
        if pred_index is None:
            pred_index = tf.argmax(preds[0])
        class_channel = preds[:, pred_index]

    # This is the gradient of the output neuron (top predicted or chosen)
    # with regard to the output feature map of the last conv layer
    grads = tape.gradient(class_channel, last_conv_layer_output)

    # This is a vector where each entry is the mean intensity of the gradient
    # over a specific feature map channel
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    # We multiply each channel in the feature map array
    # by "how important this channel is" with regard to the top predicted class
    # then sum all the channels to obtain the heatmap class activation

    # The line below returns only the heatmap for the first image. Keep commented.
    # last_conv_layer_output = last_conv_layer_output[0]

    heatmap = np.dot(last_conv_layer_output, pooled_grads[..., tf.newaxis])
    heatmap = tf.squeeze(heatmap)

    # Normalize the heatmap between 0 & 1
    heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
    return np.uint8(heatmap.numpy() * 255)


def superimpose_heatmap(img, heatmap, alpha=0.4):
    # Rescale heatmap to a range 0-255
    # heatmap = np.uint8(255 * heatmap)

    # Use jet colormap to colorize heatmap
    jet = cm.get_cmap("jet")

    # Use RGB values of the colormap
    jet_colors = jet(np.arange(256))[:, :3]
    jet_heatmap = jet_colors[heatmap]

    # Superimpose the heatmap on original image
    superimposed_images = jet_heatmap * alpha + img

    superimposed_images = np.clip(superimposed_images, a_min=None, a_max=1)
    superimposed_images = np.uint8(255 * superimposed_images)

    # Returns an array of images with with heatmaps superimposed
    return superimposed_images


if __name__ == "__main__":
    X = np.load("raw_data/X.npy") / 255
    # img_array = np.expand_dims(X[5], 0)
    img_array = X[0:2]
    model = load_model("model.h5")

    heatmap = make_heatmap(img_array, model)
    grad_cam = superimpose_heatmap(img_array, heatmap)
    plt.imshow(grad_cam[1])
    plt.show()