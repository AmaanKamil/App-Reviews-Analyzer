import os
import time
from datetime import datetime

import plotly.express as px
import streamlit as st

from llm_service import LLMService
from mailer import EmailDraft
from processor import ReviewProcessor
from scraper import scrape_reviews, DATA_FILE

st.set_page_config(page_title="Groww Review Insights", page_icon="📊", layout="wide")

WEEKS_TO_ANALYZE = 1
STALE_AFTER_HOURS = 12
SENTIMENT_COLORS = {"Positive": "#00b386", "Neutral": "#9aa0a6", "Negative": "#eb5b3c"}

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
[data-testid="stMetric"] {background: rgba(0,179,134,0.06); border: 1px solid rgba(0,179,134,0.25);
    border-radius: 12px; padding: 14px 18px;}
</style>
""", unsafe_allow_html=True)


def data_age_hours():
    if not os.path.exists(DATA_FILE):
        return None
    return (time.time() - os.path.getmtime(DATA_FILE)) / 3600


def refresh_reviews():
    """Scrapes fresh reviews. Returns an error message, or None on success."""
    try:
        scrape_reviews()
        return None
    except Exception as e:
        return str(e)


@st.cache_data(show_spinner=False)
def load_and_process_data(file_path, weeks, file_mtime):
    # file_mtime is only part of the cache key, so new scrapes invalidate the cache
    processor = ReviewProcessor(file_path)
    df = processor.load_data()
    if df is None:
        return None
    df = processor.filter_recent(weeks=weeks)
    if df is None or df.empty:
        return df
    df = processor.add_sentiment()
    try:
        df = processor.extract_themes_llm(LLMService())
    except Exception as e:
        print(f"Theme extraction skipped: {e}")
        df['Theme'] = "General / Uncategorized"
    return df


# Auto-refresh: a sleeping/restarted app starts from the old committed JSON, so
# scrape once per session whenever the file is missing or stale.
age = data_age_hours()
if (age is None or age > STALE_AFTER_HOURS) and not st.session_state.get('auto_refreshed'):
    st.session_state['auto_refreshed'] = True
    with st.spinner("Fetching the latest Play Store reviews..."):
        err = refresh_reviews()
    if err:
        st.toast(f"Couldn't fetch new reviews: {err}", icon="⚠️")

# Header
col_title, col_refresh = st.columns([5, 1], vertical_alignment="center")
with col_title:
    st.title("📊 Groww Review Insights")
    age = data_age_hours()
    if age is not None:
        updated = datetime.fromtimestamp(os.path.getmtime(DATA_FILE)).strftime('%d %b %Y, %H:%M')
        st.caption(f"Google Play Store reviews · last {WEEKS_TO_ANALYZE * 7} days · data updated {updated}")
with col_refresh:
    if st.button("🔄 Refresh data", width="stretch"):
        with st.spinner("Fetching latest reviews..."):
            err = refresh_reviews()
        if err:
            st.error(f"Refresh failed: {err}")
        else:
            st.session_state['weekly_note'] = None
            st.rerun()

if not os.getenv("OPENAI_API_KEY"):
    st.warning("OPENAI_API_KEY is not set — AI theme detection and reports are disabled.")

if not os.path.exists(DATA_FILE):
    st.error("No review data yet and the Play Store fetch failed. Try **Refresh data**.")
    st.stop()

with st.spinner("Analysing reviews and identifying themes with AI..."):
    df = load_and_process_data(DATA_FILE, WEEKS_TO_ANALYZE, os.path.getmtime(DATA_FILE))

if df is None or df.empty:
    st.warning("No reviews found for the last 7 days. Click **Refresh data** to fetch the latest.")
    st.stop()

date_from, date_to = df['Published'].min().date(), df['Published'].max().date()
neg_share = (df['Sentiment_Label'] == 'Negative').mean() * 100

m1, m2, m3, m4 = st.columns(4)
m1.metric("Reviews", f"{len(df):,}")
m2.metric("Avg. sentiment", f"{df['Sentiment_Score'].mean():+.2f}",
          help="TextBlob polarity from -1 (negative) to +1 (positive).")
if 'Rating' in df.columns and df['Rating'].notna().any():
    m3.metric("Avg. rating", f"{df['Rating'].mean():.1f} ★")
else:
    m3.metric("Negative share", f"{neg_share:.0f}%")
date_label = (f"{date_from.day}–{date_to:%d %b}" if date_from.month == date_to.month
              else f"{date_from:%d %b}–{date_to:%d %b}")
m4.metric("Date range", date_label)

tab_dash, tab_reviews, tab_report = st.tabs(["Dashboard", "Reviews", "Weekly report"])

with tab_dash:
    c1, c2 = st.columns([2, 3])
    with c1:
        with st.container(border=True):
            st.subheader("Sentiment")
            sent = df['Sentiment_Label'].value_counts().reindex(["Positive", "Neutral", "Negative"]).fillna(0)
            fig_sent = px.pie(names=sent.index, values=sent.values, hole=0.55,
                              color=sent.index, color_discrete_map=SENTIMENT_COLORS)
            fig_sent.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320,
                                   legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_sent, use_container_width=True)
    with c2:
        with st.container(border=True):
            st.subheader("Top themes")
            themes = (df.groupby('Theme')
                        .agg(Count=('Review', 'size'), Sentiment=('Sentiment_Score', 'mean'))
                        .sort_values('Count').reset_index())
            fig_theme = px.bar(themes, x='Count', y='Theme', orientation='h', color='Sentiment',
                               color_continuous_scale=["#eb5b3c", "#e8e8e8", "#00b386"],
                               range_color=(-0.5, 0.5))
            fig_theme.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320,
                                    yaxis_title=None, coloraxis_colorbar=dict(title="Sent."))
            st.plotly_chart(fig_theme, use_container_width=True)
            st.caption("Bar colour = average sentiment of the theme. "
                       "'General / Uncategorized' = reviews that matched no AI theme keywords.")

    with st.container(border=True):
        st.subheader("Daily volume")
        daily = (df.groupby([df['Published'].dt.date, 'Sentiment_Label']).size()
                   .reset_index(name='Reviews').rename(columns={'Published': 'Date'}))
        fig_daily = px.bar(daily, x='Date', y='Reviews', color='Sentiment_Label',
                           color_discrete_map=SENTIMENT_COLORS)
        fig_daily.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280,
                                legend_title=None, xaxis_title=None)
        st.plotly_chart(fig_daily, use_container_width=True)

with tab_reviews:
    f1, f2, f3 = st.columns([2, 2, 3])
    theme_filter = f1.multiselect("Theme", sorted(df['Theme'].unique()))
    sent_filter = f2.multiselect("Sentiment", ["Positive", "Neutral", "Negative"])
    search = f3.text_input("Search text")
    view = df
    if theme_filter:
        view = view[view['Theme'].isin(theme_filter)]
    if sent_filter:
        view = view[view['Sentiment_Label'].isin(sent_filter)]
    if search:
        view = view[view['Review'].str.contains(search, case=False, regex=False)]
    cols = [c for c in ['Published', 'Rating', 'Sentiment_Label', 'Theme', 'Review'] if c in view.columns]
    st.caption(f"{len(view):,} reviews")
    st.dataframe(
        view[cols].sort_values('Published', ascending=False),
        hide_index=True, width="stretch", height=520,
        column_config={
            "Published": st.column_config.DateColumn("Date", format="DD MMM"),
            "Sentiment_Label": "Sentiment",
            "Review": st.column_config.TextColumn("Review", width="large"),
        },
    )

with tab_report:
    if 'weekly_note' not in st.session_state:
        st.session_state['weekly_note'] = None

    if st.button("✨ Generate weekly report", type="primary"):
        with st.spinner("Asking the LLM for insights..."):
            try:
                st.session_state['weekly_note'] = LLMService().generate_weekly_report(df)
            except Exception as e:
                st.error(f"Could not generate report: {e}")

    weekly_note = st.session_state['weekly_note']
    if not weekly_note:
        st.info("Generate an AI summary of this week's top themes, user quotes and action ideas.")
    else:
        with st.container(border=True):
            st.markdown(weekly_note)

        mailer = EmailDraft()
        subject = f"Weekly App Review Insights - Groww - {date_from} to {date_to}"

        a1, a2, _ = st.columns([1, 1, 3])
        with a1:
            if st.button("📧 Send email", width="stretch"):
                with st.spinner("Sending email..."):
                    success, msg = mailer.send_email(
                        subject, weekly_note,
                        dashboard_url=os.getenv("DASHBOARD_URL", "http://localhost:8501"))
                (st.success if success else st.error)(msg)
        with a2:
            st.download_button("⬇️ Download .md", weekly_note, file_name="weekly_report.md",
                               width="stretch")
        with st.expander("Raw email draft"):
            st.code(mailer.create_draft(subject, weekly_note), language=None)
