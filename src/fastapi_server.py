from fastapi import Body
from uvicorn.config import Config
from uvicorn.server import Server

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.handle import load_images, get_image, delete_image, get_label, save_label, image_to_base64, external_data

app = FastAPI()
port = 8000
server = None

@app.get("/")
async def read_root():
    return {"message": "Hello World"}


@app.get("/folder")
async def read_root():
    return {"image_folder": external_data.image_folder, "label_folder": external_data.label_folder, "recycle_bin_folder": external_data.recycle_bin_folder}


@app.get("/load_images")
async def _load_images():
    images = load_images()
    return JSONResponse(content={"images": images})


@app.get("/get_image")
async def _get_image(image_filename: str):
    image = get_image(image_filename)
    img_str = image_to_base64(image, image_filename)
    return JSONResponse(content={"image": img_str})


@app.delete("/delete_image")
async def _delete_image(image_filename: str):
    print(image_filename)
    delete_image(image_filename)
    return JSONResponse(content={"status": "success"})


@app.get("/get_label")
async def _get_label(image_filename: str):
    label = get_label(image_filename)
    return JSONResponse(content={"label": label})


@app.post("/save_label")
async def _save_label(image_filename: str = Body(None), label: str = Body(None)):
    save_label(image_filename, label)
    return JSONResponse(content={"status": "success"})


def start_fastapi():
    global server
    config = Config(app, host="0.0.0.0", port=port)
    server = Server(config=config)
    server.run()


def stop_fastapi():
    global server
    server.should_exit = True
    server.shutdown()


def set_port(new_port):
    global port
    port = new_port
