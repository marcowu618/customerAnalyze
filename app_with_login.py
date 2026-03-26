import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# 设置页面配置
st.set_page_config(page_title="客户级别套餐分布分析", layout="wide")

# 标题
st.title("📊 迈瑞中国区免疫套餐VIP客户分布情况分析 (v1.2-修复数据加载)")
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
    required_cols = ['套餐', '客户级别', '医院编码', '医院名称']
    
    for encoding in encodings:
        try:
            # 1. 尝试 Tab 分隔符 (最有可能)
            df = pd.read_csv(file_path, sep='\t', encoding=encoding)
            if all(col in df.columns for col in required_cols):
                # 清理医院编码
                df['医院编码'] = df['医院编码'].astype(str).str.replace('="', '').str.replace('"', '')
                # 过滤客户级别
                df = df[df['客户级别'].isin(['V1', 'V2', 'V3'])]
                # 核心去重
                df_unique = df.drop_duplicates(subset=['套餐', '客户级别', '医院编码', '医院名称'])
                return df_unique
                
            # 2. 尝试逗号分隔符
            df = pd.read_csv(file_path, sep=',', encoding=encoding)
            if all(col in df.columns for col in required_cols):
                df['医院编码'] = df['医院编码'].astype(str).str.replace('="', '').str.replace('"', '')
                df = df[df['客户级别'].isin(['V1', 'V2', 'V3'])]
                df_unique = df.drop_duplicates(subset=['套餐', '客户级别', '医院编码', '医院名称'])
                return df_unique
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
    st.sidebar.subheader("📈 图表控制")
    bar_mode = st.sidebar.radio(
        "主图显示模式",
        options=["绝对数值", "100% 占比 (分布情况)"],
        index=0
    )
    
    use_log_scale = st.sidebar.checkbox("使用对数 Y 轴 (改善小数值可见度)", value=False)
    
    filtered_df = df[
        (df['客户级别'].isin(selected_levels)) & 
        (df['套餐'].isin(selected_packages))
    ]
    
    # 1. 五大套餐核心概览图 (堆叠柱状图)
    st.subheader("🚀 核心五大套餐分布概览 (V1/V2/V3 堆叠)")
    
    target_packages = ["传染病", "性激素", "甲功", "肿标", "心标"]
    five_packages_df = df[df['套餐'].isin(target_packages)]
    
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

    st.markdown("---")

    # 2. 原始详细分布图
    col1, col2 = st.columns([1.2, 0.8])
    
    summary = filtered_df.groupby(['客户级别', '套餐']).agg({'医院编码': 'count'}).reset_index()
    summary.columns = ['客户级别', '套餐', '客户数量']
    
    with col1:
        st.subheader("📌 套餐覆盖客户数 (详细分布)")
        if bar_mode == "100% 占比 (分布情况)":
            level_sums = summary.groupby('客户级别')['客户数量'].transform('sum')
            summary['占比'] = (summary['客户数量'] / level_sums * 100).round(1)
            fig_bar = px.bar(
                summary, x="客户级别", y="占比", color="套餐",
                title="各级别客户的套餐分布 (100% 堆叠占比)",
                barmode="relative", text=summary['占比'].apply(lambda x: f"{x}%"),
                template="plotly_white", height=500
            )
            fig_bar.update_layout(yaxis_title="占比 (%)", yaxis_range=[0, 100])
        else:
            fig_bar = px.bar(
                summary, x="客户级别", y="客户数量", color="套餐",
                title="各级别客户的套餐分布 (绝对数量统计)",
                barmode="stack", text_auto=True,
                template="plotly_white", height=500
            )
            fig_bar.update_layout(yaxis_title="客户(医院)数量")
            if use_log_scale:
                fig_bar.update_layout(yaxis_type="log")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("📌 客户级别占比 (饼图)")
        level_dist = filtered_df.drop_duplicates('医院编码')['客户级别'].value_counts().reset_index()
        level_dist.columns = ['客户级别', '医院数']
        fig_pie = px.pie(
            level_dist, values='医院数', names='客户级别', 
            title="各级别客户(医院)分布比例", hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    
    # 3. 热力图和明细
    st.subheader("🔍 套餐在各级别的覆盖率矩阵")
    pivot_df = summary.pivot(index='套餐', columns='客户级别', values='客户数量').fillna(0)
    fig_heatmap = px.imshow(
        pivot_df, text_auto=True, aspect="auto",
        labels=dict(x="客户级别", y="套餐", color="客户数"),
        color_continuous_scale='Blues', title="套餐分布热力图"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 客户明细清单")
    display_df = filtered_df[['医院编码', '医院名称', '客户级别', '套餐']].sort_values(['客户级别', '套餐'])
    search_query = st.text_input("🔍 搜索医院名称", "")
    if search_query:
        display_df = display_df[display_df['医院名称'].str.contains(search_query, na=False)]
    
    st.dataframe(
        display_df, use_container_width=True,
        column_config={
            "医院编码": st.column_config.TextColumn("医院编码"),
            "医院名称": st.column_config.TextColumn("医院名称"),
            "客户级别": st.column_config.TextColumn("客户级别"),
            "套餐": st.column_config.TextColumn("套餐")
        }
    )
    
    st.download_button(
        label="📥 导出当前筛选的客户清单",
        data=display_df.to_csv(index=False).encode('utf_8_sig'),
        file_name="客户清单_导出.csv", mime="text/csv"
    )
else:
    st.info("等待数据正确加载...")
