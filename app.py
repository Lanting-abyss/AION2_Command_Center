import streamlit as st
import pandas as pd
import glob
import os

st.set_page_config(page_title="軍團裝備指揮系統", layout="wide")

@st.cache_data
def load_data():
    all_files = [f for f in glob.glob('裝備成本戰情室*.xlsx') if not f.startswith("~$")]
    if not all_files:
        st.error("❌ 警報：找不到戰情室檔案！")
        return None, None, None
    file_path = max(all_files, key=os.path.getmtime)
    
    try:
        df_recipes = pd.read_excel(file_path, sheet_name='Data_Recipes')
        # 自動清理欄位名稱的空白，避免 "需求數量 " 讀不到
        df_recipes.columns = [c.strip() for c in df_recipes.columns]
        
        df_prices = pd.read_excel(file_path, sheet_name='Price_List')
        df_prices = df_prices.iloc[:, :2]
        df_prices.columns = ['材料名稱', '目前市價']
        df_prices = df_prices.dropna(subset=['材料名稱'])
        return df_recipes, df_prices, file_path
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return None, None, None

df_recipes, df_prices, current_file = load_data()

if df_recipes is not None:
    st.sidebar.header("⚙️ 戰略配置 (全自動版)")
    st.sidebar.caption(f"目前載入：{current_file}")
    
    # 策略與目標選擇
    strategy = st.sidebar.selectbox("1. 採購策略", ["標準(Standard)", "樂觀(Snipe)", "悲觀(Panic)"])
    series_list = df_recipes['系列'].unique()
    target_series = st.sidebar.selectbox("2. 裝備系列", series_list)
    parts_list = df_recipes[df_recipes['系列'] == target_series]['部位'].unique()
    target_part = st.sidebar.selectbox("3. 目標部位", parts_list)
    quantity = st.sidebar.number_input("4. 製作套數", min_value=1, value=1)

    # 匯率
    st.sidebar.markdown("---")
    rate_retail = st.sidebar.number_input("1 TWD (零售) =", value=35000)
    total_bulk_price = st.sidebar.number_input("大盤總價 (TWD)", value=200)
    total_bulk_coin = st.sidebar.number_input("大盤總幣量", value=10000000)
    best_rate = max(rate_retail, total_bulk_coin / total_bulk_price if total_bulk_price > 0 else 0)
    st.sidebar.info(f"最佳匯率: 1 TWD = {best_rate:,.0f} 遊戲幣")

    # 主畫面
    st.title("🛡️ 軍團裝備指揮系統 (Auto-Loaded)")
    
    # 篩選配方
    mask = (df_recipes['系列'] == target_series) & (df_recipes['部位'] == target_part)
    target_recipe = df_recipes[mask].copy()

    if target_recipe.empty:
        st.warning("⚠️ 查無此裝備配方資料。")
    else:
        # === 資料合併處理 ===
        display_df = target_recipe.merge(df_prices, on='材料名稱', how='left')
        
        # 價格計算
        if strategy == "樂觀(Snipe)": display_df['單價'] = display_df['目前市價'] * 0.8
        elif strategy == "悲觀(Panic)": display_df['單價'] = display_df['目前市價'] * 1.2
        else: display_df['單價'] = display_df['目前市價']
        display_df['單價'] = display_df['單價'].fillna(0)

        # === 關鍵：讀取 Excel 內的數量 ===
        if '需求數量' in display_df.columns:
            display_df['需求數量'] = display_df['需求數量'].fillna(0)
        else:
            st.error("❌ Excel 中缺少「需求數量」欄位！請在 Data_Recipes 分頁新增 D 欄並填寫數值。")
            display_df['需求數量'] = 0

        # 顯示表格 (這裡設為 disabled=False 讓您還是可以臨時微調，但預設值是 Excel 的數字)
        st.markdown("### 📋 戰術配方表 (已自動載入數量)")
        edited_df = st.data_editor(
            display_df[['材料名稱', '目前市價', '單價', '需求數量']],
            column_config={
                "材料名稱": st.column_config.TextColumn(disabled=True),
                "目前市價": st.column_config.NumberColumn(format="$%d", disabled=True),
                "單價": st.column_config.NumberColumn(format="$%d", disabled=True),
                "需求數量": st.column_config.NumberColumn(min_value=0, step=1, required=True)
            },
            hide_index=True,
            use_container_width=True
        )

        # 計算總成本
        total_cost = (edited_df['單價'] * edited_df['需求數量']).sum() * quantity
        
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("### 📊 決策矩陣")
            auction_price = st.number_input("拍賣場成品單價", value=0, step=100000)
            data = []
            for name, tax in [("服內拍賣", 0.12), ("面交 RMT", 0.20), ("跨服急件", 0.22)]:
                gross = total_cost / (1 - tax) if tax < 1 else 0
                buy_total = auction_price * quantity
                if best_rate > 0:
                    sav = (buy_total - gross)/best_rate if gross < buy_total else (gross - buy_total)/best_rate
                    msg = f"🟢 自造省 ${sav:,.0f}" if gross < buy_total else f"🔴 直購省 ${sav:,.0f}"
                else: msg = "匯率未設定"
                data.append([name, f"{tax:.0%}", f"{gross:,.0f}", f"${gross/best_rate:,.0f}", f"${buy_total/best_rate:,.0f}", msg])
            st.table(pd.DataFrame(data, columns=["交易渠道", "耗損", "自造含稅", "自造TWD", "直購TWD", "建議"]))
        
        with c2:
            st.metric("自造總成本 (Net)", f"{total_cost:,.0f}")
            if total_cost == 0: st.info("成本為 0，請確認 Excel 是否有填寫數量。")
