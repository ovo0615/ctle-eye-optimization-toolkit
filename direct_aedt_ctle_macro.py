# -*- coding: utf-8 -*-
# ----------------------------------------------
# Direct AEDT IronPython Macro for CTLE Batch Sweep
# Please execute this directly in AEDT via Automation > Run Script...
# ----------------------------------------------
import os
import clr
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import OpenFileDialog, DialogResult, MessageBox

import ScriptEnv

# 1. 取得當前有效的 AEDT 專案與設計
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.RestoreWindow()
oProject = oDesktop.GetActiveProject()
if not oProject:
    MessageBox.Show("請先開啟包含 EyeProbe 的 AEDT Circuit 專案。", "錯誤")
    import sys
    sys.exit()

oDesign = oProject.GetActiveDesign()
if not oDesign:
    MessageBox.Show("請先開啟包含 EyeProbe 的 Design。", "錯誤")
    import sys
    sys.exit()

oEditor = oDesign.SetActiveEditor("SchematicEditor")
oModule = oDesign.GetModule("ReportSetup")

# 2. 呼叫 Windows 原生選檔視窗
ofd = OpenFileDialog()
ofd.Title = "請選取所有要進行自動化模擬的 CTLE 檔案"
ofd.Filter = "CTLE files (*.ctle)|*.ctle|All files (*.*)|*.*"
ofd.Multiselect = True

result = ofd.ShowDialog()
if result != DialogResult.OK:
    import sys
    sys.exit() # 使用者取消

ctle_files = list(ofd.FileNames)

if not ctle_files:
    MessageBox.Show("未選取任何檔案。", "警告")
    import sys
    sys.exit()

# 3. 設定輸出檔案路徑
output_dir = os.path.dirname(ctle_files[0])
summary_csv = os.path.join(output_dir, "Eye_Summary_Results.csv")
temp_csv = os.path.join(output_dir, "temp_eye_data.csv")

# 寫入總表 Header
with open(summary_csv, "w") as f:
    f.write("CTLE_File,EyeHeight,EyeWidth\n")

plots_exist = False
results_data = []

# 4. 開始自動化迴圈
for ctle_path in ctle_files:
    safe_path = ctle_path.replace("\\", "/") # 處理路徑跳脫字元
    filename = os.path.basename(safe_path)
    
    # 變更 EyeProbe 內的 ctle 檔案參數
    oEditor.ChangeProperty(
        [
            "NAME:AllTabs",
            [
                "NAME:PassedParameterTab",
                [
                    "NAME:PropServers", 
                    "CompInst@EYEPROBE;4;20"
                ],
                [
                    "NAME:ChangedProps",
                    [
                        "NAME:CTLE_data",
                        "ButtonText:="      , 'ctle_file="{0}" ctle_reltol=1e-2 tf_num=0'.format(safe_path),
                        "AdditionalText:="  , ""
                    ]
                ]
            ]
        ]
    )
    
    # 執行模擬
    oDesign.Analyze("NexximTransient")
    
    # 若是第一次執行，建立眼圖及隱藏的數據表
    if not plots_exist:
        try:
            oModule.DeleteReports(["Transient Voltage Plot1", "EyeData"])
        except:
            pass
            
        oModule.CreateReport("Transient Voltage Plot1", "Eye Diagram", "Rectangular Plot", "NexximTransient", 
            [
                "NAME:Context",
                "SimValueContext:=", [1,0,2,0,False,False,-1,1,0,1,1,"","",0,"DE",False,"0","DP",False,"500000000","DT",False,"0.001","NUMLEVELS",False,"0","WE",False,"300ns","WM",False,"300ns","WN",False,"0ps","WS",False,"0ps"]
            ], 
            [
                "Time:=", ["All"],
                "Speed:=", ["Nominal"]
            ], 
            [
                "Component:=", ["V(AEYEPROBE(required).ctle_out)"]
            ], 
            [
                "Unit Interval:=", "1/Speed",
                "Offset:=", "0ms",
                "Auto Delay:=", True,
                "Manual Delay:=", "0ps",
                "AutoCompCrossAmplitude:=", True,
                "CrossingAmplitude:=", "0mV",
                "AutoCompEyeMeasurementPoint:=", True,
                "EyeMeasurementPoint:=", "1.66666666666667e-11"
            ])
        oModule.AddAllEyeMeasurements("Transient Voltage Plot1")
        plots_exist = True
        
    # 將 Legend 輸出至 temp.csv，並使用 Python 取出數據寫入總表
    try:
        import re
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
            
        # 直接把主圖表的 Legend 輸出成 CSV，這保證跟畫面上顯示的內容 100% 一致！
        oModule.ExportTableToFile("Transient Voltage Plot1", temp_csv, "Legend")
        
        height = "N/A"
        width = "N/A"
        
        if os.path.exists(temp_csv):
            with open(temp_csv, "r") as tr:
                text = tr.read()
            
            # 使用 Regex 精準抓出 "EyeHeight" 跟 "EyeWidth" 後面的第一個數字
            idx_h = text.find("EyeHeight")
            if idx_h != -1:
                m_h = re.search(r'([+-]?\d*\.\d+|[+-]?\d+\.?\d*[eE][+-]?\d+|[+-]?\d+)', text[idx_h+len("EyeHeight"):])
                if m_h: height = m_h.group(1)
                
            idx_w = text.find("EyeWidth")
            if idx_w != -1:
                m_w = re.search(r'([+-]?\d*\.\d+|[+-]?\d+\.?\d*[eE][+-]?\d+|[+-]?\d+)', text[idx_w+len("EyeWidth"):])
                if m_w: width = m_w.group(1)
                        
        with open(summary_csv, "a") as f:
            f.write("{0},{1},{2}\n".format(filename, height, width))
            
        results_data.append({"file": filename, "height": height, "width": width})
    except Exception as e:
        with open(summary_csv, "a") as f:
            f.write("{0},Error: {1}\n".format(filename, str(e)))
            
    # 輸出眼圖結果成 PNG
    image_name = os.path.join(output_dir, filename.replace(".ctle", "_eye.png"))
    try:
        oModule.ExportImageToFile("Transient Voltage Plot1", image_name, 1200, 800)
    except:
        pass

# 掃除臨時檔案
if os.path.exists(temp_csv):
    try:
        os.remove(temp_csv)
    except:
        pass

oProject.Save()

# 5. 分析最佳結果與完成提示視窗
max_h = -9999.0
max_w = -9999.0
best_h_file = ""
best_w_file = ""
all_closed = True

for r in results_data:
    try:
        h_val = float(r['height'])
        w_val = float(r['width'])
        
        # 只要眼高跟眼寬大於 0，就認定眼睛有打開
        if h_val > 0 and w_val > 0:
            all_closed = False
            if h_val > max_h:
                max_h = h_val
                best_h_file = r['file']
            if w_val > max_w:
                max_w = w_val
                best_w_file = r['file']
    except:
        pass

msg = "CTLE 批次眼圖分析已全部完成！\n\n共測試 {0} 個檔案，總表已儲存至:\n{1}\n\n".format(len(ctle_files), summary_csv)

if all_closed:
    msg += "⚠️ 【警告】所有模擬結果的眼睛均「無法打開」！\n(測量結果皆為無效值或負數，請檢查參數設定。)"
else:
    msg += "🏆 【眼高最高】: {0} ({1:g} V)\n".format(best_h_file, max_h)
    msg += "🏆 【眼寬最寬】: {0} ({1:g} s)".format(best_w_file, max_w)

MessageBox.Show(msg, "執行完畢")
