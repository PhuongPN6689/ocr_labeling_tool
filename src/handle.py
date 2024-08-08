import base64
import json
import os
from io import BytesIO

from PIL import Image


class BaseApp():
    def __init__(self):
        self.image_folder = None
        self.label_folder = None
        self.recycle_bin_folder = None
        self.base_url = None


external_data = BaseApp()


def set_external_data(data):
    global external_data
    external_data = data


def load_images():
    return [f for f in os.listdir(external_data.image_folder) if f.lower().endswith(('png', 'jpg', 'jpeg'))]


def get_image(image_filename):
    image_path = os.path.join(external_data.image_folder, image_filename)
    image = Image.open(image_path)
    return image


def get_label_filename(image_filename):
    return image_filename.rsplit(".", maxsplit=1)[0] + ".json"


def get_label(image_filename):
    json_path = os.path.join(external_data.label_folder, get_label_filename(image_filename))
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            content = json.load(f)
        return content["label"]
    return ""


def save_label(image_filename, label):
    json_path = os.path.join(external_data.label_folder, get_label_filename(image_filename))
    content = {
        "image_path": image_filename,
        "label": label
    }
    with open(json_path, 'w') as f:
        f.write(json.dumps(content))


def delete_image(image_filename):
    if not os.path.exists(external_data.recycle_bin_folder):
        os.makedirs(external_data.recycle_bin_folder)

    if image_filename:
        # delete image
        image_path = os.path.join(external_data.image_folder, image_filename)
        recycle_bin_path = os.path.join(external_data.recycle_bin_folder, image_filename)
        os.rename(image_path, recycle_bin_path)
        # delete label
        label_filename = get_label_filename(image_filename)
        label_path = os.path.join(external_data.label_folder, label_filename)
        if os.path.exists(label_path):
            recycle_bin_label_path = os.path.join(external_data.recycle_bin_folder, label_filename)
            os.rename(label_path, recycle_bin_label_path)


def image_to_base64(image: Image, image_filename: str) -> str:
    buffered = BytesIO()
    image_format = image_filename.split(".")[-1]
    image_format = image_format if image_format in ["png", "jpeg", "jpg"] else "png"
    image_format = "jpeg" if image_format.lower() == "jpg" else image_format
    image.save(buffered, format=image_format)
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return img_str


def base64_to_image(img_str: str) -> Image:
    img_data = base64.b64decode(img_str)
    return Image.open(BytesIO(img_data))
