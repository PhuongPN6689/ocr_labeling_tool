import requests


from tkinter import messagebox
from src.handle import external_data


def test_connection():
    try:
        response = requests.get(f"{external_data.base_url}/")
        assert response.status_code == 200
    except Exception as e:
        messagebox.showerror("Error", str(e))
        raise e


def clean_path(path):
    if path.startswith("/"):
        path = path[:-1]
    return path


def get_data(path, params=None):
    try:
        path = clean_path(path)
        response = requests.get(f"{external_data.base_url}/{path}", params=params)
        assert response.status_code == 200
        return response
    except Exception as e:
        messagebox.showerror("Error", str(e))
        raise e


def post_data(path, json):
    try:
        path = clean_path(path)
        response = requests.post(f"{external_data.base_url}/{path}", json=json)
        assert response.status_code == 200
        return response
    except Exception as e:
        messagebox.showerror("Error", str(e))
        raise e


def put_data(path, json):
    try:
        path = clean_path(path)
        response = requests.put(f"{external_data.base_url}/{path}", json=json)
        assert response.status_code == 200
        return response
    except Exception as e:
        messagebox.showerror("Error", str(e))
        raise e


def delete_data(path, params):
    try:
        path = clean_path(path)
        response = requests.delete(f"{external_data.base_url}/{path}", params=params)
        assert response.status_code == 200
        return response
    except Exception as e:
        messagebox.showerror("Error", str(e))
        raise e
