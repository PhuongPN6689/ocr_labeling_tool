import os

FILE_DIRECTORY = os.path.dirname(os.path.realpath(__file__)).replace('\\', '/')
PROJECT_DIRECTORY = '/'.join(FILE_DIRECTORY.split('/')[:-1])

vietocr_model_path = f'{PROJECT_DIRECTORY}/models/vietocr.pth'
