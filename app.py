import streamlit as st
import pandas as pd
import glob
import os

# === 1. 系統初始化 (System Init) ===
st.set_page_config(page_title="軍工鑄造審計矩陣 V5.0", layout="wide")

# CSS 駭客風格注入
st.markdown("""
    <style>
    /* 全域背景歸零 (純黑) */
    .stApp { background-color: #000000; color: #00FF00; font-family: 'Courier New', monospace; }
    /* 文字強制螢光綠 */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stText, .stMetricValue, .stMetricLabel, div[data-testid="stRadio"] label, div[data-testid="stCaptionContainer"] {
        color: #00FF00 !important;
    }
    /* 輸入框與按鈕駭客風 */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        color: #00FF00 !important; background-color: #111111 !important; border: 1px solid #00FF00 !important;
    }
    div[data-baseweb="select"] > div { background-color: #111111 !important; color: #00FF00 !important; }
    
    /* 隱藏不需要的元件 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 底部版權列 */
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%; background-color: #000000;
        color: #00FF00; text-align: center; border-top: 1px solid #00FF00; padding: 5px; font-size: 12px; z-index: 999;
    }
    </style>
""", unsafe_allow_html=True)

# === 2. 核心運算引擎 (Core Engine) ===

def parse_crypto_value(text):
    """ 解析 W/E 單位 """
    if not isinstance(text, str): return float(text)
    text = text.upper().strip().replace(',', '')
    try:
        if 'E' in text: return float(text.replace('E', '')) * 100_000_000
        elif 'W' in text: return float(text.replace('W', '')) * 10_000
        return float(text)
    except: return 0.0

def get_item_category(part_name):
    """
    V5.0 修正：非武即飾，其餘皆防具 (包含長靴)
    """
    p = str(part_name).strip()
    
    # [優先權 1] 武器矩陣 (Weapons)
    weapon_whitelist = [
        '臂甲', '長劍', '巨劍', '短劍', '法杖', 
        '弓', '法書', '法珠', '釘錘', '盾'
    ]
    if any(k in p for k in weapon_whitelist): 
        return "⚔️ 武器 (Weapon)"

    # [優先權 2] 飾品矩陣 (Accessories)
    acc_whitelist = [
        '戒指', '耳環', '項鍊', '腰帶'
    ]
    if any(k in p for k in acc_whitelist): 
        return "💍 飾品 (Accessory)"

    # [優先權 3] 其餘全部歸類為防具 (Fallback to Armor)
    # 包含：頭盔, 胸甲, 手套, 腿甲, 鞋子, 長靴, 披風...
    return "🛡️ 防具 (Armor)"

# === 3. 資料載入 (Data Loader) ===
@st.cache_data
def load_data(faction):
    keyword = "魔" if faction == "魔族 (Asmodian)" else "天"
    files = [f for f in glob.glob('裝備成本戰情室*.xlsx') if not f.startswith("~$") and keyword in f]
    
    if not files: return None, None
    file_path = max(files, key=os.path.getmtime)
    try:
        df_r = pd.read_excel(file_path, sheet_name='Data_Recipes')
        df_r.columns = [c.strip() for c in df_r.columns]
        df_r['戰術類別'] = df_r['部位'].apply(get_item_category) # 重新分類
        
        df_p = pd.read_excel(file_path, sheet_name='Price_List')
        df_p = df_p.iloc[:, :2]
        df_p.columns = ['材料名稱', '基準市價']
        return df_r, df_p
    except: return None, None

# === 4. 主戰場介面 (Main Interface) ===

# [區塊 A] 陣營識別
st.title("軍工鑄造審計矩陣 V5.0")
faction = st.radio("Step 1. 識別陣營代碼", ["魔族 (Asmodian)", "天族 (Elyos)"], horizontal=True)

# [區塊 B] 資金流向監控 (Retail Tax Added)
st.markdown("---")
st.subheader("Step 2. 資金流向監控 (Currency Radar)")

# 定義稅率常數
tax_options = {
    "賣家全包 (0%)": 1.00,
    "本服交易 (12%)": 0.88,
    "跨服-賣家吸10% (12%)": 0.88,
    "跨服-賣家不包 (22%)": 0.78
}

c1, c2, c3 = st.columns([1.2, 1.2, 1])

with c1:
    st.markdown("##### 🟢 零售渠道 (Retail)")
    rate_retail_raw = parse_crypto_value(st.text_input("1 TWD 報價 (例如 35000)", value="35000"))
    # V5.0 新增：零售稅務選擇
    tax_mode_retail = st.selectbox("零售稅務模式", list(tax_options.keys()), index=1, key="retail_tax")
    
    # 計算零售真實匯率
    rate_retail_real = rate_retail_raw * tax_options[tax_mode_retail]
    
    # 顯示折損
    if tax_options[tax_mode_retail] < 1:
        st.caption(f"📉 稅後實拿: 1:{rate_retail_real:,.0f} (損耗 {(1-tax_options[tax_mode_retail]):.0%})")

with c2:
    st.markdown("##### 🟡 大盤渠道 (Bulk)")
    col_a, col_b = st.columns(2)
    with col_a:
        bulk_price = parse_crypto_value(st.text_input("大盤報價 (TWD)", value="255"))
    with col_b:
        bulk_coin_raw = parse_crypto_value(st.text_input("購買幣量 (W/E)", value="1000W"))
    
    tax_mode_bulk = st.selectbox("大盤稅務模式", list(tax_options.keys()), index=1, key="bulk_tax")
    
    # 計算大盤真實匯率
    bulk_coin_net = bulk_coin_raw * tax_options[tax_mode_bulk]
    rate_bulk_real = bulk_coin_net / bulk_price if bulk_price > 0 else 0
    
    if tax_options[tax_mode_bulk] < 1:
        st.caption(f"📉 稅後實拿: {bulk_coin_net:,.0f} 幣")

with c3:
    st.markdown("##### ⚖️ 決策建議")
    if rate_bulk_real > 0 and rate_retail_real > 0:
        if rate_bulk_real > rate_retail_real:
            diff_pct = (rate_bulk_real - rate_retail_real) / rate_retail_real * 100
            st.success(f"✅ 建議：走大盤")
            st.metric("優勢幅度", f"+{diff_pct:.1f}%", f"匯率 1:{rate_bulk_real:,.0f}")
            best_rate = rate_bulk_real
        else:
            diff_pct = (rate_retail_real - rate_bulk_real) / rate_bulk_real * 100
            st.warning(f"⚠️ 建議：走零售")
            st.metric("大盤虧損", f"-{diff_pct:.1f}%", f"零售 1:{rate_retail_real:,.0f}")
            best_rate = rate_retail_real
    else:
        st.info("等待數據...")
        best_rate = 1

# [區塊 C] 軍工產線配置
st.markdown("---")
st.subheader("Step 3. 軍工產線配置")

df_recipes, df_prices_raw = load_data(faction)

if df_recipes is None:
    st.error(f"❌ 警報：找不到 [{faction}] 資料庫！")
else:
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        series_list = df_recipes['系列'].unique()
        target_series = st.selectbox("1. 裝備系列", series_list)
        
    with rc2:
        # V5.0 分類邏輯：無 "其他"，全併入 "防具"
        available_categories = df_recipes[df_recipes['系列'] == target_series]['戰術類別'].unique()
        cat_order = ["⚔️ 武器 (Weapon)", "🛡️ 防具 (Armor)", "💍 飾品 (Accessory)"]
        sorted_cats = sorted(available_categories, key=lambda x: cat_order.index(x) if x in cat_order else 99)
        target_category = st.radio("2. 裝備分類", sorted_cats, horizontal=True)
        
    with rc3:
        mask_parts = (df_recipes['系列'] == target_series) & (df_recipes['戰術類別'] == target_category)
        parts_list = df_recipes[mask_parts]['部位'].unique()
        target_part = st.selectbox("3. 目標部位", parts_list)

    quantity = st.number_input("製作套數", min_value=1, value=1)

    # 配方計算
    mask = (df_recipes['系列'] == target_series) & (df_recipes['部位'] == target_part)
    target_recipe = df_recipes[mask].copy()

    if target_recipe.empty:
        st.warning("⚠️ 查無配方")
    else:
        display_df = target_recipe.merge(df_prices_raw, on='材料名稱', how='left')
        display_df['基準市價'] = display_df['基準市價'].fillna(0)
        display_df['需求數量'] = display_df.get('需求數量', 0).fillna(0)
        display_df['交易所單價'] = display_df['基準市價']

        st.markdown("#### 📋 成本動態計算")
        edited_df = st.data_editor(
            display_df[['材料名稱', '需求數量', '交易所單價']],
            column_config={
                "材料名稱": st.column_config.TextColumn(disabled=True),
                "需求數量": st.column_config.NumberColumn(disabled=True),
                "交易所單價": st.column_config.NumberColumn(format="$%d", step=10000)
            },
            use_container_width=True,
            hide_index=True
        )
        
        material_cost_coin = (edited_df['交易所單價'] * edited_df['需求數量']).sum() * quantity
        
        # [區塊 D] 最終審計 (V5.0 代工費改為 TWD)
        st.markdown("---")
        st.subheader("Step 4. 最終決策審計 (Final Audit)")
        
        ac1, ac2 = st.columns(2)
        with ac1:
            st.markdown("###### 🔧 成本參數輸入")
            # 改為 TWD 輸入
            studio_fee_twd_input = st.text_input("工作室代工費/每件 (TWD)", value="0")
            auction_price_input = st.text_input("拍賣場成品單價 (W/E)", value="0")
            
            # 代工費 (TWD)
            studio_fee_twd = parse_crypto_value(studio_fee_twd_input) * quantity
            # 拍賣成品 (Coin)
            auction_price_coin = parse_crypto_value(auction_price_input) * quantity
            
        with ac2:
            st.markdown("###### 📊 三方比價矩陣 (全 TWD 結算)")
            
            # 方案 A: 自造 (材料費/匯率)
            cost_self_twd = material_cost_coin / best_rate
            st.text(f"[A] 自行製造 (僅材料): {material_cost_coin:,.0f} 基納 | ${cost_self_twd:,.0f}")
            
            # 方案 B: 代工 (材料費/匯率 + 代工費TWD)
            # 這裡的邏輯是：材料通常還是自己買(付幣)，然後給工作室TWD代工費
            cost_studio_total_twd = (material_cost_coin / best_rate) + studio_fee_twd
            st.text(f"[B] 找人代工 (材+工): 材料折台幣${cost_self_twd:,.0f} + 工費${studio_fee_twd:,.0f} = ${cost_studio_total_twd:,.0f}")
            
            # 方案 C: 直購 (成品費/匯率)
            cost_buy_twd = auction_price_coin / best_rate
            st.text(f"[C] 拍賣直購 (成品)  : {auction_price_coin:,.0f} 基納 | ${cost_buy_twd:,.0f}")
            
            st.markdown("---")
            
            # 比價邏輯
            costs = {
                "自行製造": cost_self_twd, 
                "找人代工": cost_studio_total_twd, 
                "拍賣直購": cost_buy_twd if auction_price_coin > 0 else float('inf')
            }
            best_option = min(costs, key=costs.get)
            lowest_cost = costs[best_option]
            
            st.markdown(f"### ⭐ 戰略建議：{best_option}")
            st.markdown(f"**最低成本：${lowest_cost:,.0f} TWD**")

# === 5. 簽章 ===
st.markdown('<div class="footer">System Architect: 神一 | 軍工鑄造審計矩陣 V5.0</div>', unsafe_allow_html=True)
