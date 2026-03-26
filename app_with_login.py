import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 设置页面配置
st.set_page_config(page_title="客户级别套餐分布分析", layout="wide")

# 标题
st.title("📊 迈瑞中国区免疫套餐VIP客户分布情况分析")
st.markdown("---")

@st.cache_data
def load_data():
    file_path = "设备项目月度产出统计_1.csv"
    encodings = ['utf-8', 'utf-16', 'gbk', 'gb2312', 'utf-8-sig']
    df = None
    
    # 需要的关键字段
    required_cols = ['套餐', '客户级别', '医院编码', '医院名称']
    
    for encoding in encodings:
        try:
            # 尝试多种编码和分隔符读取
            # 首先尝试 tab 分隔符
            temp_df = pd.read_csv(file_path, sep='\t', encoding=encoding)
            if all(col in temp_df.columns for col in required_cols):
                df = temp_df
                break
            
            # 如果 tab 不行，尝试默认逗号
            temp_df = pd.read_csv(file_path, sep=',', encoding=encoding)
            if all(col in temp_df.columns for col in required_cols):
                df = temp_df
                break
        except Exception:
            continue
    
    if df is None:
        st.error(f"无法正确读取文件或缺少必要列 {required_cols}，请检查文件内容。")
        return None
    
    # 过滤客户级别，只关注 V1, V2, V3
    df = df[df['客户级别'].isin(['V1', 'V2', 'V3'])]
    
    # 清理医院编码（处理 ="0060029527" 这种 Excel 格式）
    df['医院编码'] = df['医院编码'].astype(str).str.replace('="', '').str.replace('"', '')
    
    # 核心去重逻辑：按 套餐 + 客户级别 + 医院编码/名称 进行去重
    # 因为一个医院可能在同一个套餐下有多行数据（不同项目/月份），这里统计的是“有多少家医院拥有该套餐”
    df_unique = df.drop_duplicates(subset=['套餐', '客户级别', '医院编码', '医院名称'])
    
    return df_unique

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
        "柱状图显示模式",
        options=["绝对数值", "100% 占比 (分布情况)"],
        index=0
    )
    
    use_log_scale = st.sidebar.checkbox("使用对数 Y 轴 (改善小数值可见度)", value=False)
    
    filtered_df = df[
        (df['客户级别'].isin(selected_levels)) & 
        (df['套餐'].isin(selected_packages))
    ]
    
    # 数据汇总：统计唯一医院数量
    summary = filtered_df.groupby(['客户级别', '套餐']).agg({
        '医院编码': 'count'
    }).reset_index()
    summary.columns = ['客户级别', '套餐', '客户数量']
    
    # 布局：指标卡
    total_customers = filtered_df['医院编码'].nunique()
    st.sidebar.metric("当前筛选下的总客户数", total_customers)

    st.sidebar.markdown("---")

    # 布局：图表展示
    col1, col2 = st.columns([1.2, 0.8])
    
    with col1:
        st.subheader("📌 套餐覆盖客户数")
        
        # 处理 100% 占比
        if bar_mode == "100% 占比 (分布情况)":
            # 计算各级别总数用于百分比
            level_sums = summary.groupby('客户级别')['客户数量'].transform('sum')
            summary['占比'] = (summary['客户数量'] / level_sums * 100).round(1)
            
            fig_bar = px.bar(
                summary, 
                x="客户级别", 
                y="占比", 
                color="套餐",
                title="各级别客户的套餐分布 (100% 堆叠占比)",
                barmode="relative", # Plotly 100% 推荐方式
                text=summary['占比'].apply(lambda x: f"{x}%"),
                template="plotly_white",
                height=500
            )
            fig_bar.update_layout(yaxis_title="占比 (%)", yaxis_range=[0, 100])
        else:
            fig_bar = px.bar(
                summary, 
                x="客户级别", 
                y="客户数量", 
                color="套餐",
                title="各级别客户的套餐分布 (绝对数量统计)",
                barmode="stack",
                text_auto=True,
                template="plotly_white",
                height=500
            )
            fig_bar.update_layout(yaxis_title="客户(医院)数量")
            
            if use_log_scale:
                fig_bar.update_layout(yaxis_type="log")

        fig_bar.update_layout(
            xaxis_title="客户级别",
            legend_title="套餐",
            uniformtext_mode='hide', 
            uniformtext_minsize=8
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("📌 客户级别占比 (饼图)")
        # 按医院去重后统计各级别
        level_dist = filtered_df.drop_duplicates('医院编码')['客户级别'].value_counts().reset_index()
        level_dist.columns = ['客户级别', '医院数']
        fig_pie = px.pie(
            level_dist, 
            values='医院数', 
            names='客户级别', 
            title="各级别客户(医院)分布比例",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    
    # 详细的热力图分布
    st.subheader("🔍 套餐在各级别的覆盖率矩阵")
    pivot_df = summary.pivot(index='套餐', columns='客户级别', values='客户数量').fillna(0)
    
    fig_heatmap = px.imshow(
        pivot_df,
        text_auto=True,
        aspect="auto",
        labels=dict(x="客户级别", y="套餐", color="客户数"),
        color_continuous_scale='Blues',
        title="套餐分布热力图 (数值为客户数)"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # 客户清单查看
    st.markdown("---")
    st.subheader("📋 客户明细清单")
    st.info("您可以通过侧边栏筛选特定的级别 and 套餐，下方表格将展示对应的医院明细。")
    
    # 整理展示用的清单列
    display_df = filtered_df[['医院编码', '医院名称', '客户级别', '套餐']].sort_values(['客户级别', '套餐'])
    
    # 搜索框
    search_query = st.text_input("🔍 搜索医院名称", "")
    if search_query:
        display_df = display_df[display_df['医院名称'].str.contains(search_query, na=False)]
    
    st.dataframe(
        display_df, 
        use_container_width=True,
        column_config={
            "医院编码": st.column_config.TextColumn("医院编码"),
            "医院名称": st.column_config.TextColumn("医院名称"),
            "客户级别": st.column_config.TextColumn("客户级别"),
            "套餐": st.column_config.TextColumn("套餐")
        }
    )
    
    # 导出按钮
    csv = display_df.to_csv(index=False).encode('utf_8_sig')
    st.download_button(
        label="📥 导出当前筛选的客户清单",
        data=csv,
        file_name="客户清单_导出.csv",
        mime="text/csv",
    )

else:
    st.info("等待数据正确加载...")
