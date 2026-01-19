import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 系統配置 (System Config)
# ==========================================
st.set_page_config(
    page_title="神一・軍工博弈終端",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS: 軍工黑紅風格 + 浮水印 + 隱藏選單
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #C0C0C0; }
    .watermark {
        position: fixed; bottom: 10px; right: 10px; opacity: 0.3;
        font-size: 10px; color: #D32F2F; font-weight: bold; pointer-events: none;
    }
    h1, h2, h3 { color: #D32F2F !important; font-family: 'Courier New', monospace; }
    div[data-testid="stMetric"] { background-color: #1A1A1A; border: 1px solid #333; border-radius: 4px; }
    .stButton>button { width: 100%; border-radius: 0px; font-weight: bold; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    
    /* 戰術裁決區塊樣式 */
    .verdict-box {
        padding: 15px; border-left: 5px solid #D32F2F; background-color: #1E1E1E; margin-top: 10px;
    }
    .profit { color: #4CAF50; font-weight: bold; }
    .loss { color: #F44336; font-weight: bold; }
    .neutral { color: #FFC107; font-weight: bold; }
    </style>
    <div class="watermark">SHEN YI MILITARY INDUSTRIES | INTJ STRATEGY CORE</div>
    """, unsafe_allow_html=True)

# ==========================================
# 核心函數庫 (Core Logic)
# ==========================================

def parse_crypto_val(s):
    """大額數值解析 (支援 1.2E, 5000W)"""
    if isinstance(s, (int, float)): return float(s)
    s = str(s).strip().upper().replace(',', '')
    try:
        if 'E' in s or '億' in s: return float(s.replace('E','').replace('億','')) * 100_000_000
        if 'W' in s or '萬' in s: return float(s.replace('W','').replace('萬','')) * 10_000
        if 'K' in s: return float(s.replace('K','')) * 1_000
        return float(s)
    except: return 0.0

@st.cache_data(ttl=60)
def load_master_data():
    """讀取 Master Data (分頁模式)"""
    # 這裡讀取的是您剛剛用 Data_Forge.py 鑄造出來的檔案
    file_path = "AION2_Master_Data.xlsx"
    try:
        xl = pd.ExcelFile(file_path)
        return xl
    except Exception as e:
        return None

# ==========================================
# 側邊欄：戰情中心 (Sidebar)
# ==========================================
with st.sidebar:
    st.header("📡 指揮官戰術頻道")
    # 從 Secrets 讀取網址，若無則不顯示
    stream_url = st.secrets.get("STREAM_URL", "")
    if stream_url:
        st.video(stream_url)
        st.caption("🔴 LIVE | 戰略情報同步中")
    else:
        st.info("訊號連結靜默中 (等待 Secrets 配置)")
    
    st.divider()
    
    st.header("💰 匯率審計儀")
    calc_mode = st.radio("模式", ["直接匯率", "總價反推"], label_visibility="collapsed")
    
    nominal_rate = 0.0
    if calc_mode == "總價反推":
        c1, c2 = st.columns(2)
        twd = c1.number_input("TWD", value=255, label_visibility="collapsed")
        coin_str = c2.text_input("Coin", value="1000W", label_visibility="collapsed")
        coin_val = parse_crypto_val(coin_str)
        if twd > 0: nominal_rate = coin_val / twd
    else:
        nominal_rate = st.number_input("匯率 (1:X)", value=42000, step=100)
        
    st.caption(f"基準匯率: 1 : {nominal_rate:,.0f}")
    
    # 稅務損耗
    scenario = st.selectbox("交易情境", ["本服 (-12%)", "跨服 (-22%)", "跨服包稅 (-12%)", "完全包稅 (0%)"])
    tax_map = {"本服 (-12%)": 0.88, "跨服 (-22%)": 0.78, "跨服包稅 (-12%)": 0.88, "完全包稅 (0%)": 1.0}
    real_rate = nominal_rate * tax_map[scenario]
    
    if nominal_rate > 0:
        st.markdown(f"**真實價值 (TWD):** `1 : {real_rate:,.0f}`")
        st.progress(tax_map[scenario])

# ==========================================
# 主介面：軍工博弈面板
# ==========================================
st.title("神一・軍工成本審計矩陣")

# 陣營選擇
faction = st.radio("FACTION SELECT", ["Asmodian (魔族)", "Elyos (天族)"], horizontal=True)

xl_data = load_master_data()

if xl_data:
    sheet_name = "Asmodian" if "Asmodian" in faction else "Elyos"
    
    # 檢查分頁是否存在
    if sheet_name in xl_data.sheet_names:
        df = xl_data.parse(sheet_name)
        
        # 若是天族且資料為空 (只有標題)
        if sheet_name == "Elyos" and df.empty:
             st.warning("⚠️ 天族情報庫構建中 (Data Empty)")
        else:
            # --- 區域 1: 成本計算 ---
            col_table, col_metrics = st.columns([2, 1])
            
            with col_table:
                st.subheader(f"🛠️ {faction.split()[0]} 配方審計")
                edited_df = st.data_editor(
                    df, 
                    num_rows="dynamic", 
                    use_container_width=True,
                    column_config={
                        "單價": st.column_config.NumberColumn(format="%d"),
                        "數量": st.column_config.NumberColumn(format="%d")
                    }
                )
                
                # 計算總成本
                try:
                    # 確保數值型態正確
                    edited_df["單價"] = pd.to_numeric(edited_df["單價"], errors='coerce').fillna(0)
                    edited_df["數量"] = pd.to_numeric(edited_df["數量"], errors='coerce').fillna(0)
                    total_kinah = (edited_df["單價"] * edited_df["數量"]).sum()
                except:
                    total_kinah = 0

            with col_metrics:
                st.subheader("📊 成本錨定")
                st.metric("自製總成本 (基納)", f"{total_kinah:,.0f}")
                
                if real_rate > 0:
                    real_twd = total_kinah / real_rate
                    st.metric("法幣成本 (NTD)", f"${real_twd:,.0f}")
                else:
                    st.info("請設定左側匯率以解鎖法幣分析")

            st.divider()

            # --- 區域 2: 工作室三方博弈雷達 ---
            st.subheader("🎯 工作室三方博弈雷達 (Arbitrage Radar)")
            st.caption("破解定價陷阱：將所有報價統一為 TWD 進行對沖判定")

            r1, r2, r3 = st.columns(3)
            
            # A. 工作室訂製價
            studio_price_twd = r1.number_input("工作室訂製報價 (TWD)", min_value=0, value=0, help="代練/工作室開出的台幣價格")
            
            # B. 拍賣場現貨價
            market_price_str = r2.text_input("拍賣場現貨 (基納)", value="0", help="支援 1.2E 或 5000W")
            market_price_kinah = parse_crypto_val(market_price_str)
            
            # C. 自製成本 (已計算)
            craft_price_kinah = total_kinah

            # 執行博弈分析
            if real_rate > 0:
                
                # 統一換算為 TWD
                market_price_twd = 0
                if market_price_kinah > 0:
                    market_price_twd = market_price_kinah / real_rate
                
                craft_price_twd = craft_price_kinah / real_rate
                
                # 輸出戰術裁決
                st.markdown("#### ⚡ 神一戰術裁決 (The Verdict)")
                
                with st.container():
                    # 1. 訂製 vs 現貨 (工作室溢價分析)
                    if studio_price_twd > 0 and market_price_kinah > 0:
                        diff = studio_price_twd - market_price_twd
                        diff_pct = (diff / market_price_twd) * 100
                        if diff > 0:
                            st.markdown(f"""
                            <div class='verdict-box'>
                            <b>🔴 智商稅警報 (Stupidity Tax):</b> 工作室訂製比現貨貴 <span class='loss'>NT$ {diff:,.0f} (+{diff_pct:.1f}%)</span><br>
                            指令：<b>拒絕訂製，直接掃拍賣場。</b>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                             st.markdown(f"""
                            <div class='verdict-box'>
                            <b>🟢 倒掛機會:</b> 工作室報價比現貨便宜 <span class='profit'>NT$ {abs(diff):,.0f}</span><br>
                            指令：<b>異常低價，可考慮訂製 (注意帳號風險)。</b>
                            </div>
                            """, unsafe_allow_html=True)

                    # 2. 現貨 vs 自製 (隱含風險分析)
                    if market_price_kinah > 0 and craft_price_kinah > 0:
                        margin_twd = market_price_twd - craft_price_twd
                        
                        if margin_twd > 0:
                            # 反推市場隱含失敗率
                            implied_fail_rate = (1 - (craft_price_kinah / market_price_kinah)) * 100
                            st.markdown(f"""
                            <div class='verdict-box'>
                            <b>🟡 套利空間分析:</b> 自製比現貨便宜 <span class='profit'>NT$ {margin_twd:,.0f}</span><br>
                            市場隱含失敗率：<b>{implied_fail_rate:.1f}%</b><br>
                            指令：若您認為連續失敗機率低於 <b>{implied_fail_rate:.0f}%</b>，則<b>執行自製</b>。
                            </div>
                            """, unsafe_allow_html=True)
                        elif margin_twd < 0:
                            loss = abs(margin_twd)
                            st.markdown(f"""
                            <div class='verdict-box'>
                            <b>🔴 虧損警告:</b> 自製成本比現貨還貴 <span class='loss'>NT$ {loss:,.0f}</span><br>
                            指令：<b>禁止自製 (期望值為負)，直接購買現貨。</b>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # 3. 若只有自製成本，無比價對象
                    if studio_price_twd == 0 and market_price_kinah == 0:
                        st.info("等待輸入 [訂製報價] 或 [現貨價格] 以啟動博弈判定...")
                            
            elif real_rate == 0:
                st.warning("⚠️ 數據不足：請先在左側設定「匯率」以啟動法幣分析。")

    else:
         st.error(f"分頁索引錯誤：找不到 {sheet_name}。請確認 Excel 分頁名稱正確。")
else:
    st.error("🚨 系統錯誤：找不到數據庫。請確認 [AION2_Master_Data.xlsx] 已上傳至 GitHub。")

# ==========================================
# 頁尾
# ==========================================
st.markdown("---")
st.caption("System Architecture by Shen Yi | 2026")
