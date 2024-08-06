def load_ocr_model(model_name):
    if model_name == "VietOCR":
        from vietocr.tool.config import Cfg
        from vietocr.tool.predictor import Predictor
        config = Cfg.load_config_from_name('vgg_seq2seq')
        config['device'] = 'cpu'
        return Predictor(config)

    elif model_name == "EasyOCR":
        import easyocr
        return easyocr.Reader(['en', 'vi'], gpu=False)

    elif model_name == "Tesseract":
        from pytesseract import image_to_string
        return image_to_string

    else:
        return None
