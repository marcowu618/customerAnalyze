import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# 设置页面配置
st.set_page_config(page_title="客户级别套餐产出分析", layout="wide")

# 标题
st.title("📊 迈瑞中国区免疫套餐VIP客户产出分析")
st.markdown("---")

@st.cache_data
def load_data():
    file_path = "设备项目月度产出统计_1.csv"
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        st.error(f"❌ 找不到数据文件: {file_path}")
        return None
        
    # 优先尝试 utf-16，因为这是 Excel 导出的常见 tab 分隔文件编码
    encodings = ['utf-16', 'utf-8-sig', 'utf-8', 'gbk', 'gb2312']
    # 增加 'MR产出（万元）' 字段
    required_cols = ['套餐', '客户级别', '医院编码', '医院名称', 'MR产出（万元）']
    
    for encoding in encodings:
        try:
            # 1. 尝试 Tab 分隔符 (最有可能)
            df = pd.read_csv(file_path, sep='\t', encoding=encoding)
            if all(col in df.columns for col in required_cols):
                # 清理医院编码（处理 ="0060029527" 这种 Excel 格式）
                df['医院编码'] = df['医院编码'].astype(str).str.replace('="', '').str.replace('"', '')
                # 过滤客户级别，只关注 V1, V2, V3
                df = df[df['客户级别'].isin(['V1', 'V2', 'V3'])]
                # 转换产出为数值，处理可能的非数值字符
                df['MR产出（万元）'] = pd.to_numeric(df['MR产出（万元）'], errors='coerce').fillna(0)
                return df
                
            # 2. 尝试逗号分隔符
            df = pd.read_csv(file_path, sep=',', encoding=encoding)
            if all(col in df.columns for col in required_cols):
                df['医院编码'] = df['医院编码'].astype(str).str.replace('="', '').str.replace('"', '')
                df = df[df['客户级别'].isin(['V1', 'V2', 'V3'])]
                df['MR产出（万元）'] = pd.to_numeric(df['MR产出（万元）'], errors='coerce').fillna(0)
                return df
        except Exception:
            continue
            
    st.error(f"❌ 无法正确解析文件内容，请检查文件格式是否包含：{required_cols}")
    return None

df = load_data()

if df is not None:
    # 侧边栏过滤器
    st.sidebar.header("🎯 数据筛选")
    selected_levels = st.sidebar.multiselect(
        "选择客户级别",
        options=['V1', 'V2', 'V3'],
        default=['V1', 'V2', 'V3']
    )
    
    # 套餐多选
    all_packages = sorted(df['套餐'].unique().tolist())
    selected_packages = st.sidebar.multiselect(
        "选择套餐类型",
        options=all_packages,
        default=all_packages
    )

    st.sidebar.markdown("---")
    
    filtered_df = df[
        (df['客户级别'].isin(selected_levels)) & 
        (df['套餐'].isin(selected_packages))
    ]
    
    # --- 新增分析部分：产出排名 ---
    st.header("💰 套餐产出分析")
    
    # 1. 各套餐总产出排名
    st.subheader("📌 各套餐总产出排名 (万元)")
    pkg_revenue = filtered_df.groupby('套餐')['MR产出（万元）'].sum().reset_index()
    pkg_revenue = pkg_revenue.sort_values(by='MR产出（万元）', ascending=False)
    
    fig_pkg_rev = px.bar(
        pkg_revenue,
        x='套餐',
        y='MR产出（万元）',
        text_auto='.2f',
        title="各套餐年度/月度总产出排名",
        labels={'MR产出（万元）': '总产出 (万元)'},
        template="plotly_white",
        color='MR产出（万元）',
        color_continuous_scale='Blues'
    )
    st.plotly_chart(fig_pkg_rev, use_container_width=True)
    
    # 2. 核心分析：不同套餐下产出最大的客户
    st.subheader("🏆 各套餐下的 Top 产出客户")
    
    # 按 套餐 + 医院 汇总产出
    customer_revenue = filtered_df.groupby(['套餐', '医院名称', '客户级别'])['MR产出（万元）'].sum().reset_index()
    
    # 获取每个套餐产出前 10 的客户
    top_n = 10
    top_customers = customer_revenue.sort_values(['套餐', 'MR产出（万元）'], ascending=[True, False]).groupby('套餐').head(top_n)
    
    # 让用户选择一个套餐查看详细排名
    target_pkg = st.selectbox("选择套餐查看客户产出排名", options=pkg_revenue['套餐'].tolist())
    
    pkg_top_customers = customer_revenue[customer_revenue['套餐'] == target_pkg].sort_values(by='MR产出（万元）', ascending=False).head(15)
    
    fig_top_cust = px.bar(
        pkg_top_customers,
        y='医院名称',
        x='MR产出（万元）',
        color='客户级别',
        orientation='h',
        text_auto='.2f',
        title=f"{target_pkg} 套餐产出 Top 15 客户名单",
        labels={'MR产出（万元）': '产出 (万元)', '医院名称': '医院名称'},
        template="plotly_white",
        color_discrete_map={"V1": "#1f77b4", "V2": "#ff7f0e", "V3": "#2ca02c"}
    )
    # 反转 y 轴让最大的在上面
    fig_top_cust.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_top_cust, use_container_width=True)

    st.markdown("---")
    
    # --- 原有分析部分：分布概览 ---
    st.header("📊 套餐分布概览")
    
    # 原始详细分布图
    col1, col2 = st.columns([1.2, 0.8])
    
    # 重新计算去重后的分布数据
    df_unique = filtered_df.drop_duplicates(subset=['套餐', '客户级别', '医院编码', '医院名称'])
    summary = df_unique.groupby(['客户级别', '套餐']).agg({'医院编码': 'count'}).reset_index()
    summary.columns = ['客户级别', '套餐', '客户数量']
    
    with col1:
        st.subheader("📌 套餐覆盖客户数 (详细分布)")
        fig_bar = px.bar(
            summary, x="客户级别", y="客户数量", color="套餐",
            title="各级别客户的套餐分布 (绝对数量统计)",
            barmode="stack", text_auto=True,
            template="plotly_white", height=500
        )
        fig_bar.update_layout(yaxis_title="客户(医院)数量")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("📌 客户级别占比 (饼图)")
        level_dist = df_unique.drop_duplicates('医院编码')['客户级别'].value_counts().reset_index()
        level_dist.columns = ['客户级别', '医院数']
        fig_pie = px.pie(
            level_dist, values='医院数', names='客户级别', 
            title="各级别客户(医院)分布比例", hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    
    # 热力图
    st.subheader("🔍 套餐在各级别的覆盖率矩阵")
    pivot_df = summary.pivot(index='套餐', columns='客户级别', values='客户数量').fillna(0)
    fig_heatmap = px.imshow(
        pivot_df, text_auto=True, aspect="auto",
        labels=dict(x="客户级别", y="套餐", color="客户数"),
        color_continuous_scale='Blues', title="套餐分布热力图"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.markdown("---")
    
    # 客户明细清单
    st.subheader("📋 客户明细清单")
    # 清单增加产出列
    display_df = filtered_df.groupby(['医院编码', '医院名称', '客户级别', '套餐'])['MR产出（万元）'].sum().reset_index()
    display_df = display_df.sort_values(by='MR产出（万元）', ascending=False)
    
    search_query = st.text_input("🔍 搜索医院名称", "")
    if search_query:
        display_df = display_df[display_df['医院名称'].str.contains(search_query, na=False)]
    
    st.dataframe(
        display_df, use_container_width=True,
        column_config={
            "医院编码": st.column_config.TextColumn("医院编码"),
            "医院名称": st.column_config.TextColumn("医院名称"),
            "客户级别": st.column_config.TextColumn("客户级别"),
            "套餐": st.column_config.TextColumn("套餐"),
            "MR产出（万元）": st.column_config.NumberColumn("产出 (万元)", format="%.2f")
        }
    )
    
    st.download_button(
        label="📥 导出当前筛选的客户清单 (含产出)",
        data=display_df.to_csv(index=False).encode('utf_8_sig'),
        file_name="客户产出清单_导出.csv", mime="text/csv"
    )

    st.markdown("---")

    # 4. 五大套餐核心概览图 (堆叠柱状图) - 移至最下方
    st.subheader("🚀 核心五大套餐分布概览 (V1/V2/V3 堆叠)")
    
    target_packages = ["传染病", "性激素", "甲功", "肿标", "心标"]
    five_packages_df = df_unique[df_unique['套餐'].isin(target_packages)]
    
    if not five_packages_df.empty:
        five_summary = five_packages_df.groupby(['套餐', '客户级别']).agg({'医院编码': 'count'}).reset_index()
        five_summary.columns = ['套餐', '客户级别', '客户数量']
        
        # 计算总计用于排序
        total_counts = five_summary.groupby('套餐')['客户数量'].sum().reset_index()
        total_counts = total_counts.sort_values(by='客户数量', ascending=False)
        sorted_five_packages = total_counts['套餐'].tolist()
        
        fig_five = px.bar(
            five_summary,
            x="套餐",
            y="客户数量",
            color="客户级别",
            barmode="stack",
            text="客户数量",
            template="plotly_white",
            height=500,
            category_orders={
                "套餐": sorted_five_packages,
                "客户级别": ["V3", "V2", "V1"]
            },
            color_discrete_map={"V1": "#1f77b4", "V2": "#ff7f0e", "V3": "#2ca02c"}
        )
        fig_five.update_traces(texttemplate='%{text}', textposition='inside')
        
        # 添加顶部总数
        for i, row in total_counts.iterrows():
            fig_five.add_annotation(
                x=row['套餐'], y=row['客户数量'], text=f"{int(row['客户数量'])}",
                showarrow=False, yshift=10, font=dict(size=12, color="black", family="Arial Black")
            )
        st.plotly_chart(fig_five, use_container_width=True)
    else:
        st.warning("未在数据中找到五大核心套餐。")

else:
    st.info("等待数据正确加载...")
