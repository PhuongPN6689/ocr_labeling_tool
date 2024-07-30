import copy
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os


def load_ocr_model(model_name):
    if model_name == "VietOCR":
        from vietocr.tool.config import Cfg
        from vietocr.tool.predictor import Predictor
        config = Cfg.load_config_from_name('vgg_seq2seq')
        config['device'] = 'cpu'  # Use CPU for this example
        return Predictor(config)

    elif model_name == "EasyOCR":
        import easyocr
        return easyocr.Reader(['en', 'vi'], gpu=False)

    elif model_name == "Tesseract":
        from pytesseract import image_to_string
        return image_to_string

    else:
        return None


class OCRLabelingTool(tk.Tk):
    def __init__(self):
        super().__init__()

        # Thiết lập cửa sổ chính
        self.title("OCR Labeling Tool")
        self.geometry("1100x600")

        # Biến để lưu trữ các thông tin cần thiết
        self.image = None
        self.image_filename = None
        self.image_folder = None
        self.old_label_value = ''
        self.label_folder = None
        self.image_list = []
        self.current_image_index = 0
        self.auto_save = tk.BooleanVar()
        self.zoom_level = tk.StringVar(value="Auto")
        self.fixed_canvas_size = (600, 500)  # Kích thước cố định cho khu vực hiển thị ảnh
        self.model_name = None
        self.ocr_model = None
        self.log = []

        # Gọi các phương thức để tạo các thành phần giao diện
        self.create_widgets()
        self.bind_keys()

    def create_widgets(self):
        # Cột 1: Khu vực bên trái
        left_frame = tk.Frame(self)
        left_frame.pack(side="left", fill="y", padx=10, pady=5)

        open_image_folder_button = tk.Button(left_frame, text="Open Image Folder", compound=tk.TOP, command=self.open_image_folder_click)
        open_image_folder_button.pack(pady=5, fill="x")

        open_label_folder_button = tk.Button(left_frame, text="Open Label Folder", compound=tk.TOP, command=self.open_label_folder_click)
        open_label_folder_button.pack(pady=5, fill="x")

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

        auto_ocr_all_button = tk.Button(left_frame, text="Auto OCR All File", command=self.auto_ocr_all_click)
        auto_ocr_all_button.pack(pady=10, fill="x")

        tk.Frame(left_frame).pack(fill="x", pady=15)

        help_button = tk.Button(left_frame, text="Help", command=self.help_click)
        help_button.pack(pady=5, fill="x")

        tk.Frame(left_frame).pack(fill="x", pady=15)

        tk.Label(left_frame, text="Log").pack(padx=5)
        self.status_label = tk.Text(left_frame, height=15, width=25)
        self.status_label.pack(fill="both", padx=5, pady=5)

        # Cột 2: Khu vực trung tâm
        center_frame = tk.Frame(self)
        center_frame.pack(side="left", expand=True, fill="both", padx=10, pady=5)

        # Tùy chọn zoom
        zoom_frame = tk.Frame(center_frame)
        zoom_frame.pack(pady=5, fill="x")

        tk.Label(zoom_frame, text="Zoom:").pack(side="left", padx=5)

        for zoom in ["Auto", "50%", "100%", "150%", "200%", "300%"]:
            radio = tk.Radiobutton(zoom_frame, text=zoom, variable=self.zoom_level, value=zoom,
                                   command=self.display_image_click)
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

        tk.Frame(button_frame).pack(side="left", fill="x")

        save_button = tk.Button(button_frame, text="Save", command=self.save_label_click)
        save_button.pack(side="right", padx=5, pady=5)

        self.text_entry = tk.Entry(button_frame, font=("Consolas", 14))
        self.text_entry.pack(side="right", padx=5, pady=5)

        auto_ocr_button = tk.Button(button_frame, text="Auto OCR", command=self.auto_ocr_click)
        auto_ocr_button.pack(side="right", padx=5, pady=5)

        # Khu vực hiển thị ảnh với kích thước cố định
        self.canvas = tk.Canvas(center_frame, width=self.fixed_canvas_size[0], height=self.fixed_canvas_size[1])
        self.canvas.pack()

        # Cột 3: Khu vực bên phải
        right_frame = tk.Frame(self, width=400)
        right_frame.pack(side="right", fill="y", padx=5, pady=5)

        label_right_frame = tk.Frame(right_frame)
        label_right_frame.pack(fill="x")

        tk.Label(label_right_frame, text="List image").pack(side="left", padx=5)
        tk.Frame(label_right_frame).pack(side="right", fill="x")

        copy_filename_button = tk.Button(label_right_frame, text="Copy filename", command=self.copy_filename_click)
        copy_filename_button.pack(side="right", padx=5, pady=5)

        # Tạo khung chứa Listbox và thanh cuộn
        listbox_frame = tk.Frame(right_frame)
        listbox_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Tạo Listbox
        self.file_listbox = tk.Listbox(listbox_frame, height=20)  # Điều chỉnh chiều cao theo ý muốn
        self.file_listbox.pack(side="left", fill="both", expand=True)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_image_select)

        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.file_listbox.yview)

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
            return self.text_entry.get()

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

    def bind_keys(self):
        self.bind('<F4>', lambda event: self.prev_image_click())
        self.bind('<Prior>', lambda event: self.prev_image_click())

        self.bind('<F5>', lambda event: self.next_image_click())
        self.bind('<Next>', lambda event: self.next_image_click())

        self.bind('<Control-S>', lambda event: self.save_label_click())
        self.bind('<Return>', lambda event: self.save_label_click())

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

        if is_new_img_folder:
            self.current_image_index = 0
            self.load_images_click()
            self.display_image_click()

    def open_label_folder_click(self):
        # Mở thư mục chứa nhãn
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.label_folder = folder_path
            self.add_log(f"Open label folder: {folder_path}")

    def load_images_click(self):
        # Load danh sách ảnh
        if self.image_folder:
            self.image_list = [f for f in os.listdir(self.image_folder) if f.lower().endswith(('png', 'jpg', 'jpeg'))]
            # Hiển thị lên listbox
            self.file_listbox.delete(0, tk.END)
            for image_filename in self.image_list:
                self.file_listbox.insert(tk.END, image_filename)

    def display_image_click(self):
        # Hiển thị ảnh hiện tại với kích thước và zoom phù hợp
        if self.image_list and 0 <= self.current_image_index < len(self.image_list):
            self.image_filename = self.image_list[self.current_image_index]
            self.title(f"OCR Labeling Tool ({self.current_image_index + 1}/{len(self.image_list)}) - {self.image_filename}")
            self.add_log(f"Display image: {self.image_filename}")
            image_path = os.path.join(self.image_folder, self.image_filename)
            image = Image.open(image_path)
            self.image = copy.deepcopy(image)

            self.old_label_value = self.load_label_file(self.image_filename)
            self.set_text_entry_value(self.old_label_value)

            # Xử lý chế độ zoom
            zoom_value = self.zoom_level.get()
            if zoom_value == "Auto":
                image.thumbnail(self.fixed_canvas_size, Image.Resampling.LANCZOS)
            else:
                zoom_percentage = int(zoom_value.replace("%", ""))
                image = image.resize(
                    (int(image.width * zoom_percentage / 100), int(image.height * zoom_percentage / 100)),
                    Image.Resampling.LANCZOS)

            # Hiển thị ảnh lên canvas
            self.canvas_image = ImageTk.PhotoImage(image)
            self.canvas.create_image(self.fixed_canvas_size[0] // 2, self.fixed_canvas_size[1] // 2,
                                     image=self.canvas_image, anchor='center')

        else:
            self.title("OCR Labeling Tool")

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

    def auto_ocr_click(self):
        if self.image is None:
            return

        # Nhận diện chữ
        text = self.run_ocr(self.image)
        self.set_text_entry_value(text)

    def copy_filename_click(self):
        if self.image_filename:
            self.clipboard_clear()
            self.clipboard_append(self.image_filename)
            self.update()

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
        if self.label_folder is None and self.image_folder is None:
            return
        self.add_log(f"Save label for {image_filename}")
        json_path = os.path.join(self.label_folder, image_filename.rsplit(".", maxsplit=1)[0] + ".json")
        content = {
            "image_path": image_filename,
            "label": text
        }
        with open(json_path, 'w') as f:
            f.write(json.dumps(content))

    def load_label_file(self, image_filename):
        json_path = os.path.join(self.label_folder, image_filename.rsplit(".", maxsplit=1)[0] + ".json")
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                content = json.load(f)
            return content["label"]
        return ""

    def on_image_select(self, event):
        # Lấy chỉ số của mục được chọn
        selected_index = event.widget.curselection()
        if selected_index:
            self.current_image_index = selected_index[0]
            self.display_image_click()


if __name__ == "__main__":
    app = OCRLabelingTool()
    app.mainloop()
