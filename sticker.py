import tkinter as tk
from tkinter import filedialog, Toplevel, Label, Button
from PIL import Image, ImageFilter, ImageDraw, ImageTk
import numpy as np
import math
import re
import os

ERROR_MESSAGE = 'GUI-based application'

def add_margin(filename):
    imr = Image.open(filename).convert('RGBA')
    imr_back = Image.new('RGBA', imr.size, (255, 255, 255))
    imc = Image.alpha_composite(imr_back, imr)
    im = imc.convert('RGB')
    ima = np.array(im)
    blur_px = max(round(min(im.size[0], im.size[1]) * 0.01), 1)
    imb = im.filter(ImageFilter.GaussianBlur(radius=2))
    imba = np.array(imb)
    ceil_tens = np.vectorize(lambda x: min(math.ceil(x / 10) * 10, 250))
    width = im.size[0]
    height = im.size[1]
    px = round(min(width, height) * 0.05)
    corners = np.zeros((4, px, px, 3))
    corners[0] = imba[:px, :px]
    corners[1] = imba[:px, -px:]
    corners[2] = imba[-px:, :px]
    corners[3] = imba[-px:, -px:]
    corner_list = np.reshape(corners, (px * px * 4, 3))
    rounded_corner_list = ceil_tens(corner_list)
    corner_dict = {}
    for item in rounded_corner_list:
        item_t = tuple(item)
        if item_t in corner_dict.keys():
            corner_dict[item_t] += 1
        else:
            corner_dict[item_t] = 1
    corner_dict_sorted = dict(sorted(corner_dict.items(), key=lambda x: -x[1]))
    color_list = list(corner_dict_sorted.keys())
    bg = color_list[0]
    mg = round(max(width, height) * 0.1)
    exp_img = np.full((height + (2 * mg), width + (2 * mg), 3), bg, np.float32)
    exp_img[mg:(height + mg), mg:(width + mg)] = ima
    ei = Image.fromarray(exp_img.astype(np.uint8))
    
    # Just save the expanded image in the same directory as the original
    fn_no_pre = re.sub('^.*\/', '', filename)
    path = f'exp-{fn_no_pre}'
    ei.save(path)
    return path

def process_img(filename, add_border, crop, threshold=150):
    im = Image.open(filename).convert('RGB')
    ImageDraw.floodfill(im, xy=(10, 10), value=(255, 0, 255), thresh=threshold)
    am = np.array(im)
    am[(am[:, :, 0:3] != [255, 0, 255]).any(2)] = [0, 255, 0]
    mask = Image.fromarray(am)
    if add_border:
        maa = [255, 0, 255]
        def is_border(r, c):
            return (am[r, c] != maa).any() and (
                (am[r-1, c] == maa).all() or
                (am[r, c+1] == maa).all() or
                (am[r+1, c] == maa).all() or
                (am[r, c-1] == maa).all()
            )
        draw = ImageDraw.Draw(mask)
        RAD = 8
        for r in range(1, am.shape[0] - 1):
            for c in range(1, am.shape[1] - 1):
                if is_border(r, c):
                    draw.ellipse((c - RAD, r - RAD, c + RAD, r + RAD), (0, 255, 0), None)
        ma = np.array(mask)
        ma = ma + am
        def fix(x):
            return 255 if x > 0 else 0
        fixv = np.vectorize(fix)
        bma = fixv(ma)
        mask = Image.fromarray(bma.astype(np.uint8))
    im.putalpha(255)
    imm = np.array(im)
    bma = np.array(mask)
    imm[(bma[:, :, 0:3] == [255, 255, 255]).all(2)] = [255, 255, 255, 255]
    imm[(bma[:, :, 0:3] == [255, 0, 255]).all(2)] = [0, 0, 0, 0]
    fim = Image.fromarray(imm)
    if crop:
        maa = [255, 0, 255]
        maxh, maxw, minh, minw = 0, 0, am.shape[0], am.shape[1]
        for r in range(1, am.shape[0] - 1):
            for c in range(1, am.shape[1] - 1):
                if (bma[r, c] != maa).any():
                    if maxh < r:
                        maxh = r
                    if minh > r:
                        minh = r
                    if maxw < c:
                        maxw = c
                    if minw > c:
                        minw = c
        mg = round(max(maxw - minw, maxh - minh) * 0.05)
        minw = max(0, minw - mg)
        minh = max(0, minh - mg)
        maxw = min(am.shape[1], maxw + mg)
        maxh = min(am.shape[0], maxh + mg)
        fim = fim.crop((minw, minh, maxw, maxh))
    return fim

def createDir(name):
    try:
        os.mkdir(name)
    except:
        pass

def full_process(filename):
    margin_filename = add_margin(filename)
    return process_img(margin_filename, add_border=True, crop=True)

def save_final_image(image, counter=1):
    createDir('results')
    save_path = f'results/trimmped_pic_{counter}.png'
    image.save(save_path)

class ImageCutterGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Cutter")
        self.master.configure(bg="#F0F0F0")
        self.filename = None
        self.original_image = None
        self.processed_image = None

        self.upload_button = tk.Button(
            self.master,
            text="Upload Image",
            command=self.upload_image,
            bg="#1E90FF",
            fg="#FFFFFF",
            font=("Arial", 12, "bold"),
            padx=10, pady=5
        )
        self.upload_button.pack(pady=10)

        self.preview_label = tk.Label(
            self.master,
            text="No image uploaded",
            bg="#F0F0F0",
            font=("Arial", 10)
        )
        self.preview_label.pack()

        self.process_button = tk.Button(
            self.master,
            text="Process Image",
            command=self.process_image,
            bg="#32CD32",
            fg="#FFFFFF",
            font=("Arial", 12, "bold"),
            padx=10, pady=5
        )
        self.process_button.pack(pady=10)

    def upload_image(self):
        self.filename = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if self.filename:
            self.original_image = Image.open(self.filename)
            tk_image = self.get_tk_image(self.original_image, maxsize=(400, 400))
            self.preview_label.configure(image=tk_image, text="")
            self.preview_label.image = tk_image

    def process_image(self):
        if not self.filename:
            return
        self.processed_image = full_process(self.filename)
        self.show_result_popup()

    def show_result_popup(self):
        if not self.processed_image:
            return
        popup = Toplevel(self.master)
        popup.title("Processed Image")
        popup.configure(bg="#F0F0F0")

        tk_proc_img = self.get_tk_image(self.processed_image, maxsize=(400, 400))
        result_label = Label(popup, image=tk_proc_img, bg="#F0F0F0")
        result_label.image = tk_proc_img
        result_label.pack(pady=10)

        save_button = Button(
            popup,
            text="Save Image",
            command=lambda: self.save_processed_and_close(popup),
            bg="#FF4500",
            fg="#FFFFFF",
            font=("Arial", 12, "bold"),
            padx=10, pady=5
        )
        save_button.pack(pady=10)

    def save_processed_and_close(self, popup):
        save_final_image(self.processed_image, counter=1)
        popup.destroy()

    def get_tk_image(self, pil_img, maxsize=(400, 400)):
        pil_img.thumbnail(maxsize, Image.LANCZOS)
        return ImageTk.PhotoImage(pil_img)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCutterGUI(root)
    root.mainloop()
