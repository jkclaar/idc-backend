from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from keras.utils.io_utils import path_to_string
from tensorflow.keras.models import load_model
import numpy as np

from PIL import Image  # encode into a bytesIO and #decode

import base64
from idc.processing import split, stitch
from idc.gradcam import make_heatmap, superimpose_heatmap
import matplotlib.pyplot as plt
from google.cloud import storage
import uuid


app = FastAPI()
model = load_model("model.h5")
IDC_BUCKET = "idc_bucket"


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.get("/")
def index():
    return {"greeting": "Hello nadia"}


@app.post("/predict")
def predict(file: bytes = File(...)):

    file_decode = base64.b64decode(file)
    long_array = np.frombuffer(file_decode, dtype=np.uint8)

    count = long_array.shape[0] // 7500
    pics = np.reshape(long_array, (count, 50, 50, 3)) / 255

    model = load_model("model.h5")

    prediction = model.predict(pics)[:, 0].tolist()

    return {"prediction": prediction}


@app.post("/annotate")
def annotate(file: UploadFile = File(...)):
    # image = file.file.read()
    image = Image.open(file.file)
    height, width, _ = np.asarray(image).shape

    round_height = int(np.ceil(height / 50))
    round_width = int(np.ceil(width / 50))

    pics = split(image) / 255
    heatmap = make_heatmap(pics, model)
    grad_cam = superimpose_heatmap(pics, heatmap)

    # high_image = np.reshape(grad_cam, (round_height * 50, round_width * 50, 3)) Why does this not work?
    high_image = stitch(grad_cam, round_height * 50, round_width * 50)[
        :height,
        :width,
    ]

    print(f"input shape is: ({height}, {width}, 3)")
    print(f"output shape is {high_image.shape}")

    myuuid = uuid.uuid4()
    path = f"{myuuid}.png"

    # save the image as a png
    im = Image.fromarray(high_image)  # this hsould be high_image
    im.save(path)

    gcs = storage.Client()
    bucket = gcs.get_bucket(IDC_BUCKET)
    blob = bucket.blob(path)
    blob.upload_from_filename(path)

    return {"url": blob.public_url}


# if __name__ == "__main__":
#     annotate()
