import torch
import torchvision.models as models
from PIL import Image
import requests
import io

model = models.resnet50(pretrained=True)

model.eval()


def extract_embedding(image_url):

    r = requests.get(image_url)

    img = Image.open(io.BytesIO(r.content))

    tensor = preprocess(img).unsqueeze(0)

    embedding = model(tensor)

    return embedding.detach().numpy()