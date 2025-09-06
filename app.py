import streamlit as st
from utils import fetch_imap_emails, analyze_email, generate_reply, parse_csv_emails
import time
from datetime import datetime

st.set_page_config(page_title='AI Email Assistant', layout='wide')

if 'emails' not in st.session_state:
    st.session_state['emails'] = []

st.title("AI-Powered Email Assistant")
st.markdown(
    "Upload CSV or fetch Gmail emails. Filter emails by subject keywords, analyze urgency & sentiment, extract info, and auto-generate draft replies."
)

# --- Sidebar ---
st.sidebar.markdown("### Gmail Fetch")
gmail_user = st.sidebar.text_input("Gmail Address")
gmail_pass = st.sidebar.text_input("App Password", type="password")
limit = st.sidebar.slider("Number of emails", 10, 200, 50)
if st.sidebar.button("Fetch from Gmail"):
    if gmail_user and gmail_pass:
        results = fetch_imap_emails("imap.gmail.com", gmail_user, gmail_pass, "INBOX", limit=limit)
        for i, r in enumerate(results):
            analysis = analyze_email(r['subject'], r['body'], r['from_email'])
            st.session_state['emails'].append({
                'id': int(time.time()*1000)+i,
                'from_email': r['from_email'],
                'subject': r['subject'],
                'body': r['body'],
                'received_at': r.get('received_at', time.time()),
                'analysis': analysis
            })
        st.sidebar.success(f"Fetched {len(results)} emails")
    else:
        st.sidebar.error("Enter Gmail address and App Password")

st.sidebar.markdown("### Filter by Subject Keywords")
keyword_options = ["Support", "Query", "Request", "Help"]
selected_keywords = st.sidebar.multiselect("", keyword_options, default=keyword_options)

# --- CSV Upload ---
st.subheader("Upload CSV")
uploaded_file = st.file_uploader("Upload CSV with emails", type=["csv"])
if uploaded_file:
    rows = parse_csv_emails(uploaded_file)
    for i, r in enumerate(rows):
        analysis = analyze_email(r['subject'], r['body'], r['from_email'])
        st.session_state['emails'].append({
            'id': int(time.time()*1000)+i,
            'from_email': r['from_email'],
            'subject': r['subject'],
            'body': r['body'],
            'received_at': r['received_at'],
            'analysis': analysis
        })
    st.success(f"Added {len(rows)} emails from CSV.")

# --- Filter emails ---
filtered_emails = [
    e for e in st.session_state['emails']
    if any(k.lower() in e['subject'].lower() for k in selected_keywords)
]
filtered_emails = sorted(filtered_emails, key=lambda e: -e['analysis']['urgency'])

# --- Display emails table ---
if filtered_emails:
    st.subheader(f"Filtered Emails ({len(filtered_emails)}) — Urgent first")
    MAX_BODY = 32
    MAX_SUBJECT = 25
    MAX_DATE = 10
    table_data = []
    for e in filtered_emails:
        priority = "Urgent" if e['analysis']['urgency']>=0.6 else "Not urgent"
        ts = e['received_at']
        if isinstance(ts,str):
            try: ts = datetime.strptime(ts,"%Y-%m-%d %H:%M:%S").timestamp()
            except: ts = time.time()
        body_text = e['body'].replace("\n"," ")
        if len(body_text) > MAX_BODY: body_text = body_text[:MAX_BODY]+"..."
        subject_text = e['subject'].replace("\n"," ")
        if len(subject_text) > MAX_SUBJECT: subject_text = subject_text[:MAX_SUBJECT]+"..."
        sent_date = time.strftime('%Y-%m-%d', time.localtime(ts))
        if len(sent_date) > MAX_DATE: sent_date = sent_date[:MAX_DATE]+"..."
        table_data.append({
            "Sender": e['from_email'],
            "Subject": subject_text,
            "Body": body_text,
            "Sent Date": sent_date,
            "Priority": priority,
            "Sentiment": e['analysis']['sentiment_label']
        })
    st.table(table_data)

    # --- Draft replies & info in transparent blue boxes ---
    st.subheader("Auto-Generated Draft Replies & Extracted Info")
    for e in filtered_emails:
        ts = e['received_at']
        if isinstance(ts,str):
            try: ts = datetime.strptime(ts,"%Y-%m-%d %H:%M:%S").timestamp()
            except: ts = time.time()
        sent_date = time.strftime('%Y-%m-%d', time.localtime(ts))
        contacts = e['analysis']['contacts']
        requests = e['analysis']['requests']

        email_html = f"""
        <div style="
            border:2px solid #BFA5D4;
            border-radius:10px;
            padding:15px;
            margin-bottom:15px;
            background-color:rgba(191,165,212,0.1);
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            line-height:1.5;
        ">
            <b>Sender:</b> {e['from_email']}<br>
            <b>Subject:</b> {e['subject']}<br>
            <b>Body:</b> {e['body']}<br>
            <b>Sent Date:</b> {sent_date}<br>
            <b>Priority:</b> {'Urgent' if e['analysis']['urgency']>=0.6 else 'Not urgent'}<br>
            <b>Contacts Extracted:</b> Emails: {e['from_email']}, Phones: {contacts['phones']}<br>
            <b>Customer Requests / Requirements:</b> {requests}<br>
            <b>Sentiment:</b> {e['analysis']['sentiment_label']} (Pos:{e['analysis']['pos_count']} Neg:{e['analysis']['neg_count']})<br>
            <div style="
                border:1px solid #D2B48C;
                border-radius:8px;
                padding-left:35px;
                margin:15px 195px 5px 20px;
                background-color:rgba(210,180,140,0.1);
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                line-height:1.6;
                font-family:inherit;
                font-size:0.95rem;
                white-space:pre-wrap;
            ">
                <b>Draft Reply:</b> {generate_reply(e)}
            </div>
        </div>
        """
        st.markdown(email_html, unsafe_allow_html=True)
else:
    st.info("No emails match the selected subject keywords.")