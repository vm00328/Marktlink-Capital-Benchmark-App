import os
import requests
from io import BytesIO
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import plotly.graph_objects as go

AUTHORIZED_EMAILS = st.secrets["AUTHORIZED_EMAILS"]

def authenticate():
    st.sidebar.title("Login")
    email = st.sidebar.text_input("Enter your email")
    if st.sidebar.button("Submit"):
        if email in AUTHORIZED_EMAILS:
            st.session_state['authenticated'] = True
            st.sidebar.success("Authentication successful")
        else:
            st.sidebar.error("Unauthorized email")
            st.session_state['authenticated'] = False

# Initialize authentication state
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# Authentication block
if not st.session_state['authenticated']:
    authenticate()
    if not st.session_state['authenticated']:
        st.stop()  # Stop the app if not authenticated

st.set_page_config(layout = "wide")

excel_file_url = st.secrets["EXCEL_FILE_URL"]

@st.cache_data
def load_fund_data(url):
    response = requests.get(url)
    fund_data = pd.read_excel(BytesIO(response.content), engine = "openpyxl")
    return fund_data

logo_path = os.path.join(os.path.dirname(__file__), "static/ML_logo.png")
st.sidebar.image(logo_path, use_container_width = True)

# UI components
st.title("Fund Performance Benchmarking")
st.sidebar.title("Fund Details")
st.sidebar.info("Compare against industry benchmarks.")

# Input fields for fund details
with st.sidebar.expander("🎯 Fund Details", expanded = True):
    fund_name = st.text_input("Fund Name")
    asset_class = st.selectbox("Asset Class", options = ["Venture Capital (all stages)", "Private Equity (Buy-out)"])
    vintage = st.selectbox("Vintage", options = [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024])
    geography = st.selectbox("Fund Manager Location", options = ["Europe", "US", "Europe & US"])
    
    if asset_class == "Venture Capital (all stages)":
        fund_size = st.selectbox("Fund Size ($mn)", options = ["$10mn-$50mn", "$50mn-$100mn", "$100mn-$200mn", "$200mn-$500mn", "$500mn+", "Agnostic"])
    else:
        fund_size = st.selectbox("Fund Size ($mn)", options = ["<$1bn", "$1bn-$3bn", "$3bn-$5bn", "$5bn-$10bn", ">$10bn", "Agnostic"])

# Input fields for performance metrics
with st.sidebar.expander("📊 Performance Metrics", expanded = True):
    net_irr = st.number_input("Net IRR (%)", step = 0.01)
    net_tvpi = st.number_input("Net TVPI (X)", min_value = 0.0, step = 0.01)
    net_dpi = st.number_input("Net DPI (X)", min_value = 0.0, step = 0.01)

if st.sidebar.button("Submit"):

    fund_data = load_fund_data(excel_file_url)

    if not fund_name:
        st.error("Please provide a fund name.")
        st.stop()

    # Asset Class Selection
    asset_class_mapping = {
        "Venture Capital (all stages)" : ["Venture Capital"],
        "Private Equity (Buy-out)" : ["Private Equity"]
    }
    selected_asset_class = asset_class_mapping.get(asset_class)

    # Geography Selection
    geography_mapping = {
        "Europe": ["Europe"],
        "US": ["North America"],
        "Europe & US": ["Europe", "North America"]
    }
    selected_regions = geography_mapping.get(geography)

    # Fund Size Selection
    fund_size_mapping = {
        "Venture Capital (all stages)": {
            "$10mn-$50mn": (10, 50),
            "$50mn-$100mn": (50, 100),
            "$100mn-$200mn": (100, 200),
            "$200mn-$500mn": (200, 500),
            "$500mn+": (500, float('inf')),
            "Agnostic" : (0, float('inf'))
        },

        "Private Equity (Buy-out)": {
            "<$1bn": (0, 1000),
            "$1bn-$3bn": (1000, 3000),
            "$3bn-$5bn": (3000, 5000),
            "$5bn-$10bn": (5000, 10000),
            ">$10bn": (10000, float('inf')),
            "Agnostic" : (0, float('inf'))
        }
    }
    selected_size_range = fund_size_mapping[asset_class][fund_size] # the numeric range for the selected fund size

    # Filter data based on vintage and fund manager location
    filtered_data = fund_data[
        (fund_data['ASSET CLASS'].isin(selected_asset_class)) &
        (fund_data['VINTAGE'] == vintage) &
        (fund_data['FM REGION'].isin(selected_regions)) &
        (fund_data['FUND SIZE (USD MN)'].between(selected_size_range[0], selected_size_range[1]))
    ]

    num_funds = len(filtered_data)
    if num_funds == 0:
        st.warning("No funds match the selected filters. Please adjust your input.")
    else:
        if vintage in [2022, 2023, 2024]:
            metric_names = ["NET TVPI (X)", "NET DPI (X)"] # Omit IRR since it is not meaningful within the first 3 years since inception
        else:
            metric_names = ["NET IRR (%)", "NET TVPI (X)", "NET DPI (X)"]

        metrics = {
            "NET IRR (%)": net_irr,
            "NET TVPI (X)": net_tvpi,
            "NET DPI (X)": net_dpi
        }
        metrics = {k: v for k, v in metrics.items() if k in metric_names}  # Filter by metric_names

        # Ensure metrics are provided
        required_metrics = {k: v for k, v in metrics.items() if k in metric_names}
        missing_metrics = [k for k, v in required_metrics.items() if v is None or v == 0]

        if missing_metrics:
            st.error(f"Please provide values for the following metrics: {', '.join(missing_metrics)}")
            st.stop()

        # Compute benchmarks dynamically
        benchmark_values = {}

        for metric in metric_names:
            top_decile = filtered_data[metric].quantile(0.9)
            top_quartile = filtered_data[metric].quantile(0.75)
            average = filtered_data[metric].mean()
            benchmark_values[metric] = {
                "Top Decile (90%)": top_decile,
                "Top Quartile (75%)": top_quartile,
                "Average": average
            }

        # Bar charts for each metric with dynamic columns
        if not metrics:
            st.warning("No performance metrics to display.")
            st.stop()

        # Bar charts for each metric with dynamic columns
        columns = st.columns(len(metrics))

        # Define your custom colors
        primary_colors = {
            "Top Decile (90%)": "#003165",   # Dark Blue
            "Top Quartile (75%)": "#0076C8", # Bright Blue
            "Average": "#F2F2F2",            # Light Gray
            fund_name: "#FF8300"             # Accent Orange for user's fund
        }

        for i, (metric_name, user_value) in enumerate(metrics.items()):
            benchmarks = benchmark_values[metric_name]
            categories = ["Top Decile (90%)", "Top Quartile (75%)", "Average", fund_name]

            values = [
                benchmarks["Top Decile (90%)"],
                benchmarks["Top Quartile (75%)"],
                benchmarks["Average"],
                user_value
            ]

            colors = [
                primary_colors["Top Decile (90%)"],
                primary_colors["Top Quartile (75%)"],
                primary_colors["Average"],
                primary_colors[fund_name]
            ]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x = categories,
                y = values,
                marker_color = colors,
                text = [f"{v:.2f}" for v in values],
                textposition = 'auto',
            ))

            fig.update_layout(
                title = {
                    'text': f"{metric_name} Benchmark",
                    'y': 0.9,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top'
                },

                xaxis_title = "Categories",
                yaxis_title = metric_name,
                font = dict(family = "Arial, sans-serif", size = 14, color = "#003165"),
                plot_bgcolor = 'white',
                bargap = 0.2,
                xaxis = dict(showgrid = False),
                yaxis = dict(showgrid = True, gridcolor = '#F2F2F2')
            )

            columns[i].plotly_chart(fig, use_container_width = True) # Assigning each chart to a column

        # Footer Section with dynamic data insights
        footer_text = f"""**Asset Class:** {asset_class} | **Vintage Year:** {vintage} | **Sector:** Sector-Agnostic | **Geography:** {', '.join(selected_regions)} | **Number of Funds:** {num_funds}"""
        st.markdown("---")
        st.markdown(footer_text)