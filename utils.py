import re
import imaplib, email, time
from email.header import decode_header
import pandas as pd

SUPPORT_KEYWORDS = ['support','query','request','help']
URGENT_KEYWORDS = ['urgent','immediately','critical','cannot access','asap','escalate']
NEGATIVE_WORDS = ['not','never','cancel','wrong','late','delay','missing','unhappy','angry','problem','issue','frustrat']
POSITIVE_WORDS = ['thank','great','good','happy','love','excellent','appreciate']

# --- IMAP email fetching ---
def _decode_header(h):
    parts = decode_header(h)
    result = ''
    for bytes_, enc in parts:
        if isinstance(bytes_, bytes):
            try:
                result += bytes_.decode(enc or 'utf-8', errors='ignore')
            except:
                result += bytes_.decode('utf-8', errors='ignore')
        else:
            result += bytes_
    return result

def _get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get('Content-Disposition') or '')
            if ct == 'text/plain' and 'attachment' not in disp:
                return part.get_payload(decode=True).decode(errors='ignore')
        return ''
    else:
        return msg.get_payload(decode=True).decode(errors='ignore') if msg.get_payload(decode=True) else ''

def parse_msg(msg_bytes):
    msg = email.message_from_bytes(msg_bytes)
    subject = msg.get('Subject') or ''
    subject = _decode_header(subject)
    from_ = msg.get('From') or ''
    date_ = msg.get('Date') or ''
    try:
        parsed_date = email.utils.parsedate_to_datetime(date_)
        ts = parsed_date.timestamp()
    except:
        ts = time.time()
    body = _get_body(msg) or ''
    return {'from_email': from_, 'subject': subject, 'body': body, 'received_at': ts}

def fetch_imap_emails(host, user, password, mailbox='INBOX', limit=50):
    res = []
    try:
        M = imaplib.IMAP4_SSL(host)
        M.login(user, password)
        M.select(mailbox)
        typ, data = M.search(None, 'ALL')
        if typ != 'OK':
            return res
        ids = data[0].split()
        for num in ids[-limit:]:
            typ, msg_data = M.fetch(num, '(RFC822)')
            if typ != 'OK':
                continue
            for resp_part in msg_data:
                if isinstance(resp_part, tuple):
                    parsed = parse_msg(resp_part[1])
                    subj = parsed['subject'].lower()
                    if any(k in subj for k in SUPPORT_KEYWORDS):
                        res.append(parsed)
        M.logout()
    except Exception as e:
        print('IMAP fetch error:', e)
    return res

# --- CSV parsing ---
def parse_csv_emails(uploaded_file):
    df = pd.read_csv(uploaded_file)
    rows = []
    for _, row in df.iterrows():
        rows.append({
            'from_email': row.get('sender', ''),
            'subject': row.get('subject', ''),
            'body': row.get('body', ''),
            'received_at': row.get('sent_date', time.time())
        })
    return rows

# --- Information extraction ---
def extract_contacts(body):
    phones = re.findall(r'\+?\d[\d\s\-]{7,}\d', body)
    emails = re.findall(r'[\w\.-]+@[\w\.-]+', body)
    return {'phones': phones, 'emails': emails}

def extract_requests(body):
    # Placeholder: capture sentences with request/help keywords
    sentences = re.split(r'[.!?]', body)
    requests = [s.strip() for s in sentences if any(k in s.lower() for k in ['need','require','help','request','issue','problem','cannot'])]
    return requests

def detect_sentiment(body):
    body_lower = body.lower()
    neg = sum(1 for w in NEGATIVE_WORDS if w in body_lower)
    pos = sum(1 for w in POSITIVE_WORDS if w in body_lower)
    score = pos - neg
    if score > 0:
        label = "Positive"
    elif score < 0:
        label = "Negative"
    else:
        label = "Neutral"
    return {'score': score, 'label': label, 'pos_count': pos, 'neg_count': neg}

def detect_urgency(subject, body):
    text = (subject + " " + body).lower()
    score = 0.0
    for kw in URGENT_KEYWORDS:
        if kw in text:
            score += 0.5
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)
    score += min(0.5, 0.1 * neg_count)
    return min(score, 1.0)

# --- Draft reply generator ---
def generate_reply(email):
    sender_name = email.get('from_email','').split('@')[0].title()
    body = email.get('body','')
    analysis = email.get('analysis',{})
    sentiment = analysis.get('sentiment_label','Neutral')
    priority = "Urgent" if analysis.get('urgency',0) >= 0.6 else "Not urgent"
    frustrated = sentiment=='Negative' or analysis.get('urgency',0) >=0.6

    # detect product mentions
    products = re.findall(r'product\s*[:\-]?\s*(\w+)', body, re.IGNORECASE)
    product_text = f" regarding the {', '.join(products)}" if products else ""

    reply = f"Hi {sender_name},\n\n"
    if frustrated:
        reply += "We understand your frustration and apologize for any inconvenience caused.\n"
    reply += f"Thank you for contacting us{product_text}. Our team is reviewing your request and will respond promptly.\n\n"
    reply += "— Support Team"
    return reply

# --- Email analysis ---
def analyze_email(subject, body, from_email):
    info = extract_contacts(body)
    requests = extract_requests(body)
    sentiment = detect_sentiment(body)
    urgency = detect_urgency(subject, body)
    return {
        'contacts': info,
        'requests': requests,
        'sentiment_label': sentiment['label'],
        'sentiment_score': sentiment['score'],
        'pos_count': sentiment['pos_count'],
        'neg_count': sentiment['neg_count'],
        'urgency': urgency,
        'raw_text': body
    }
