import streamlit as st
import pandas as pd
import glob
import os
import re

# === 1. 系統初始化與視覺駭入 (CSS Injection) ===
st.set_page_config(page_title="軍工鑄造審計矩陣", layout="wide")

# 定義矩陣風格 (Terminal Matrix Theme)
st.markdown("""
    <style>
    /* 全域背景歸零 (純黑) */
    .stApp {
        background-color: #000000;
        color: #00FF00;
        font-family: 'Courier New', monospace;
    }
    /* 所有文字強制螢光綠 */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stText, .stMetricValue, .stMetricLabel {
        color: #00FF00 !important;
    }
    /* 輸入框駭客風 */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        color: #00FF00 !important;
        background-color: #111111 !important;
        border: 1px solid #00FF00 !important;
    }
    /* 表格樣式重構 */
    div[data-testid="stDataFrame"] {
        border: 1px solid #003300;
    }
    /* 底部版權列 */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #000000;
        color: #00FF00;
        text-align: center;
        border-top: 1px solid #00FF00;
        padding: 5px;
        font-size: 12px;
        z-index: 999;
    }
    </style>
""", unsafe_allow_html=True)

# === 2. 智能解析引擎 (W/E Parser) ===
def parse_crypto_value(text):
    """
    將帶有 W(萬), E(億) 的戰術代碼轉換為浮點數
    """
    if not isinstance(text, str):
        return float(text)
    
    text = text.upper().strip().replace(',', '') # 去除干擾符
    
    try:
        if 'E' in text:
            base = float(text.replace('E', ''))
            return base * 100_000_000
        elif 'W' in text:
            base = float(text.replace('W', ''))
            return base * 10_000
        else:
            return float(text)
    except:
        return 0.0

# === 3. 資料庫讀取 ===
@st.cache_data
def get_available_files():
    files = [f for f in glob.glob('裝備成本戰情室*.xlsx') if not f.startswith("~$")]
    files.sort()
    return files

available_files = get_available_files()

# === 4. 側邊欄：戰術參數配置 ===
st.sidebar.markdown("### ⚙️ 戰術參數配置")

# 4-1. 檔案選擇
if not available_files:
    st.sidebar.error("❌ 警報：無數據源")
    st.stop()
selected_file = st.sidebar.selectbox("資料庫來源", available_files)

# 4-2. 匯率與資金渠道 (動態稅率)
st.sidebar.markdown("---")
st.sidebar.markdown("#### 💰 資金流向監控")

# 使用文字輸入以支援 W/E 語法
rate_retail_input = st.sidebar.text_input("1 TWD (零售) 報價", value="35000")
bulk_price_input = st.sidebar.text_input("大盤總價 (TWD)", value="255")
bulk_coin_input = st.sidebar.text_input("購買幣量 (支援 W/E)", value="1000W")

# 稅率情境選擇
tax_options = {
    "🟢 賣家全包 (無損耗 0%)": 1.00,
    "🟡 本服交易 (系統稅 12%)": 0.88,
    "🟡 跨服-賣家吸10% (淨損 12%)": 0.88,
    "🔴 跨服-賣家不包 (重稅 22%)": 0.78
}
selected_tax_name = st.sidebar.selectbox("交易/稅務渠道", list(tax_options.keys()), index=1)
tax_coefficient = tax_options[selected_tax_name]

# 匯率即時運算
rate_retail = parse_crypto_value(rate_retail_input)
bulk_price = parse_crypto_value(bulk_price_input)
bulk_coin_raw = parse_crypto_value(bulk_coin_input)

# 計算真實到手幣量
bulk_coin_net = bulk_coin_raw * tax_coefficient
# 計算最佳匯率 (取 零售 vs 大盤真實匯率 的最大值)
bulk_rate = bulk_coin_net / bulk_price if bulk_price > 0 else 0
best_rate = max(rate_retail, bulk_rate)

st.sidebar.metric(
    "📉 真實匯率 (含稅)",
    f"1 : {best_rate:,.0f}",
    delta=f"損耗: {(1-tax_coefficient):.0%}" if tax_coefficient < 1 else "無損",
    delta_color="inverse"
)

# 4-3. 採購目標
st.sidebar.markdown("---")
try:
    df_recipes = pd.read_excel(selected_file, sheet_name='Data_Recipes')
    df_recipes.columns = [c.strip() for c in df_recipes.columns]
    
    # 讀取 Excel 原始價格作為基準
    df_prices_raw = pd.read_excel(selected_file, sheet_name='Price_List')
    df_prices_raw = df_prices_raw.iloc[:, :2]
    df_prices_raw.columns = ['材料名稱', '基準市價']
    
except Exception as e:
    st.error(f"資料庫讀取失敗: {e}")
    st.stop()

series_list = df_recipes['系列'].unique()
target_series = st.sidebar.selectbox("裝備系列", series_list)
parts_list = df_recipes[df_recipes['系列'] == target_series]['部位'].unique()
target_part = st.sidebar.selectbox("目標部位", parts_list)
quantity = st.sidebar.number_input("製作套數", min_value=1, value=1)

# === 5. 主畫面：軍工審計矩陣 ===
st.title("軍工鑄造審計矩陣")
st.markdown(f"> **TARGET:** {target_series} | {target_part} | **x{quantity}**")

# 資料篩選
mask = (df_recipes['系列'] == target_series) & (df_recipes['部位'] == target_part)
target_recipe = df_recipes[mask].copy()

if target_recipe.empty:
    st.warning("⚠️ 查無配方")
else:
    # 合併價格
    display_df = target_recipe.merge(df_prices_raw, on='材料名稱', how='left')
    display_df['基準市價'] = display_df['基準市價'].fillna(0)
    
    # 確保有數量欄位
    if '需求數量' not in display_df.columns:
        display_df['需求數量'] = 0
    else:
        display_df['需求數量'] = display_df['需求數量'].fillna(0)

    # 準備編輯區資料 (預設交易所價格 = 基準市價)
    # 我們讓使用者編輯 '交易所單價'
    display_df['交易所單價'] = display_df['基準市價']
    
    st.markdown("### 📋 動態火控面板 (可編輯單價)")
    
    # 使用 Data Editor 讓使用者改價
    edited_df = st.data_editor(
        display_df[['材料名稱', '需求數量', '交易所單價']],
        column_config={
            "材料名稱": st.column_config.TextColumn(disabled=True),
            "需求數量": st.column_config.NumberColumn(format="%d", disabled=True),
            "交易所單價": st.column_config.NumberColumn(
                format="$%d", 
                min_value=0, 
                step=10000, 
                help="點擊修改即時價格"
            )
        },
        use_container_width=True,
        hide_index=True
    )

    # === 即時運算核心 ===
    # 這裡會根據使用者改過的 edited_df 重新計算
    edited_df['單項小計'] = edited_df['交易所單價'] * edited_df['需求數量']
    total_cost_coin = edited_df['單項小計'].sum() * quantity
    total_cost_twd = total_cost_coin / best_rate if best_rate > 0 else 0

    st.markdown("---")
    
    # 顯示總結果
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 📊 成本審計")
        st.metric("自造總成本 (基納)", f"{total_cost_coin:,.0f}")
        st.metric("自造總現金 (TWD)", f"${total_cost_twd:,.0f}")
        
    with col2:
        st.markdown("#### ⚖️ 損益決策")
        auction_price_input = st.text_input("拍賣場成品單價 (支援 W/E)", value="0")
        auction_price = parse_crypto_value(auction_price_input)
        
        buy_total_coin = auction_price * quantity
        buy_total_twd = buy_total_coin / best_rate if best_rate > 0 else 0
        
        if auction_price > 0:
            diff = buy_total_coin - total_cost_coin
            diff_twd = diff / best_rate
            
            if diff > 0:
                st.success(f"✅ 自造獲利: {diff:,.0f} 基納")
                st.success(f"💰 現金節省: ${diff_twd:,.0f} TWD")
            else:
                st.error(f"❌ 自造虧損: {abs(diff):,.0f} 基納")
                st.error(f"💸 建議直購 (省 ${abs(diff_twd):,.0f})")
        else:
            st.info("等待輸入成品價格...")

# === 6. 系統簽章 ===
st.markdown('<div class="footer">System Architect: 神一 | 軍工鑄造審計矩陣 Ver 3.0</div>', unsafe_allow_html=True)
