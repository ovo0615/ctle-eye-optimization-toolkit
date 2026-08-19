# CTLE Eye Optimization Toolkit

提供 CTLE 參數產生、批次 sweep 與 Eye Diagram 分析的工具集合，可搭配 AEDT Circuit 進行高速通道分析流程自動化。

## 主要功能

- 產生 CTLE 頻率響應檔案。
- 依起始值、終止值與步進值執行參數 sweep。
- 批次匯入 CTLE 檔案並執行 AEDT Eye Analysis。
- 輸出 Eye Height、Eye Width 等摘要結果。

## 使用環境

- Ansys Electronics Desktop（含 Circuit）
- Python 3
- NumPy：`pip install numpy`
- Matplotlib：`pip install matplotlib`
- PyAEDT：`pip install pyaedt`

## 使用方式

- `ctle_dashboard_gui.py`：啟動 CTLE 產生與分析 GUI。
- `direct_aedt_ctle_macro.py`：在 AEDT 中透過 `Automation > Run Script...` 執行批次流程。

## 公開範圍

本 Repository 公開腳本與操作流程；AEDT 專案與模擬結果僅作展示用途，不代表特定客戶設定。

如需完整流程、模型整合或客製化 Eye Optimization 功能，請來信洽詢。

---

本 Repository 為 Jeff Hong 個人技術作品集之公開展示內容，非 Taiwan Auto-Design Co.（TADC，虎門科技）官方帳號，亦非 Ansys, Inc. 官方合作項目；Ansys、HFSS、SIwave 為 Ansys, Inc. 之商標。原始碼與內容僅供技術展示，未經授權不得商業使用、散布或製作衍生作品，詳見 [LICENSE](LICENSE)。如需授權或合作，請洽 jeff.hong@cadmen.com。
