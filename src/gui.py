import csv
import datetime
import os
from typing import Any
import image_tree
import tkinter as tk
import tkinter.font as tk_font

import cv2
from PIL import Image, ImageTk
import numpy as np
import image_managers, sample_extraction, percent, tube, segmentacion_contorno as sc
from sample_extraction import SampleExtractor
from utils import EntryWithPlaceholder

CLUSTER_RESHAPE = 0.7
IMAGE_RESHAPE = 0.7
    
class GUI(object):
    """
    The GUI class holds the behaviour of the graphic user interface
    of the geology cuantifier. It allows the user to interact with
    the diferent scripts developed for the processing and quanitification
    of rock samples.
    """
    def __init__(self, root: tk.Tk) -> None:
        """
        Constructor of the class. Instantiates class parameters related
        to both the workflow of the app and the elements of the interface.
        """

        # --- workflow parameters ---
        self.org_img = None
        self.img_tree = None
        self.selected_images_indices = []
        self.main_win = root

        # --- interface parameters ---
        
        # -- fonts -- 
        self.myFont = tk_font.Font(size=13)
        
        # -- frames --
        self.btns_fr = tk.Frame(self.main_win)
        self.btns_fr.grid(row=0, column=1, columnspan=3, padx=10, pady=10, sticky=tk.NW)

        self.img_container_fr = tk.Frame(self.main_win)
        
        self.img_container_canvas= tk.Canvas(self.img_container_fr)

        self.cropped_img_fr = tk.Frame(self.main_win)
        self.cropped_img_fr.grid(row=1, column=1)
        
        self.results_fr = tk.Frame(self.main_win)
        self.results_fr.grid(row=2,column=1, sticky=tk.S)

        # -- buttons --
        self.btn_img = tk.Button(self.btns_fr, text='Seleccionar imagen', width=20, command=self.show_img, cursor='arrow')
        self.btn_img['font'] = self.myFont
        self.btn_img.grid(row=0, column=0)

        self.btn_3d = tk.Button(self.btns_fr, text='3D', width=20, command=self.plot_3d, cursor='arrow')
        self.btn_3d['font'] = self.myFont

        self.btn_split = tk.Button(self.btns_fr, text='Separar', width=20, command=self.split, cursor='arrow')
        self.btn_split['font'] = self.myFont

        self.btn_merge = tk.Button(self.btns_fr, text='Combinar', width=20, command=self.merge, cursor='arrow')
        self.btn_merge['font'] = self.myFont
        
        self.btn_sub = tk.Button(self.btns_fr, text='Eliminar', width=20, command=self.delete, cursor='arrow')
        self.btn_sub['font'] = self.myFont
        
        self.btn_up = tk.Button(self.btns_fr, text='Subir', width=20, command=self.up, cursor='arrow')
        self.btn_up['font'] = self.myFont
        
        self.btn_down = tk.Button(self.btns_fr, text='Bajar', width=20, command=self.down, cursor='arrow')
        self.btn_down['font'] = self.myFont

        self.btn_undo = tk.Button(self.btns_fr, text='Deshacer', width=20, command=self.undo, cursor='arrow')
        self.btn_undo['font'] = self.myFont

        self.btn_contour = tk.Button(self.btns_fr, text='Segmentar', width=20, command=self.segmentate, cursor='arrow')
        self.btn_contour['font'] = self.myFont

        self.btn_save = tk.Button(self.btns_fr, text='Guardar', width=20, command=self.save, cursor='arrow')
        self.btn_save['font'] = self.myFont

        # -- entries --
        self.total_clusters = EntryWithPlaceholder(self.btns_fr, "Número de clusters", 'gray')
        self.total_clusters['font'] = self.myFont

        # -- extras --
        self.canvas_fr = tk.Frame(self.img_container_canvas)
        self.set_up_scrollbar()
    
    def set_up_scrollbar(self):
        
        self.scrollbar = tk.Scrollbar(self.img_container_fr, orient=tk.HORIZONTAL , command = self.img_container_canvas.xview)

        self.canvas_fr.bind(
            "<Configure>",
            lambda e: self.img_container_canvas.configure(
                scrollregion=self.img_container_canvas.bbox("all")
            )
        )

        self.img_container_canvas.create_window((0, 0), window=self.canvas_fr, anchor="nw")

        self.main_win.columnconfigure(2, weight=1)
        self.main_win.rowconfigure(1, weight=1)

        self.img_container_fr.columnconfigure(0, weight=1)
        self.img_container_fr.rowconfigure(0, weight=1)
        self.img_container_canvas.configure(xscrollcommand=self.scrollbar.set)

        self.img_container_canvas.grid()
        
        
        self.canvas_fr.bind('<Enter>', self._bound_to_mousewheel)
        self.canvas_fr.bind('<Leave>', self._unbound_to_mousewheel)

        self.img_container_canvas.configure(xscrollcommand= self.scrollbar.set)
        self.scrollbar.grid(row = 1, column=0, sticky=tk.N+tk.EW)
        self.img_container_canvas.grid(row=0, column=0, sticky=tk.N+tk.E+tk.W+tk.S)

    def _bound_to_mousewheel(self, event):
        self.img_container_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        self.img_container_canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.img_container_canvas.xview_scroll(int(-1*(event.delta/120)), "units")

    def split(self) -> None:
        """
        Splits the current image by doing KMeans clustering on it. The number of clusters
        is given by the user by filling the 'total_clusters' entry.
        """

        n_childs = int(self.total_clusters.get())
        selected_imgs = len(self.selected_images_indices)
        
        if selected_imgs > 1:
            tk.messagebox.showwarning("Error", message="Por favor selecciona solo una imagen.")
            return
        
        if selected_imgs == 1:
            self.img_tree = self.img_tree.childs[self.selected_images_indices[0]]
        
        self.img_tree.split(n_childs=n_childs)
        self.update_screen()
        self.selected_images_indices=[]
    
    def show_img(self) -> None:
        """
        This method is called when a new image is uploaded. 
        """
        self.main_win.withdraw()
        
        image = image_managers.load_image_from_window()
        self.org_img = SampleExtractor(image).extract_sample()
        self.img_tree = image_tree.ImageNode(None, self.org_img)
        self.update_screen()
                
        if self.org_img.size > 0:
            # Set buttons positions
            self.btn_3d.grid(row=0, column=1)
            self.total_clusters.grid(row=0, column=2)
            self.btn_split.grid(row=0, column=3)
            self.btn_merge.grid(row=0, column=4)
            self.btn_sub.grid(row=0, column=5)      
            self.btn_undo.grid(row=1,column=0)
            self.btn_save.grid(row=1, column=1)
            self.btn_up.grid(row=1, column=2)
            self.btn_down.grid(row=1, column=3)
            self.btn_contour.grid(row=1, column=4)
        
        self.main_win.deiconify()
        

    def clean_win(self) -> None:
        """
        Destroy every tkinter instance on screen and
        starts new ones.
        """
        for wget in self.canvas_fr.winfo_children():
            wget.destroy()

        for wget in self.results_fr.winfo_children():
            wget.destroy()
        
        for wget in self.cropped_img_fr.winfo_children():
            wget.destroy()
        
        self.cropped_img_fr.destroy()
        self.cropped_img_fr = tk.Frame(self.main_win)
        self.cropped_img_fr.grid(row=1, column=1)
        self.img_container_fr.grid(row=1, column=2, columnspan=2, sticky=tk.N+tk.E+tk.W+tk.S)
    
    def add_img_to_canvas(self, canvas: tk.Canvas, img: cv2.Mat) -> None:
        """
        Adds an image to the canvas.
        """
        photo_img = Image.fromarray(img)
        img_for_label = ImageTk.PhotoImage(photo_img)
        label_img = tk.Label(canvas, image=img_for_label)
        label_img.image = img_for_label
        label_img.grid(row=0, column=0, padx=10, pady=10)
        return label_img
        
    def click(self, image: cv2.Mat, key: Any, canvas: tk.Canvas) -> None:
        """
        Handles the clicks on screen, unselecting previous images if needed
        or selecting new ones.
        """
        if key in self.selected_images_indices:
            self.selected_images_indices.remove(key)
            canvas.configure(bg='white')
            for widget in canvas.winfo_children():
                if widget.cget("text"):
                    widget.destroy()
        else:
            self.selected_images_indices.append(key)
            canvas.configure(bg='red')

            widgetP = tk.Label(canvas, text=str(percent.percent(image)), fg='white', bg='black')
            widgetP.grid(row = 1,column=0 )

            widgetC = tk.Label(canvas, text=str(percent.contour(image)), fg='white', bg='black')
            widgetC.grid(row = 2,column=0 )

    def update_screen(self) -> None:
        """
        Updates the screen, this method is called right after
        the user interacts with the current image.
        """
        self.clean_win()

        img = self.img_tree.image # image at the current node of the image_tree
        self.selected_images_indices = [] # resets selected images

        # Set image for cropped image frame
        canva = tk.Canvas(self.cropped_img_fr, width=img.shape[1], height=img.shape[0])
        fix_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        _ = self.add_img_to_canvas(canva, fix_img)
        canva.grid(row=1, column=1)

        # draws image node childs
        img_row_shape = 2
        i = 0
        for child in self.img_tree.childs:
            child_img = cv2.resize(child.image, (int(child.image.shape[1]*CLUSTER_RESHAPE), int(child.image.shape[0]*CLUSTER_RESHAPE)))
            child_img = cv2.cvtColor(child_img, cv2.COLOR_BGR2RGB)
            canva = tk.Canvas(self.canvas_fr, width=child_img.shape[1], height=child_img.shape[0])
            label = self.add_img_to_canvas(canva, child_img)
            label.bind('<ButtonPress-1>', lambda event, image=child.image, key=i, canvas=canva: self.click(image, key, canvas))
            canva.grid(row=1+i%img_row_shape, column=i//img_row_shape)
            i+=1

    def merge(self) -> None:
        """
        This method merges 2 or more clusters, updating the image tree.
        """
        if len(self.selected_images_indices) < 2:
            tk.messagebox.showwarning("Error", message="Por favor seleccionar 2 o más de una imagenes.")
            return
        self.img_tree.merge(self.selected_images_indices)
        self.update_screen()
        self.selected_images_indices=[]

    def delete(self) -> None:
        """
        This method deletes at least 1 cluster, updating the image tree.
        """
        if len(self.selected_images_indices) == 0:
            tk.messagebox.showwarning("Error", message="Por favor seleccionar al menos una imagen.")
            return
        self.img_tree.delete(self.selected_images_indices)
        self.update_screen()
        self.selected_images_indices=[]

    def plot_3d(self) -> None:
        """
        This method plots the image of the current node of the image tree
        in a 3D model of a cilinder.
        """
        
        img = self.img_tree.image
        # If there isn't an image available
        while img.size > 0:
            # Load image using OS file window
            raw_img = image_managers.load_image_from_window()

            # Cut the img to analize an specific part of it.
            img = sample_extraction.extract_sample(raw_img)
        
        cv2.destroyAllWindows()

        # Use the loaded img to fill a 3D tube surface.
        tube.fill_tube(img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
    def undo(self) -> None:
        """
        Resets the image tree back to it's original form.
        """
        self.img_tree = image_tree.ImageNode(None,self.org_img)
        self.selected_images_indices = []
        self.update_screen()

    def down(self) -> None:
        """
        Travels one level downwards in the image tree, this means that the GUI
        will show a cluster as a main image and the user will be able to
        call functions on it.
        """
        if len(self.selected_images_indices) != 1:
            tk.messagebox.showwarning("Error", message="Por favor seleccionar una imagen.")
            return
        self.img_tree = self.img_tree.childs[self.selected_images_indices[0]]
        self.selected_images_indices = []
        self.update_screen()

    def up(self) -> None:
        """
        Travels one level upwards in the image tree, updates the GUI showing all the data
        related to the parent of the current node.
        """
        if self.img_tree.parent == None:
            tk.messagebox.showwarning("Error", message="Esta es la imagen original.")
            return
        self.img_tree = self.img_tree.parent
        self.selected_images_indices = []
        self.update_screen()

    
    def segmentate(self) -> None:
        """
        This method is in charge of the body detection at a cluster
        """
        if len(self.selected_images_indices) > 1:
            tk.messagebox.showwarning("Error", message="Por favor seleccionar solo una imagen.")
            return
        if len(self.selected_images_indices) == 1:
            self.img_tree = self.img_tree.childs[self.selected_images_indices[0]]

        self.update_screen()
        for wget in self.canvas_fr.winfo_children():
            wget.destroy()
        self.selected_images_indices = []
        

        contour = sc.contour_segmentation(self.img_tree.image) 
        sc.contour_agrupation(contour)
        segmentated = sc.cluster_segmentation(self.img_tree.image,contour)
        child_img = segmentated
        child_img = cv2.cvtColor(child_img, cv2.COLOR_BGR2RGB)
        canva = tk.Canvas(self.canvas_fr, width=child_img.shape[1], height=child_img.shape[0])
        self.add_img_to_canvas(canva, child_img)
        canva.grid(row=1,column=0)

        results = sc.generate_results(contour)
        self.fill_table(results)


    def fill_table(self, results) -> None:
        """
        This method fills and shows a table at the GUI.
        The data is given as an input.
        """
        label_color = tk.Label(self.results_fr, text="Color")
        label_color.grid(row=0, column=0)
        label_name = tk.Label(self.results_fr, text="Grupo")
        label_name.grid(row=0, column=1)
        label_total = tk.Label(self.results_fr, text="Porcentaje Total")
        label_total.grid(row=0, column=2)
        label_prom = tk.Label(self.results_fr, text="Porcentaje Promedio")
        label_prom.grid(row=0, column=3)
        
        for row_num in range(1, len(results[0])+1):
            (b, g, r) = sc.COLORS[row_num-1]
            color = '#%02x%02x%02x' % (r, g, b)
            label_color = tk.Label(self.results_fr, bg=color, width=1, height=1, justify=tk.CENTER)
            label_color.grid(row=row_num, column=0, sticky=tk.W)
            
            name = EntryWithPlaceholder(self.results_fr, f"Grupo {row_num}")
            name['font'] = self.myFont
            name.grid(row=row_num, column=1)

            label_total = tk.Label(self.results_fr, text=results[0][row_num-1])
            label_total.grid(row=row_num, column=2)

            label_prom = tk.Label(self.results_fr, text=results[1][row_num-1])
            label_prom.grid(row=row_num, column=3)

        self.btnExport = tk.Button(self.results_fr, text="Export to csv", width=15, command=self.table_to_csv, cursor='arrow')
        self.btnExport['font'] = self.myFont
        self.btnExport.grid(row=2, column=4)
    
    def table_to_csv(self) -> None:
        """
        This method takes the data from a table at the GUI
        and generates a csv with it.
        """
        wgets = self.results_fr.winfo_children()[:-1]
        def wgetter(wget_arr):
            ret_arr = []
            for wget in wget_arr:
                if isinstance(wget, tk.Entry):
                    ret_arr.append(wget.get())
                else:
                    if wget.cget('text') == '':
                        ret_arr.append(wget.cget('bg'))
                    else:
                        ret_arr.append(wget.cget('text'))
            return ret_arr
    
        rows = [wgetter(wgets[i:i+4]) for i in range(0, len(wgets), 4)]

        with open('geo_data.csv', 'w', newline='') as f:
            wrtr = csv.writer(f, delimiter=',')
            for row in rows:
                wrtr.writerow(row)
    
    def save(self) -> None:
        """
        This method saves both the current image and it's clusters if they exist.
        """
        PATH = f"output/{datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}"
        os.makedirs(PATH)
        image_managers.save_image_from_path(self.img_tree.image, f"{PATH}/original.png")
        for i in range(len(self.img_tree.childs)):
            image_managers.save_image_from_path(self.img_tree.childs[i].image, f"{PATH}/cluster_{i}.png")
        tk.messagebox.showinfo("Guardado", message="Las imagenes se han guardado correctamente")
    


    
root = tk.Tk()
root.title("Cuantificador geologico")
root.iconbitmap("icon.ico")
root.config(cursor='plus')
gg = GUI(root)        
root.mainloop()