import streamlit as st
import pandas as pd
import glob
import os

# === 1. 系統初始化與駭客矩陣視覺 (CSS) ===
st.set_page_config(page_title="軍工鑄造審計矩陣 V4.6", layout="wide")

st.markdown("""
    <style>
    /* 全域背景歸零 (純黑) */
    .stApp { background-color: #000000; color: #00FF00; font-family: 'Courier New', monospace; }
    /* 文字強制螢光綠 */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stText, .stMetricValue, .stMetricLabel, div[data-testid="stRadio"] label {
        color: #00FF00 !important;
    }
    /* 輸入框與按鈕駭客風 */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        color: #00FF00 !important; background-color: #111111 !important; border: 1px solid #00FF00 !important;
    }
    div[data-baseweb="select"] > div { background-color: #111111 !important; color: #00FF00 !important; }
    
    /* 強制隱藏不需要的元件 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 底部版權列 */
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%; background-color: #000000;
        color: #00FF00; text-align: center; border-top: 1px solid #00FF00; padding: 5px; font-size: 12px; z-index: 999;
    }
    </style>
""", unsafe_allow_html=True)

# === 2. 智能解析引擎 (W/E Parser) & 精確分類演算法 ===
def parse_crypto_value(text):
    if not isinstance(text, str): return float(text)
    text = text.upper().strip().replace(',', '')
    try:
        if 'E' in text: return float(text.replace('E', '')) * 100_000_000
        elif 'W' in text: return float(text.replace('W', '')) * 10_000
        return float(text)
    except: return 0.0

def get_item_category(part_name):
    """
    V4.6 修正：依照長官指定的白名單進行精確分類
    解決 '臂甲' 誤判為防具的問題
    """
    p = str(part_name).strip()
    
    # [優先權 1] 武器矩陣 (Weapons)
    # 包含 '臂甲'，必須先於防具判定
    weapon_whitelist = [
        '臂甲', '長劍', '巨劍', '短劍', '法杖', 
        '弓', '法書', '法珠', '釘錘'
    ]
    if any(k in p for k in weapon_whitelist): 
        return "⚔️ 武器 (Weapon)"

    # [優先權 2] 防具矩陣 (Armor)
    # 包含 '披風'
    armor_whitelist = [
        '頭盔', '肩甲', '胸甲', '手套', '腿甲', '鞋子', '披風'
    ]
    if any(k in p for k in armor_whitelist): 
        return "🛡️ 防具 (Armor)"

    # [優先權 3] 飾品矩陣 (Accessories)
    acc_whitelist = [
        '戒指', '耳環', '項鍊'
    ]
    if any(k in p for k in acc_whitelist): 
        return "💍 飾品 (Accessory)"

    return "📦 其他 (Misc)"

# === 3. 戰術資料載入邏輯 ===
@st.cache_data
def load_data(faction):
    keyword = "魔" if faction == "魔族 (Asmodian)" else "天"
    files = [f for f in glob.glob('裝備成本戰情室*.xlsx') if not f.startswith("~$") and keyword in f]
    
    if not files: return None, None
    file_path = max(files, key=os.path.getmtime)
    try:
        df_r = pd.read_excel(file_path, sheet_name='Data_Recipes')
        df_r.columns = [c.strip() for c in df_r.columns]
        
        # 執行新的分類邏輯
        df_r['戰術類別'] = df_r['部位'].apply(get_item_category)
        
        df_p = pd.read_excel(file_path, sheet_name='Price_List')
        df_p = df_p.iloc[:, :2]
        df_p.columns = ['材料名稱', '基準市價']
        return df_r, df_p
    except: return None, None

# === 4. 主介面：戰略控制台 ===

# [區塊 A] 陣營識別
st.title("軍工鑄造審計矩陣 V4.6")
faction = st.radio("Step 1. 識別陣營代碼", ["魔族 (Asmodian)", "天族 (Elyos)"], horizontal=True)

# [區塊 B] 資金流向監控
st.markdown("---")
st.subheader("Step 2. 資金流向監控 (Currency Radar)")

c1, c2, c3 = st.columns([1, 1.5, 1])

with c1:
    st.markdown("##### 🟢 零售渠道")
    rate_retail_input = st.text_input("1 TWD 可換幣量", value="35000")
    rate_retail = parse_crypto_value(rate_retail_input)

with c2:
    st.markdown("##### 🟡 大盤渠道")
    col_a, col_b = st.columns(2)
    with col_a:
        bulk_price = parse_crypto_value(st.text_input("大盤報價 (TWD)", value="255"))
    with col_b:
        bulk_coin_raw = parse_crypto_value(st.text_input("購買幣量 (W/E)", value="1000W"))
    
    tax_options = {
        "賣家全包 (0%)": 1.00,
        "本服交易 (12%)": 0.88,
        "跨服-賣家吸10% (12%)": 0.88,
        "跨服-賣家不包 (22%)": 0.78
    }
    tax_mode = st.selectbox("稅務損耗模式", list(tax_options.keys()))
    tax_coef = tax_options[tax_mode]
    
    bulk_coin_net = bulk_coin_raw * tax_coef
    rate_bulk_real = bulk_coin_net / bulk_price if bulk_price > 0 else 0

with c3:
    st.markdown("##### ⚖️ 決策建議")
    if rate_bulk_real > 0 and rate_retail > 0:
        if rate_bulk_real > rate_retail:
            diff_pct = (rate_bulk_real - rate_retail) / rate_retail * 100
            st.success(f"✅ 建議：走大盤渠道")
            st.metric("優勢幅度", f"+{diff_pct:.1f}%", f"匯率 1:{rate_bulk_real:,.0f}")
            best_rate = rate_bulk_real
        else:
            diff_pct = (rate_retail - rate_bulk_real) / rate_bulk_real * 100
            st.warning(f"⚠️ 建議：走零售渠道")
            st.metric("大盤虧損", f"-{diff_pct:.1f}%", f"大盤實拿 1:{rate_bulk_real:,.0f}")
            best_rate = rate_retail
    else:
        st.info("等待數據輸入...")
        best_rate = 1

# [區塊 C] 軍工產線配置 (修正版)
st.markdown("---")
st.subheader("Step 3. 軍工產線配置")

df_recipes, df_prices_raw = load_data(faction)

if df_recipes is None:
    st.error(f"❌ 警報：找不到 [{faction}] 的戰情室資料庫檔案！")
else:
    # --- 戰術分鏡選擇邏輯 ---
    rc1, rc2, rc3 = st.columns(3)
    
    with rc1:
        series_list = df_recipes['系列'].unique()
        target_series = st.selectbox("1. 裝備系列", series_list)
        
    with rc2:
        # 動態過濾：只顯示該系列下有的類別
        available_categories = df_recipes[df_recipes['系列'] == target_series]['戰術類別'].unique()
        # 排序優化：讓武器排前面
        cat_order = ["⚔️ 武器 (Weapon)", "🛡️ 防具 (Armor)", "💍 飾品 (Accessory)", "📦 其他 (Misc)"]
        sorted_cats = sorted(available_categories, key=lambda x: cat_order.index(x) if x in cat_order else 99)
        target_category = st.radio("2. 裝備分類 (Filter)", sorted_cats, horizontal=True)
        
    with rc3:
        # 動態過濾：只顯示 [系列] + [類別] 下的部位
        mask_parts = (df_recipes['系列'] == target_series) & (df_recipes['戰術類別'] == target_category)
        parts_list = df_recipes[mask_parts]['部位'].unique()
        target_part = st.selectbox("3. 目標部位", parts_list)

    quantity = st.number_input("製作套數", min_value=1, value=1)

    # 資料處理
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
        
        st.markdown("---")
        # [區塊 D] 最終審計
        st.subheader("Step 4. 最終決策審計 (Final Audit)")
        
        ac1, ac2 = st.columns(2)
        with ac1:
            st.markdown("###### 🔧 成本參數輸入")
            studio_fee_input = st.text_input("工作室代工費/每件 (W/E)", value="0")
            auction_price_input = st.text_input("拍賣場成品單價 (W/E)", value="0")
            studio_fee = parse_crypto_value(studio_fee_input) * quantity
            auction_price = parse_crypto_value(auction_price_input) * quantity
            
        with ac2:
            st.markdown("###### 📊 三方比價矩陣 (TWD / 基納)")
            cost_self_twd = material_cost_coin / best_rate
            st.text(f"[方案 A] 自行製造 (僅材料): {material_cost_coin:,.0f} 基納 | ${cost_self_twd:,.0f} TWD")
            
            cost_studio_coin = material_cost_coin + studio_fee
            cost_studio_twd = cost_studio_coin / best_rate
            st.text(f"[方案 B] 找人代工 (材+工): {cost_studio_coin:,.0f} 基納 | ${cost_studio_twd:,.0f} TWD")
            
            cost_buy_twd = auction_price / best_rate
            st.text(f"[方案 C] 拍賣直購 (成品)  : {auction_price:,.0f} 基納 | ${cost_buy_twd:,.0f} TWD")
            
            st.markdown("---")
            costs = {
                "自行製造": cost_self_twd, 
                "找人代工": cost_studio_twd, 
                "拍賣直購": cost_buy_twd if auction_price > 0 else float('inf')
            }
            best_option = min(costs, key=costs.get)
            lowest_cost = costs[best_option]
            
            st.markdown(f"### ⭐ 戰略建議：{best_option}")
            st.markdown(f"**最低成本：${lowest_cost:,.0f} TWD**")

# === 5. 簽章 ===
st.markdown('<div class="footer">System Architect: 神一 | 軍工鑄造審計矩陣 V4.6</div>', unsafe_allow_html=True)
