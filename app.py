import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta

# Set up the page
st.set_page_config(layout="wide", page_title="Ramadan 2024 Analysis")

# Title and description
st.title("Ramadan 2024 TPS and Pod Analysis")
st.markdown("""
This analysis shows TPS and pod counts for each service during Ramadan 2024, with configurable time windows and aggregation methods.
Use the sidebar controls to customize the visualization.
""")

# Load the data
df = pd.read_csv('ramadan_hourly.csv')
df['hour'] = pd.to_datetime(df['hour'])

# Get time range
min_date = df['hour'].min()
max_date = df['hour'].max()

# Sidebar controls
with st.sidebar:
    st.header("Visualization Controls")
    
    # Time window selection
    st.subheader("Time Window")
    date_range = st.date_input(
        "Select Date Range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date()
    )
    
    # Time aggregation
    st.subheader("Time Aggregation")
    time_window = st.selectbox(
        "Group Data By",
        ["Hour", "Day", "Week"],
        index=0
    )
    
    # Aggregation method
    st.subheader("Aggregation Method")
    agg_method = st.selectbox(
        "Calculate",
        ["Maximum", "Average", "Minimum"],
        index=0
    )
    
    # Metric selection
    st.subheader("Metrics to Show")
    show_metrics = st.multiselect(
        "Select Metrics",
        ["TPS", "Pods"],
        default=["TPS", "Pods"]
    )
    
    # Service selection
    st.subheader("Service Selection")
    view_mode = st.radio(
        "View Mode",
        ["All Services", "Select Services"]
    )
    
    if view_mode == "Select Services":
        services = sorted(df['service'].unique())
        selected_services = st.multiselect(
            "Select Services",
            services,
            default=services
        )
    else:
        selected_services = sorted(df['service'].unique())

# Filter by date range
start_date = pd.Timestamp(date_range[0])
end_date = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
df_filtered = df[(df['hour'] >= start_date) & (df['hour'] <= end_date)]

# Filter by selected services
df_filtered = df_filtered[df_filtered['service'].isin(selected_services)]

# Aggregate by selected time window
if time_window == "Day":
    df_filtered['group'] = df_filtered['hour'].dt.floor('D')
elif time_window == "Week":
    df_filtered['group'] = df_filtered['hour'].dt.floor('W')
else:
    df_filtered['group'] = df_filtered['hour']

# Apply selected aggregation method
agg_map = {
    "Maximum": "max",
    "Average": "mean",
    "Minimum": "min"
}
agg_method_str = agg_map[agg_method]

df_agg = df_filtered.groupby(['group', 'service']).agg({
    'tps': agg_method_str,
    'pods': agg_method_str
}).reset_index()

# Create figure with secondary y-axis if needed
use_secondary_y = len(show_metrics) > 1
fig = make_subplots(specs=[[{"secondary_y": use_secondary_y}]])

# Add traces for each service
for service in selected_services:
    service_data = df_agg[df_agg['service'] == service]
    
    # Add TPS line if selected
    if "TPS" in show_metrics:
        fig.add_trace(
            go.Scatter(
                x=service_data['group'],
                y=service_data['tps'],
                name=f"{service} (TPS)",
                line=dict(width=2),
            ),
            secondary_y=False,
        )
    
    # Add Pods line if selected
    if "Pods" in show_metrics:
        fig.add_trace(
            go.Scatter(
                x=service_data['group'],
                y=service_data['pods'],
                name=f"{service} (Pods)",
                line=dict(dash='dot', width=2),
            ),
            secondary_y=use_secondary_y,  # Only use secondary y if showing both metrics
        )

# Update layout
metrics_shown = " and ".join(show_metrics)
fig.update_layout(
    title=f"{agg_method} {metrics_shown} by {time_window}",
    height=700,
    hovermode="x unified",
    showlegend=True,
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=1.02
    )
)

# Set y-axes titles
if "TPS" in show_metrics:
    fig.update_yaxes(title_text="Transactions Per Second", secondary_y=False)
if "Pods" in show_metrics:
    y_axis = use_secondary_y if "TPS" in show_metrics else False
    fig.update_yaxes(title_text="Number of Pods", secondary_y=y_axis)
fig.update_xaxes(title_text="Time")

# Show the figure
st.plotly_chart(fig, use_container_width=True)

# Calculate statistics using the filtered and aggregated data
stats = []
for service in selected_services:
    service_data = df_agg[df_agg['service'] == service]
    stat_row = {"Service": service}
    
    if "TPS" in show_metrics:
        peak_tps = service_data['tps'].max()
        peak_tps_idx = service_data['tps'].idxmax()
        peak_tps_time = service_data.loc[peak_tps_idx, 'group']
        avg_tps = service_data['tps'].mean()
        stat_row.update({
            "Peak TPS": peak_tps,  # Store as number
            "Peak TPS (Display)": f"{peak_tps:.1f}",  # For display only
            "Peak TPS Time": peak_tps_time.strftime('%Y-%m-%d %H:00'),
            "Avg TPS": avg_tps,  # Store as number
            "Avg TPS (Display)": f"{avg_tps:.1f}",  # For display only
        })
    
    if "Pods" in show_metrics:
        peak_pods = service_data['pods'].max()
        peak_pods_idx = service_data['pods'].idxmax()
        peak_pods_time = service_data.loc[peak_pods_idx, 'group']
        avg_pods = service_data['pods'].mean()
        stat_row.update({
            "Peak Pods": peak_pods,  # Store as number
            "Peak Pods (Display)": f"{peak_pods:.0f}",  # For display only
            "Peak Pods Time": peak_pods_time.strftime('%Y-%m-%d %H:00'),
            "Avg Pods": avg_pods,  # Store as number
            "Avg Pods (Display)": f"{avg_pods:.1f}",  # For display only
        })
    
    stats.append(stat_row)

# Create DataFrame and sort by numeric values
stats_df = pd.DataFrame(stats)

# Create display DataFrame with formatted strings
display_cols = ["Service"]
if "TPS" in show_metrics:
    display_cols.extend(["Peak TPS (Display)", "Peak TPS Time", "Avg TPS (Display)"])
if "Pods" in show_metrics:
    display_cols.extend(["Peak Pods (Display)", "Peak Pods Time", "Avg Pods (Display)"])

# Show statistics table with proper column names
if stats:
    st.header("Service Statistics")
    display_df = stats_df[display_cols].copy()
    # Rename columns to remove "(Display)" suffix
    display_df.columns = [col.replace(" (Display)", "") for col in display_df.columns]
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "Peak TPS": st.column_config.NumberColumn(format="%.1f"),
            "Avg TPS": st.column_config.NumberColumn(format="%.1f"),
            "Peak Pods": st.column_config.NumberColumn(format="%.0f"),
            "Avg Pods": st.column_config.NumberColumn(format="%.1f"),
        }
    )

# Create correlation plots if both metrics are selected and only one service
if "TPS" in show_metrics and "Pods" in show_metrics and len(selected_services) == 1:
    st.header("TPS vs Pods Correlation")
    
    service = selected_services[0]
    service_data = df_agg[df_agg['service'] == service]
    
    fig_corr = px.scatter(
        service_data,
        x='tps',
        y='pods',
        title=f"{service}: Pod Count vs TPS ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})",
        labels={'tps': 'Transactions Per Second', 'pods': 'Number of Pods'},
        trendline="lowess",  # Add a trend line
        trendline_color_override="red"
    )
    
    fig_corr.update_layout(height=400)
    st.plotly_chart(fig_corr, use_container_width=True)
    
    # Calculate correlation coefficient
    correlation = service_data['tps'].corr(service_data['pods'])
    st.markdown(f"Correlation coefficient: **{correlation:.3f}**")
elif "TPS" in show_metrics and "Pods" in show_metrics and len(selected_services) > 1:
    st.info("Select a single service to view its TPS vs Pods correlation analysis.")
