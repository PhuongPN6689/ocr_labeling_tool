import copy
import json
import logging

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import threading

from src.handle import load_images, get_image, delete_image, get_label, save_label, base64_to_image, BaseApp, \
    load_settings, save_settings
from src.ocr import load_ocr_model


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, is_open_server, is_connect_to_server, port, base_url):
        super().__init__(parent)
        self.is_open_server = is_open_server
        self.is_connect_to_server = is_connect_to_server
        self.port = port
        self.base_url = base_url

        self.title("Settings")
        self.geometry("700x300")

        # Create a frame to hold the settings in two rows
        frame = tk.Frame(self)
        frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Third row
        row0 = tk.Frame(frame)
        row0.pack(fill="x", pady=5)

        # Now IP address
        tk.Label(row0, text="IP Address:").pack(side="left", padx=5)
        self.ip_address_entry = tk.Entry(row0, width=20)
        self.ip_address_entry.pack(side="left", padx=5)

        # First row
        row1 = tk.Frame(frame)
        row1.pack(fill="x", pady=5)

        tk.Label(row1, text="Open Server Connection:").pack(side="left", padx=5)
        self.open_server = tk.BooleanVar()
        self.open_server.set(self.is_open_server)
        self.server_connection_check = tk.Checkbutton(row1, variable=self.open_server, command=self.open_server_click)
        self.server_connection_check.pack(side="left", padx=5)

        tk.Label(row1, text="Port:").pack(side="left", padx=5)
        self.port_entry = tk.Entry(row1, width=4)
        self.port_entry.insert(0, str(self.port))
        self.port_entry.pack(side="left", padx=5)

        # Second row
        row2 = tk.Frame(frame)
        row2.pack(fill="x", pady=5)

        tk.Label(row2, text="Connect to Another Server:").pack(side="left", padx=5)
        self.connect_to_server = tk.BooleanVar()
        self.connect_to_server.set(self.is_connect_to_server)
        self.another_server_connection_check = tk.Checkbutton(row2, variable=self.connect_to_server, command=self.connect_to_server_click)
        self.another_server_connection_check.pack(side="left", padx=5)

        tk.Label(row2, text="Base URL of Another Server:").pack(side="left", padx=5)
        self.base_url_entry = tk.Entry(row2, width=50)
        self.base_url_entry.insert(0, self.base_url)
        self.base_url_entry.pack(side="left", padx=5)

        save_button = tk.Button(self, text="Save", command=self.save_settings)
        save_button.pack(pady=20)

        # get local IP address
        import socket
        my_ip = socket.gethostbyname(socket.gethostname())
        self.ip_address_entry.insert(0, my_ip)

    def open_server_click(self):
        if self.open_server.get() and self.connect_to_server.get():
            self.open_server.set(True)
            self.connect_to_server.set(False)

    def connect_to_server_click(self):
        if self.open_server.get() and self.connect_to_server.get():
            self.open_server.set(False)
            self.connect_to_server.set(True)

    def save_settings(self):
        self.is_connect_to_server = self.connect_to_server.get()
        self.is_open_server = self.open_server.get()
        self.port = int(self.port_entry.get())
        self.base_url = self.base_url_entry.get()
        self.destroy()


class OCRLabelingTool(tk.Tk, BaseApp):
    def __init__(self):
        super().__init__()

        self.is_open_server = False
        self.is_connect_to_server = False
        self.port = 8000
        self.base_url = "http://127.0.0.1:8000"

        # Thiết lập cửa sổ chính
        self.title("OCR Labeling Tool")
        self.geometry("1400x700")

        # Biến để lưu trữ các thông tin cần thiết
        self.image = None
        self.image_filename = None
        self.image_folder = None
        self.label_folder = None
        self.recycle_bin_folder = None
        self.old_label_value = ''
        self.image_list = []
        self.current_image_index = 0
        self.auto_save = tk.BooleanVar()
        self.zoom_level = tk.StringVar(value="Auto")
        self.fixed_canvas_size = (800, 400)  # Kích thước cố định cho khu vực hiển thị ảnh
        self.model_name = None
        self.ocr_model = None
        self.log = []

        # Gọi các phương thức để tạo các thành phần giao diện
        self.create_widgets()
        self.bind_keys()

        self.cancel_update_saved_label = False
        self.bind("<Configure>", self.on_resize)
        self.resize_after_id = None

    def restore_session(self):
        settings = load_settings()

        is_open_server = settings.get('is_open_server', self.is_open_server)
        is_connect_to_server = settings.get('is_connect_to_server', self.is_connect_to_server)
        port = settings.get('port', self.port)
        base_url = settings.get('base_url', self.base_url)
        image_folder = settings.get('image_folder', self.image_folder)
        label_folder = settings.get('label_folder', self.label_folder)
        recycle_bin_folder = settings.get('recycle_bin_folder', self.recycle_bin_folder)

        if settings:
            old_session_message = f"Previous session found with these settings:\n\n"
            if is_connect_to_server:
                is_open_server = False
                old_session_message += f"Connect to server at {base_url}\n"
            else:
                if is_open_server:
                    old_session_message += f"Open server at port {port}\n"
                if image_folder:
                    old_session_message += f"Image folder: {image_folder}\n"
                if label_folder:
                    old_session_message += f"Label folder: {label_folder}\n"
                if recycle_bin_folder:
                    old_session_message += f"Recycle bin folder: {recycle_bin_folder}\n"
            restore_session = messagebox.askyesno("Restore Session", old_session_message, parent=self)
        else:
            restore_session = False

        if restore_session:
            self.is_open_server = is_open_server
            self.is_connect_to_server = is_connect_to_server
            self.port = port
            self.base_url = base_url
            self.image_folder = image_folder
            self.label_folder = label_folder
            self.recycle_bin_folder = recycle_bin_folder

            self.load_images_click()
            self.apply_server_settings(False, False)
            self.add_log("Restore session successfully")

    def auto_save_session(self):
        # Save settings on exit
        settings = {
            'is_open_server': self.is_open_server,
            'is_connect_to_server': self.is_connect_to_server,
            'port': self.port,
            'base_url': self.base_url,
            'image_folder': self.image_folder,
            'label_folder': self.label_folder,
            'recycle_bin_folder': self.recycle_bin_folder,
        }
        save_settings(settings)

    def create_widgets(self):
        # Cột 1: Khu vực bên trái
        left_frame = tk.Frame(self)
        left_frame.pack(side="left", fill="y", padx=10, pady=5)

        self.open_image_folder_button = tk.Button(left_frame, text="Open Image Folder", compound=tk.TOP, command=self.open_image_folder_click)
        self.open_image_folder_button.pack(pady=5, fill="x")

        self.open_label_folder_button = tk.Button(left_frame, text="Open Label Folder", compound=tk.TOP, command=self.open_label_folder_click)
        self.open_label_folder_button.pack(pady=5, fill="x")

        self.open_recycle_bin_folder_button = tk.Button(left_frame, text="Open Recycle Bin Folder", compound=tk.TOP, command=self.open_recycle_bin_click)
        self.open_recycle_bin_folder_button.pack(pady=5, fill="x")

        reload_button = tk.Button(left_frame, text="Reload Files", compound=tk.TOP, command=self.load_images_click)
        reload_button.pack(pady=5, fill="x")

        tk.Frame(left_frame).pack(fill="x", pady=15)

        # Dropdown OCR model options
        tk.Label(left_frame, text="OCR Model").pack()
        options = ["None", "VietOCR", "EasyOCR", "Tesseract"]
        self.model_dropdown = ttk.Combobox(left_frame, values=options)
        self.model_dropdown.bind("<<ComboboxSelected>>", self.on_model_change)
        self.model_dropdown.set(options[0])
        self.model_dropdown.pack(fill="x")

        self.auto_ocr_all_button = tk.Button(left_frame, text="Auto OCR All File", command=self.auto_ocr_all_click)
        self.auto_ocr_all_button.pack(pady=10, fill="x")

        self.check_error_button = tk.Button(left_frame, text="Check Error", command=self.check_error_click)
        self.check_error_button.pack(pady=10, fill="x")

        tk.Frame(left_frame).pack(fill="x", pady=15)

        server_settings_button = tk.Button(left_frame, text="Server setting", command=self.open_server_settings_click)
        server_settings_button.pack(pady=5, fill="x")

        help_button = tk.Button(left_frame, text="Help", command=self.help_click)
        help_button.pack(pady=5, fill="x")

        # Cột 2: Khu vực trung tâm
        center_frame = tk.Frame(self)
        center_frame.pack(side="left", expand=True, fill="both", padx=10, pady=5)
        self.center_frame = center_frame

        # Tùy chọn zoom
        zoom_frame = tk.Frame(center_frame)
        zoom_frame.pack(pady=5, fill="x")

        tk.Label(zoom_frame, text="Zoom:").pack(side="left", padx=5)

        for zoom in ["Auto", "50%", "100%", "200%", "400%", "600%", "800%"]:
            radio = tk.Radiobutton(zoom_frame, text=zoom, variable=self.zoom_level, value=zoom, command=self.display_image_click)
            radio.pack(side="left", padx=5)

        tk.Frame(zoom_frame).pack(side="left", fill="x")

        auto_save_checkbox = tk.Checkbutton(zoom_frame, variable=self.auto_save)
        auto_save_checkbox.pack(side="right", pady=5)

        tk.Label(zoom_frame, text='Auto save:').pack(side="right", fill="x")

        # Khu vực các nút nhấn
        button_frame = tk.Frame(center_frame)
        button_frame.pack(pady=5, fill="x")

        prev_image_button = tk.Button(button_frame, text="⇦ Prev Image", compound=tk.TOP, command=self.prev_image_click)
        prev_image_button.pack(side="left", padx=5, pady=5)

        next_image_button = tk.Button(button_frame, text="Next Image ⇨", compound=tk.TOP, command=self.next_image_click)
        next_image_button.pack(side="left", padx=5, pady=5)

        delete_img_button = tk.Button(button_frame, text="Delete Image", command=self.delete_img_click)
        delete_img_button.pack(side="left", padx=5, pady=5)

        tk.Frame(button_frame).pack(side="left", fill="x")

        save_button = tk.Button(button_frame, text="Save", command=self.save_label_click)
        save_button.pack(side="right", padx=5, pady=5)

        self.text_entry = tk.Entry(button_frame, font=("Consolas", 14))
        self.text_entry.pack(side="right", padx=5, pady=5)

        cancel_button = tk.Button(button_frame, text="Cancel change", command=self.cancel_change)
        cancel_button.pack(side="right", padx=5, pady=5)

        auto_ocr_button = tk.Button(button_frame, text="Auto OCR", command=self.auto_ocr_click)
        auto_ocr_button.pack(side="right", padx=5, pady=5)

        # Khu vực hiển thị ảnh với kích thước cố định
        self.canvas = tk.Canvas(center_frame, width=self.fixed_canvas_size[0], height=self.fixed_canvas_size[1])
        self.canvas.pack()

        # Cột 3: Khu vực bên phải
        right_frame = tk.Frame(self, width=400)
        right_frame.pack(side="right", fill="y", padx=5, pady=5)

        # Label bên trái
        tk.Label(right_frame, text="List image").grid(column=0, row=0, pady=5, sticky="w")

        # Tạo khung chứa Listbox và thanh cuộn
        listbox_frame_2 = tk.Frame(right_frame)
        listbox_frame_2.grid(column=0, row=1, pady=5, sticky="nsew")

        # Tạo Listbox
        self.file_listbox = tk.Listbox(listbox_frame_2, width=50)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        self.file_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(listbox_frame_2, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.file_listbox.yview)

        tk.Label(right_frame, text="Log").grid(column=0, row=2, pady=5, sticky="w")

        listbox_frame_1 = tk.Frame(right_frame)
        listbox_frame_1.grid(column=0, row=3, pady=5, sticky="nsew")

        self.status_label = tk.Text(listbox_frame_1, width=38)
        self.status_label.pack(side="left", fill="both", expand=True)

        scrollbar_1 = tk.Scrollbar(listbox_frame_1, orient="vertical")
        scrollbar_1.pack(side="right", fill="y")
        self.status_label.config(yscrollcommand=scrollbar_1.set)
        scrollbar_1.config(command=self.status_label.yview)

        # Đảm bảo các hàng 1 và 3 có thể mở rộng đều nhau
        right_frame.rowconfigure(1, weight=1)
        right_frame.rowconfigure(3, weight=1)
        right_frame.columnconfigure(0, weight=1)

    def start_server(self):
        from src.fastapi_server import start_fastapi, set_port
        set_port(self.port)
        self.fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
        self.fastapi_thread.start()

    def stop_server(self):
        from src.fastapi_server import stop_fastapi
        stop_fastapi()

    def on_resize(self, _):
        self.fixed_canvas_size = (self.center_frame.winfo_width() - 25, self.center_frame.winfo_height() - 110)
        self.canvas.config(width=self.fixed_canvas_size[0], height=self.fixed_canvas_size[1])

        if self.resize_after_id:
            self.after_cancel(self.resize_after_id)
        self.resize_after_id = self.after(50, self.perform_resize)

    def open_server_settings_click(self):
        is_connect_to_server_old_value = self.is_connect_to_server
        is_open_server_old_value = self.is_open_server

        settings_window = SettingsDialog(self, self.is_open_server, self.is_connect_to_server, self.port, self.base_url)
        self.wait_window(settings_window)

        self.port = settings_window.port
        self.is_connect_to_server = settings_window.is_connect_to_server
        self.is_open_server = settings_window.is_open_server
        self.base_url = settings_window.base_url

        self.auto_save_session()
        self.apply_server_settings(is_connect_to_server_old_value, is_open_server_old_value)

    def apply_server_settings(self, is_connect_to_server_old_value, is_open_server_old_value):
        if self.is_open_server != is_open_server_old_value:
            if self.is_open_server:
                if is_connect_to_server_old_value:
                    self.add_log("Disconnect from another server")
                self.add_log(f"Open server at port {self.port}")
                self.start_server()
            else:
                if is_open_server_old_value:
                    self.add_log("Close server")
                    self.stop_server()

        if self.is_connect_to_server != is_connect_to_server_old_value:
            if self.is_connect_to_server:
                try:
                    from src.call_to_server import test_connection
                    test_connection()
                except Exception as e:
                    self.add_log(f"Error when connect to server: {e}")
                    self.is_connect_to_server = False
                    return
                self.add_log(f"Connect to server at {self.base_url}")
                self.load_images_click()

                # disable button
                self.open_image_folder_button.config(state=tk.DISABLED)
                self.open_label_folder_button.config(state=tk.DISABLED)
                self.open_recycle_bin_folder_button.config(state=tk.DISABLED)
                self.auto_ocr_all_button.config(state=tk.DISABLED)
                self.check_error_button.config(state=tk.DISABLED)
            else:
                # enable button
                self.open_image_folder_button.config(state=tk.NORMAL)
                self.open_label_folder_button.config(state=tk.NORMAL)
                self.open_recycle_bin_folder_button.config(state=tk.NORMAL)
                self.auto_ocr_all_button.config(state=tk.NORMAL)
                self.check_error_button.config(state=tk.NORMAL)

    def perform_resize(self):
        self.cancel_update_saved_label = True
        self.display_image_click()

    def on_model_change(self, _):
        self.add_log("Loading OCR model")
        self.model_name = self.model_dropdown.get()
        self.ocr_model = load_ocr_model(self.model_name)
        self.add_log("OCR model loaded")

    def run_ocr(self, image: Image):
        if self.model_name == "VietOCR":
            return self.ocr_model.predict(image)
        elif self.model_name == "EasyOCR":
            return self.ocr_model.readtext(image)
        elif self.model_name == "Tesseract":
            return self.ocr_model(image)
        else:
            messagebox.showerror("Error", "Please select OCR model")
            raise ValueError("Please select OCR model")

    def cancel_change(self):
        self.text_entry.focus_set()
        self.text_entry.delete(0, tk.END)
        self.text_entry.insert(0, self.old_label_value)

    def add_log(self, message):
        self.log.append(message)
        while len(self.log) > 100:
            self.log.pop(0)
        self.status_label.delete(1.0, tk.END)
        for log in self.log[::-1]:
            self.status_label.insert(tk.END, "⇨" + log + "\n")
        self.update()

    def enter_pressed(self):
        if self.text_entry.get() == self.old_label_value:
            self.next_image_click()
        else:
            self.save_label_click()

    def bind_keys(self):
        self.bind('<F4>', lambda event: self.prev_image_click())
        self.bind('<Prior>', lambda event: self.prev_image_click())

        self.bind('<F5>', lambda event: self.next_image_click())
        self.bind('<Next>', lambda event: self.next_image_click())

        self.bind('<Control-S>', lambda event: self.save_label_click())
        self.bind('<Return>', lambda event: self.enter_pressed())

        self.bind('<F1>', lambda event: self.help_click())
        self.bind('<Escape>', lambda event: self.cancel_change())

    def open_image_folder_click(self):
        # Mở thư mục chứa ảnh
        folder_path = filedialog.askdirectory()
        if folder_path is None or len(folder_path) == 0:
            return

        self.add_log(f"Open image folder: {folder_path}")

        is_new_img_folder = True
        if folder_path == self.image_folder:
            is_new_img_folder = False

        self.image_folder = folder_path
        if self.label_folder is None:
            self.label_folder = folder_path
        if self.recycle_bin_folder is None:
            self.recycle_bin_folder = (folder_path + "/recycle_bin").replace("\\", "/").replace("//", "/")

        if is_new_img_folder:
            self.current_image_index = 0
            self.load_images_click()

    def open_label_folder_click(self):
        # Mở thư mục chứa nhãn
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.label_folder = folder_path
            self.add_log(f"Open label folder: {folder_path}")
            self.display_image_click()

    def open_recycle_bin_click(self):
        # Mở thư mục chứa nhãn
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.recycle_bin_folder = folder_path
            self.add_log(f"Open recycle bin folder: {folder_path}")

    def load_images_click(self):
        self.auto_save_session()
        if self.is_connect_to_server:
            self.add_log("Load images from server")
            try:
                from src.call_to_server import get_data
                response = get_data("load_images")
                self.image_list = response.json().get("images", [])
            except Exception as e:
                logging.exception(e)
                self.add_log(f"Error when load images from server: {e}")
                self.image_list = []

        else:
            # Load danh sách ảnh
            if self.image_folder:
                self.image_list = load_images()

        # Hiển thị lên listbox
        self.file_listbox.delete(0, tk.END)
        for i, image_filename in enumerate(self.image_list):
            self.file_listbox.insert(tk.END, f"{i + 1}) {image_filename}")

        if self.image_filename in self.image_list:
            self.current_image_index = self.image_list.index(self.image_filename)
        else:
            self.current_image_index = 0
        self.display_image_click()

    def check_error_click(self):
        image_list = load_images()
        self.image_list = []
        self.file_listbox.delete(0, tk.END)
        count = 0
        for i, image_filename in enumerate(image_list):
            self.add_log(f"Check error {i + 1}/{len(image_list)}, {count} images have error")
            old_label = self.load_label_file(image_filename)
            image_path = os.path.join(self.image_folder, image_filename)
            image = Image.open(image_path)
            new_label = self.run_ocr(image)
            if old_label != new_label:
                count += 1
                self.image_list.append(image_filename)
                self.file_listbox.insert(tk.END, f"{count}) {image_filename}")

        # Hiển thị lên listbox
        self.file_listbox.delete(0, tk.END)
        for i, image_filename in enumerate(self.image_list):
            self.file_listbox.insert(tk.END, f"{i + 1}) {image_filename}")
        self.current_image_index = 0
        self.display_image_click()

    def display_image_click(self):
        if not (self.image_list and 0 <= self.current_image_index < len(self.image_list)):
            self.title("OCR Labeling Tool")
            return

        self.image_filename = self.image_list[self.current_image_index]
        self.title(f"OCR Labeling Tool ({self.current_image_index + 1}/{len(self.image_list)}) - {self.image_filename}")
        self.add_log(f"Open: {self.image_filename}")

        if self.is_connect_to_server:
            self.add_log(f"Get image from server")
            try:
                from src.call_to_server import get_data
                response = get_data("get_image", params={"image_filename": self.image_filename})
                image_base64 = response.json().get("image", "")
                image = base64_to_image(image_base64)
            except Exception as e:
                logging.exception(e)
                self.add_log(f"Error when get image from server: {e}")
                return
        else:
            image = get_image(self.image_filename)

        self.image = copy.deepcopy(image)

        if not self.cancel_update_saved_label:
            self.old_label_value = self.load_label_file(self.image_filename)
            self.set_text_entry_value(self.old_label_value)
        self.cancel_update_saved_label = False

        # Handle zoom level
        zoom_value = self.zoom_level.get()
        if zoom_value == "Auto":
            zoom_percentage = 300
            image = image.resize(
                (int(image.width * zoom_percentage / 100), int(image.height * zoom_percentage / 100)),
                Image.Resampling.LANCZOS
            )
            if image.width > self.fixed_canvas_size[0] or image.height > self.fixed_canvas_size[1]:
                image.thumbnail(self.fixed_canvas_size, Image.Resampling.LANCZOS)
        else:
            zoom_percentage = int(zoom_value.replace("%", ""))
            image = image.resize(
                (int(image.width * zoom_percentage / 100), int(image.height * zoom_percentage / 100)),
                Image.Resampling.LANCZOS)

        # Display image on canvas
        self.canvas_image = ImageTk.PhotoImage(image)
        self.canvas.create_image(self.fixed_canvas_size[0] // 2, self.fixed_canvas_size[1] // 2,
                                 image=self.canvas_image, anchor='center')

    def next_image_click(self):
        self.text_entry.focus_set()
        if self.auto_save.get():
            self.save_label_click()

        if self.old_label_value != self.text_entry.get():
            if messagebox.askyesno("Save Label", "Do you want to save the current label?"):
                self.save_label_click()

        # Chuyển sang ảnh tiếp theo
        if self.current_image_index < len(self.image_list) - 1:
            self.current_image_index += 1
            self.add_log(f"Next image")
            self.display_image_click()

    def prev_image_click(self):
        self.text_entry.focus_set()
        if self.auto_save.get():
            self.save_label_click()

        if self.old_label_value != self.text_entry.get():
            if messagebox.askyesno("Save Label", "Do you want to save the current label?"):
                self.save_label_click()

        # Chuyển về ảnh trước đó
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.add_log(f"Previous image")
            self.display_image_click()

    def set_text_entry_value(self, text: str):
        self.text_entry.delete(0, tk.END)
        self.text_entry.insert(0, text)

    def save_label_click(self):
        self.text_entry.focus_set()
        self.save_label_file(self.image_filename, self.text_entry.get())
        self.old_label_value = self.text_entry.get()

    def delete_img_click(self):
        # if self.recycle_bin_folder is None or self.recycle_bin_folder == "" or self.image_folder is None or self.image_folder == "":
        #     messagebox.showerror("Error", "Recycle bin folder is not set")
        #     return
        if not messagebox.askyesno("Delete Image", "Do you want to delete this image?"):
            return

        if self.is_connect_to_server:
            self.add_log(f"Delete {self.image_filename}")
            from src.call_to_server import delete_data
            response = delete_data("delete_image", params={"image_filename": self.image_filename})
            if not response.status_code == 200:
                self.add_log(f"Error when delete image: {response.text}")
                return
        else:
            delete_image(self.image_filename)

        self.add_log(f"Delete {self.image_filename}")
        self.load_images_click()

    def auto_ocr_click(self):
        if self.image is None:
            return

        # Nhận diện chữ
        text = self.run_ocr(self.image)
        self.set_text_entry_value(text)

    @staticmethod
    def help_click():
        messagebox.showinfo("Help", "Open Image Folder: Open folder contains images\n"
                                    "Open Label Folder: Open folder contains labels\n"
                                    "Reload Files: Reload images in the folder\n\n"
                                    "Auto OCR: Auto OCR current image\n"
                                    "Auto OCR All File: Auto OCR all files in the folder\n\n"
                                    "Zoom: Change zoom level\n"
                                    "Auto save: Auto save label when move to next image\n\n"
                                    "F4 / Previous / Page up: Previous image\n"
                                    "F5 / Next / Page down: Next image\n"
                                    "Enter / Ctrl+S: Save label\n"
                                    "Esc: Cancel change")

    def auto_ocr_all_click(self):
        if not self.image_list:
            return

        self.add_log("Auto OCR all files...")
        count = 0
        for image_filename in self.image_list:
            count += 1
            self.add_log(f"Auto OCR {count}/{len(self.image_list)}")
            label = self.load_label_file(image_filename)
            if label is None or label == "":
                image_path = os.path.join(self.image_folder, image_filename)
                image = Image.open(image_path)
                text = self.run_ocr(image)
                self.save_label_file(image_filename, text)
        self.add_log("Auto OCR all files done")

    def save_label_file(self, image_filename: str, text: str):
        if self.is_connect_to_server:
            from src.call_to_server import post_data
            response = post_data("save_label", json={"image_filename": image_filename, "label": text})
            if response.status_code == 200:
                self.add_log(f"Save label for {image_filename}")
            else:
                self.add_log(f"Error when save label: {response.text}")
            return

        # if self.label_folder is None or self.label_folder == "" or self.image_folder is None or self.image_folder == "":
        #     messagebox.showerror("Error", "Image folder or Label folder is not set")
        #     return
        self.add_log(f"Save label for {image_filename}")
        save_label(image_filename, text)

    def load_label_file(self, image_filename):
        # TODO: Load nhãn
        if self.is_connect_to_server:
            self.add_log(f"Load label for {image_filename}")
            from src.call_to_server import get_data
            response = get_data("get_label", params={"image_filename": image_filename})
            return response.json().get("label", "")

        return get_label(image_filename)

    def on_image_select(self, event):
        # Lấy chỉ số của mục được chọn
        selected_index = event.widget.curselection()
        if selected_index:
            self.current_image_index = selected_index[0]
            self.display_image_click()
