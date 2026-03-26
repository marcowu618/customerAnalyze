import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 设置页面配置
st.set_page_config(page_title="五大套餐分布图", layout="wide")

# 标题
st.title("📊 五大套餐在 V1/V2/V3 客户中的分布情况")
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
            temp_df = pd.read_csv(file_path, sep='\t', encoding=encoding)
            if all(col in temp_df.columns for col in required_cols):
                df = temp_df
                break
            temp_df = pd.read_csv(file_path, sep=',', encoding=encoding)
            if all(col in temp_df.columns for col in required_cols):
                df = temp_df
                break
        except Exception:
            continue
    
    if df is None:
        st.error(f"无法正确读取文件或缺少必要列 {required_cols}")
        return None
    
    # 筛选 V1, V2, V3 客户
    df = df[df['客户级别'].isin(['V1', 'V2', 'V3'])]
    
    # 筛选特定的五个套餐
    target_packages = ["传染病", "性激素", "甲功", "肿标", "心标"]
    df = df[df['套餐'].isin(target_packages)]
    
    # 清理医院编码
    df['医院编码'] = df['医院编码'].astype(str).str.replace('="', '').str.replace('"', '')
    
    # 按 套餐 + 客户级别 + 医院名称 去重
    df_unique = df.drop_duplicates(subset=['套餐', '客户级别', '医院编码', '医院名称'])
    
    return df_unique

df = load_data()

if df is not None:
    # 统计数据
    summary = df.groupby(['套餐', '客户级别']).agg({
        '医院编码': 'count'
    }).reset_index()
    summary.columns = ['套餐', '客户级别', '客户数量']
    
    # 计算各级别客户在各套餐中的占比
    # 这里的占比是指：在某个客户级别下，各个套餐的分布比例
    level_totals = summary.groupby('客户级别')['客户数量'].transform('sum')
    summary['占比'] = (summary['客户数量'] / level_totals * 100).round(1)
    
    # 创建堆叠柱状图 (Stacked Bar Chart)
    fig = px.bar(
        summary,
        x="套餐",
        y="客户数量",
        color="客户级别",
        barmode="stack", # 改为堆叠模式
        text="客户数量", # 直接显示数量
        title="五大套餐在不同级别客户中的开展家数分布 (堆叠图)",
        template="plotly_white",
        height=600,
        category_orders={
            "套餐": ["传染病", "性激素", "甲功", "肿标", "心标"],
            "客户级别": ["V3", "V2", "V1"] # 自下而上堆叠顺序
        },
        color_discrete_map={
            "V1": "#1f77b4",
            "V2": "#ff7f0e",
            "V3": "#2ca02c"
        }
    )
    
    # 优化图表样式：在柱子内部显示标签 (增加字体大小)
    fig.update_traces(
        texttemplate='%{text}',
        textposition='inside',
        textfont=dict(size=16, color="white") # 增加柱内数字大小
    )
    
    # 计算每个套餐的总数，并在柱子顶部显示总家数 (增加字体大小)
    total_summary = summary.groupby('套餐')['客户数量'].sum().reset_index()
    for i, row in total_summary.iterrows():
        fig.add_annotation(
            x=row['套餐'],
            y=row['客户数量'],
            text=f"{int(row['客户数量'])}",
            showarrow=False,
            yshift=15,
            font=dict(size=18, color="black", family="Arial Black") # 增加顶部总数大小
        )
    
    fig.update_layout(
        title=dict(
            text="五大套餐在不同级别客户中的开展家数分布 (堆叠图)",
            font=dict(size=24) # 增加标题大小
        ),
        xaxis=dict(
            title=dict(text="套餐类型", font=dict(size=20)), # 增加X轴标题大小
            tickfont=dict(size=16) # 增加X轴刻度文字大小
        ),
        yaxis=dict(
            title=dict(text="开展家数 (医院数量)", font=dict(size=20)), # 增加Y轴标题大小
            tickfont=dict(size=16) # 增加Y轴刻度文字大小
        ),
        legend=dict(
            title=dict(text="客户级别", font=dict(size=18)), # 增加图例标题大小
            font=dict(size=16) # 增加图例文字大小
        ),
        uniformtext_mode='hide',
        uniformtext_minsize=12
    )
    
    # 在 Streamlit 中显示
    st.plotly_chart(fig, use_container_width=True)
    
    # 数据明细表格
    with st.expander("查看统计数据明细"):
        st.dataframe(summary[['套餐', '客户级别', '客户数量', '占比']], use_container_width=True)
else:
    st.info("数据加载失败，请检查 CSV 文件。")
