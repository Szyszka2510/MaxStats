# Custom CSS — ukrycie menu Streamlit, stopki (korony) oraz stylizacja
st.markdown("""
<style>
    /* Ukrycie menu w prawym górnym rogu oraz stopki na dole */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    div[data-testid="stMetric"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 15px;
    }
    div[data-testid="stMetric"]:hover {
        border: 1px solid #38BDF8;
    }
    .pos-box {
        background-color: #1E293B;
        border: 1px solid #0284C7;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
    }
    /* Stylizacja czystej tabeli HTML */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #1E293B;
        border-radius: 8px;
        overflow: hidden;
        margin-top: 10px;
    }
    .custom-table th, .custom-table td {
        padding: 10px 12px;
        text-align: center;
        border-bottom: 1px solid #334155;
    }
    .custom-table th {
        background-color: #0F172A;
        color: #38BDF8;
        font-weight: bold;
    }
    .custom-table tr:hover {
        background-color: #334155;
    }
</style>
""", unsafe_allow_html=True)
