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
    
    # 计算每个套餐的总数，并按总数从高到低排序
    total_summary = summary.groupby('套餐')['客户数量'].sum().reset_index()
    total_summary = total_summary.sort_values(by='客户数量', ascending=False)
    sorted_packages = total_summary['套餐'].tolist()

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
        height=700, # 稍微增加高度以适应大字体
        category_orders={
            "套餐": sorted_packages, # 按总数从高到低排序
            "客户级别": ["V3", "V2", "V1"] # 自下而上堆叠顺序
        },
        color_discrete_map={
            "V1": "#1f77b4",
            "V2": "#ff7f0e",
            "V3": "#2ca02c"
        }
    )
    
    # 优化图表样式：在柱子内部显示标签 (再次增加字体大小，并调细柱子)
    fig.update_traces(
        texttemplate='%{text}',
        textposition='inside',
        textfont=dict(size=20, color="white"), # 柱内数字增大到 20
        width=0.4 # 调细柱子，默认是 0.8 左右，设置为 0.4 显著变细
    )
    
    # 在柱子顶部显示总家数 (再次增加字体大小)
    for i, row in total_summary.iterrows():
        fig.add_annotation(
            x=row['套餐'],
            y=row['客户数量'],
            text=f"{int(row['客户数量'])}",
            showarrow=False,
            yshift=20, # 增加向上偏移量，避免重叠
            font=dict(size=22, color="black", family="Arial Black") # 顶部总数增大到 22
        )
    
    fig.update_layout(
        title=dict(
            text="五大套餐在不同级别客户中的开展家数分布 (堆叠图)",
            font=dict(size=28) # 标题增大到 28
        ),
        xaxis=dict(
            title=dict(text="套餐类型", font=dict(size=24)), # X轴标题增大到 24
            tickfont=dict(size=20) # X轴刻度文字增大到 20
        ),
        yaxis=dict(
            title=dict(text="开展家数 (医院数量)", font=dict(size=24)), # Y轴标题增大到 24
            tickfont=dict(size=20) # Y轴刻度文字增大到 20
        ),
        legend=dict(
            title=dict(text="客户级别", font=dict(size=22)), # 图例标题增大到 22
            font=dict(size=20) # 图例文字增大到 20
        ),
        bargap=0.5, # 增加柱子之间的间距，使柱子看起来更细
        uniformtext_mode='hide',
        uniformtext_minsize=14
    )
    
    # 在 Streamlit 中显示
    st.plotly_chart(fig, use_container_width=True)
    
    # 数据明细表格
    with st.expander("查看统计数据明细"):
        st.dataframe(summary[['套餐', '客户级别', '客户数量', '占比']], use_container_width=True)
else:
    st.info("数据加载失败，请检查 CSV 文件。")
