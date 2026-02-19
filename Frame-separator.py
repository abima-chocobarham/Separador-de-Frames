import cv2
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import threading
import time
from tkinterdnd2 import TkinterDnD, DND_ALL

# Configuración global de tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ExtractorApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        
        # Inicializar TkinterDnD
        self.TkdndVersion = TkinterDnD._require(self)

        # Configuración de ventana
        self.title("Extractor Pro")
        self.geometry("600x700")
        self.resizable(False, False)
        
        # Estado
        self.ruta_video = None
        self.stop_event = threading.Event()
        self.procesando = False

        # Registrar Drop Target (todo la ventana)
        self.drop_target_register(DND_ALL)
        self.dnd_bind('<<Drop>>', self.drop_video)

        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Título
        self.lbl_titulo = ctk.CTkLabel(self.main_frame, text="Video a Frames", font=("Roboto Medium", 24))
        self.lbl_titulo.pack(pady=(20, 10))

        # Preview
        self.preview_frame = ctk.CTkFrame(self.main_frame, width=400, height=250, fg_color="gray20")
        self.preview_frame.pack(pady=10)
        self.preview_frame.pack_propagate(False)

        self.lbl_imagen = ctk.CTkLabel(self.preview_frame, text="Arrastra o selecciona un video", text_color="gray")
        self.lbl_imagen.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_info = ctk.CTkLabel(self.main_frame, text="", font=("Roboto", 12), text_color="gray70")
        self.lbl_info.pack(pady=10)

        # Controles de extracción
        self.frame_opciones = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frame_opciones.pack(pady=5)
        self.lbl_intervalo = ctk.CTkLabel(self.frame_opciones, text="Extraer cada (segundos):")
        self.lbl_intervalo.pack(side="left", padx=5)
        self.entry_intervalo = ctk.CTkEntry(self.frame_opciones, width=50)
        self.entry_intervalo.insert(0, "1")
        self.entry_intervalo.pack(side="left")

        # Barra de Progreso
        self.barra = ctk.CTkProgressBar(self.main_frame, width=400)
        self.barra.set(0)
        self.barra.pack(pady=(15, 5))
        
        self.lbl_estado = ctk.CTkLabel(self.main_frame, text="Listo", font=("Roboto", 10))
        self.lbl_estado.pack(pady=(0, 10))

        # Botones
        self.btn_cargar = ctk.CTkButton(self.main_frame, text="Seleccionar Video", 
                                      command=self.seleccionar_video, height=40, width=180)
        self.btn_cargar.pack(pady=5)

        self.btn_iniciar = ctk.CTkButton(self.main_frame, text="Iniciar Extracción", 
                                       command=self.iniciar_thread, state="disabled", 
                                       fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"),
                                       height=40, width=180)
        self.btn_iniciar.pack(pady=5)
        
        self.btn_cancelar = ctk.CTkButton(self.main_frame, text="Cancelar", 
                                        command=self.cancelar_proceso, state="disabled",
                                        fg_color="#C0392B", hover_color="#E74C3C",
                                        height=30, width=180)
        self.btn_cancelar.pack(pady=5)

    def seleccionar_video(self):
        ruta = filedialog.askopenfilename(filetypes=[("Videos", "*.mp4 *.avi *.mkv *.mov")])
        if not ruta: return
        self.cargar_video(ruta)

    def drop_video(self, event):
        ruta = event.data
        # Limpiar ruta si viene con llaves (común en TkinterDnD en Linux/Windows con espacios)
        if ruta.startswith('{') and ruta.endswith('}'):
            ruta = ruta[1:-1]
        self.cargar_video(ruta)

    def cargar_video(self, ruta):
        self.ruta_video = ruta
        
        video = cv2.VideoCapture(ruta)
        
        if not video.isOpened():
            messagebox.showerror("Error", "No se pudo abrir el archivo de video.\nAsegúrate de que es un formato válido.")
            return

        frames_totales = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = video.get(cv2.CAP_PROP_FPS)
        duration = frames_totales / fps if fps > 0 else 0
        
        # Evitar crash en videos cortos intentando leer frame 30
        frame_to_read = 30 if frames_totales > 30 else 0
        video.set(cv2.CAP_PROP_POS_FRAMES, frame_to_read)
        success, frame = video.read()
        video.release()

        if success:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(frame)
            
            # Mantener proporción (aspect ratio) para la miniatura
            ratio = img_pil.width / img_pil.height
            new_width = 400
            new_height = int(new_width / ratio)
            if new_height > 250:
                new_height = 250
                new_width = int(new_height * ratio)

            ctk_img = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(new_width, new_height))
            
            self.lbl_imagen.configure(image=ctk_img, text="")
            self.lbl_info.configure(text=f"{os.path.basename(ruta)}\n⏱ {duration:.1f} seg  |  🎞 {frames_totales} frames | FPS: {fps:.1f}")
            self.btn_iniciar.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])
        
    def iniciar_thread(self):
        try:
            intervalo = float(self.entry_intervalo.get())
            if intervalo <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "El intervalo debe ser un número mayor a 0.")
            return

        destino = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if not destino: return

        self.stop_event.clear()
        self.procesando = True
        self.update_ui_state(running=True)
        
        threading.Thread(target=self.procesar, args=(destino, intervalo), daemon=True).start()

    def cancelar_proceso(self):
        if self.procesando:
            self.stop_event.set()
            self.lbl_estado.configure(text="Cancelando...")

    def update_ui_state(self, running):
        state_input = "disabled" if running else "normal"
        state_cancel = "normal" if running else "disabled"
        
        self.btn_iniciar.configure(state=state_input)
        self.btn_cargar.configure(state=state_input)
        self.entry_intervalo.configure(state=state_input)
        self.btn_cancelar.configure(state=state_cancel)

    def procesar(self, carpeta_destino, intervalo_segundos):
        cap = None
        guardados = 0
        try:
            nombre_video = os.path.splitext(os.path.basename(self.ruta_video))[0]
            # Crear subcarpeta con el nombre del video dentro del destino seleccionado
            destino_final = os.path.join(carpeta_destino, nombre_video)
            os.makedirs(destino_final, exist_ok=True)

            cap = cv2.VideoCapture(self.ruta_video)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if fps <= 0:
                raise Exception("No se pudo determinar los FPS del video.")

            # Calcular cada cuántos frames capturar
            frames_step = int(fps * intervalo_segundos)
            if frames_step < 1: frames_step = 1

            current_frame = 0

            while cap.isOpened() and not self.stop_event.is_set():
                if current_frame >= total_frames:
                    break

                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                ret, frame = cap.read()
                
                if not ret:
                    break

                # Nombre del archivo con tiempo y número secuencial
                tiempo_seg = current_frame / fps
                nombre_archivo = f"frame_{guardados:04d}_{tiempo_seg:.2f}s.jpg"
                output_path = os.path.join(destino_final, nombre_archivo)
                
                cv2.imwrite(output_path, frame)
                
                guardados += 1
                current_frame += frames_step

                # Actualizar UI (Progreso)
                progreso = min(current_frame / total_frames, 1.0)
                self.after(0, lambda p=progreso, g=guardados: self.actualizar_progreso(p, g))

        except Exception as e:
            self.after(0, lambda err=str(e): messagebox.showerror("Error", err))
        
        finally:
            if cap: cap.release()
            self.after(0, lambda: self.finalizar_proceso(guardados))

    def actualizar_progreso(self, val, guardados):
        self.barra.set(val)
        self.lbl_estado.configure(text=f"Procesando... {guardados} imágenes guardadas")

    def finalizar_proceso(self, guardados):
        self.procesando = False
        self.update_ui_state(running=False)
        
        if self.stop_event.is_set():
            self.lbl_estado.configure(text=f"Cancelado. {guardados} imágenes guardadas.")
            messagebox.showinfo("Cancelado", f"Proceso cancelado por el usuario.\nSe guardaron {guardados} imágenes.")
        else:
            self.lbl_estado.configure(text="¡Completado!")
            self.barra.set(1)
            messagebox.showinfo("Éxito", f"Proceso finalizado exitosamente.\nSe guardaron {guardados} imágenes.")

if __name__ == "__main__":
    app = ExtractorApp()
    app.mainloop()