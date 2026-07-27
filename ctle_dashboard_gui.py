# -*- coding: utf-8 -*-
import os
import itertools
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import math

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ---------------------------------------------
# 產生 CTLE 檔案核心邏輯
# ---------------------------------------------
def generate_ctle_core(f1, f2, fz, gain_db, f_max, num_points, output_filename=None):
    gain_lin = 10 ** (gain_db / 20.0)
    w1 = 2 * math.pi * f1
    w2 = 2 * math.pi * f2
    wz = 2 * math.pi * fz
    
    freqs = np.linspace(0, f_max, num_points)
    factor = (w1 * w2) / wz
    
    # 用 numpy 計算全頻段響應
    s = 1j * 2 * np.pi * freqs
    h_array = gain_lin * factor * (s + wz) / ((s + w1) * (s + w2))
    
    if output_filename:
        # File generation
        with open(output_filename, 'w') as f:
            f.write(f"! pole1={f1:g}, pole2={f2:g}, zero={fz:g}\n")
            f.write(f"! Gain={gain_db}dB for transfer function\n")
            f.write("! Transfer function has the format\n")
            f.write("! H(s)=2*pi*f1*2*pi*f2/(2*pi*fz)*Gain*(s+2*pi*fz)/((s+2*pi*f1)*(s+2*pi*f2))\n")
            f.write(f"[Number of frequencies] {num_points}\n")
            f.write("[Number of transfer functions] 1\n")
            f.write("[Complex format] RI\n")
            f.write("[Data]\n\n")
            
            for i, freq in enumerate(freqs):
                h = h_array[i]
                if freq == 0:
                    h = complex(gain_lin, 0)
                f.write(f"{freq:g},{h.real:.10g},{h.imag:.10g}\n")
                
    return freqs, h_array

# ---------------------------------------------
# 解析 Start, Stop, Step 陣列
# ---------------------------------------------
def parse_sweep_range(start_str, stop_str, step_str):
    start = float(start_str)
    stop = float(stop_str)
    step = float(step_str)
    
    if start == stop:
        return [start]
    
    if step == 0:
        return [start]
        
    num = int(round((stop - start) / step)) + 1
    # 防護帶：若區間不合理 (如 start < stop 但 step < 0)
    if num <= 0:
        return [start]
        
    return list(np.linspace(start, stop, num))

class CTLEDashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CTLE 批次掃描儀與 AEDT 發射中心 - 此工具由 虎門科技資深技術工程師 Jeff Hong 洪敬傑提供")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        
        style = ttk.Style()
        style.configure("Header.TLabel", font=("Microsoft JhengHei UI", 12, "bold"), foreground="#005A9C")
        style.configure("Sub.TLabel", font=("Microsoft JhengHei UI", 9, "bold"))
        
        # Main Layout
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.left_frame = ttk.Frame(self.paned_window, width=500)
        self.right_frame = ttk.Frame(self.paned_window)
        
        self.paned_window.add(self.left_frame, weight=1)
        self.paned_window.add(self.right_frame, weight=2)
        
        # --- LEFT FRAME (Inputs) ---
        header = ttk.Label(self.left_frame, text="掃描區間設定 (Start, Stop, Step)", style="Header.TLabel")
        header.pack(pady=(10,5))
        
        input_frame = ttk.Frame(self.left_frame)
        input_frame.pack(padx=10, fill="x")
        
        # Header Row
        ttk.Label(input_frame, text="Parameter", style="Sub.TLabel").grid(row=0, column=0, pady=5, sticky="w")
        ttk.Label(input_frame, text="Start", style="Sub.TLabel").grid(row=0, column=1, pady=5, padx=5)
        ttk.Label(input_frame, text="Stop", style="Sub.TLabel").grid(row=0, column=2, pady=5, padx=5)
        ttk.Label(input_frame, text="Step", style="Sub.TLabel").grid(row=0, column=3, pady=5, padx=5)
        
        # Default Params
        self.params = {
            "DC Gain (dB)": ("-3.0", "-4.0", "-0.5"),
            "Zero Freq (Hz)": ("0.6e9", "0.7e9", "0.05e9"),
            "Pole 1 Freq (Hz)": ("1.95e9", "1.95e9", "0e9"),
            "Pole 2 Freq (Hz)": ("5.0e9", "5.0e9", "0e9")
        }
        
        self.vars = {}
        for r, (name, defaults) in enumerate(self.params.items(), start=1):
            ttk.Label(input_frame, text=name).grid(row=r, column=0, sticky="w", pady=5)
            
            v_start = tk.StringVar(value=defaults[0])
            v_stop = tk.StringVar(value=defaults[1])
            v_step = tk.StringVar(value=defaults[2])
            
            # Trace to auto update
            v_start.trace_add("write", self.on_input_change)
            v_stop.trace_add("write", self.on_input_change)
            v_step.trace_add("write", self.on_input_change)
            
            self.vars[name] = {"start": v_start, "stop": v_stop, "step": v_step}
            
            ent_start = ttk.Entry(input_frame, textvariable=v_start, width=9)
            ent_stop = ttk.Entry(input_frame, textvariable=v_stop, width=9)
            ent_step = ttk.Entry(input_frame, textvariable=v_step, width=9)
            
            ent_start.grid(row=r, column=1, padx=5)
            ent_stop.grid(row=r, column=2, padx=5)
            ent_step.grid(row=r, column=3, padx=5)
            
        # Fixed Variables 
        ttk.Separator(self.left_frame, orient="horizontal").pack(fill="x", pady=15)
        fix_frame = ttk.Frame(self.left_frame)
        fix_frame.pack(padx=10, fill="x")
        
        ttk.Label(fix_frame, text="Max Freq (Hz):").grid(row=0, column=0, sticky="w", pady=5)
        self.v_max_freq = tk.StringVar(value="6e9")
        self.v_max_freq.trace_add("write", self.on_input_change)
        ttk.Entry(fix_frame, textvariable=self.v_max_freq, width=15).grid(row=0, column=1, sticky="w", padx=10)
        
        ttk.Label(fix_frame, text="Num Points:").grid(row=1, column=0, sticky="w", pady=5)
        self.v_num_pts = tk.StringVar(value="1000")
        self.v_num_pts.trace_add("write", self.on_input_change)
        ttk.Entry(fix_frame, textvariable=self.v_num_pts, width=15).grid(row=1, column=1, sticky="w", padx=10)
        
        # Info Panel
        ttk.Separator(self.left_frame, orient="horizontal").pack(fill="x", pady=15)
        self.lbl_count = ttk.Label(self.left_frame, text="預估產出數量：計算中...", style="Header.TLabel")
        self.lbl_count.pack(pady=10)
        
        btn_gen = ttk.Button(self.left_frame, text="產生全批次 CTLE 模型", command=self.on_generate)
        btn_gen.pack(pady=15, ipadx=10, ipady=10, fill="x", padx=20)
        
        # Footer label
        lbl_footer = ttk.Label(self.left_frame, text="此工具由 虎門科技資深技術工程師 Jeff Hong 洪敬傑提供", font=("Microsoft JhengHei UI", 9), foreground="gray")
        lbl_footer.pack(side=tk.BOTTOM, pady=(0, 10))
        
        # --- RIGHT FRAME (Plot) ---
        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # State
        self.valid_combinations = []
        
        # Init
        self.update_plot()

    def on_input_change(self, *args):
        if hasattr(self, '_after_id') and self._after_id:
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(400, self.update_plot)
        
    def _parse_lists(self):
        try:
            g_list = parse_sweep_range(self.vars["DC Gain (dB)"]["start"].get(), 
                                       self.vars["DC Gain (dB)"]["stop"].get(), 
                                       self.vars["DC Gain (dB)"]["step"].get())
            
            z_list = parse_sweep_range(self.vars["Zero Freq (Hz)"]["start"].get(), 
                                       self.vars["Zero Freq (Hz)"]["stop"].get(), 
                                       self.vars["Zero Freq (Hz)"]["step"].get())
            
            p1_list = parse_sweep_range(self.vars["Pole 1 Freq (Hz)"]["start"].get(), 
                                        self.vars["Pole 1 Freq (Hz)"]["stop"].get(), 
                                        self.vars["Pole 1 Freq (Hz)"]["step"].get())
            
            p2_list = parse_sweep_range(self.vars["Pole 2 Freq (Hz)"]["start"].get(), 
                                        self.vars["Pole 2 Freq (Hz)"]["stop"].get(), 
                                        self.vars["Pole 2 Freq (Hz)"]["step"].get())
                                        
            return list(itertools.product(g_list, z_list, p1_list, p2_list))
        except Exception:
            return []

    def update_plot(self):
        self.ax.clear()
        self.ax.set_title("CTLE Gain Responses (Batch Preview)", fontsize=12, fontweight='bold', color='#333333')
        self.ax.set_xlabel("Frequency (Hz)", fontsize=10)
        self.ax.set_ylabel("Gain (dB)", fontsize=10)
        self.ax.grid(True, which="both", ls="--", alpha=0.5)
        
        combos = self._parse_lists()
        self.valid_combinations = combos
        
        if not combos:
            self.lbl_count.config(text="預估產出數量：0 (格式錯誤)", foreground="red")
            self.canvas.draw()
            return
            
        self.lbl_count.config(text=f"預估產出數量：{len(combos)} 個模型", foreground="green")
        
        try:
            f_max = float(self.v_max_freq.get())
            n_pts = int(self.v_num_pts.get())
            
            # Use logspace for plot
            freq_log = np.logspace(6, np.log10(f_max) if f_max > 0 else 10, num=100)
            s_log = 1j * 2 * np.pi * freq_log
            
            # 若組合超過 50 條，為了 UI 順暢，只隨機挑選 50 條顯示，並用 alpha 疊加
            display_combos = combos
            if len(combos) > 100:
                indices = np.linspace(0, len(combos)-1, 100, dtype=int)
                display_combos = [combos[i] for i in indices]
                self.ax.set_title(f"CTLE Gain Responses (Previewing 100/{len(combos)})", fontsize=12, fontweight='bold', color='#333333')
            
            for (gain_db, fz, f1, f2) in display_combos:
                gain_lin = 10 ** (gain_db / 20.0)
                factor = ((2*math.pi*f1) * (2*math.pi*f2)) / (2*math.pi*fz)
                
                h_log = gain_lin * factor * (s_log + 2*math.pi*fz) / ((s_log + 2*math.pi*f1) * (s_log + 2*math.pi*f2))
                h_mag_db = 20 * np.log10(np.abs(h_log))
                
                self.ax.semilogx(freq_log, h_mag_db, linewidth=1.0, alpha=0.6)
                
            self.canvas.draw()
        except Exception:
            pass

    def on_generate(self):
        combos = self.valid_combinations
        if not combos:
            messagebox.showerror("錯誤", "無法計算組合，請檢查參數格式是否合法。")
            return
            
        try:
            f_max = float(self.v_max_freq.get())
            n_pts = int(self.v_num_pts.get())
            
            output_dir = filedialog.askdirectory(title="選擇輸出資料夾", initialdir=os.getcwd())
            if not output_dir:
                return
                
            # 建立一個獨立子資料夾以策安全
            sweep_dir = os.path.join(output_dir, "CTLE_Generated_Models")
            if not os.path.exists(sweep_dir):
                os.makedirs(sweep_dir)
                
            mapping_csv = os.path.join(sweep_dir, "Mapping.csv")
            
            with open(mapping_csv, "w") as fm:
                fm.write("File_Index,FileName,Gain_dB,Zero_Hz,Pole1_Hz,Pole2_Hz\n")
                
                for idx, (gain_db, fz, f1, f2) in enumerate(combos, start=1):
                    filename = f"ctle_{idx}.ctle"
                    filepath = os.path.join(sweep_dir, filename)
                    
                    generate_ctle_core(f1, f2, fz, gain_db, f_max, n_pts, filepath)
                    fm.write(f"{idx},{filename},{gain_db},{fz:g},{f1:g},{f2:g}\n")
                    
            msg = (f"成功產出 {len(combos)} 個 CTLE 模型檔案！\n\n"
                   f"儲存位置：\n{sweep_dir}\n\n"
                   f"下一步：\n"
                   f"您可以開啟 AEDT，執行 direct_aedt_ctle_macro.py，\n"
                   f"並直接選取這個資料夾裡的所有檔案進行一鍵模擬！")
            messagebox.showinfo("生成完畢", msg)
            
        except Exception as e:
            messagebox.showerror("生成錯誤", f"發生未預期錯誤:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CTLEDashboardApp(root)
    root.mainloop()
