import json
import os
from datetime import date
from pathlib import Path

import streamlit as st

from study_agent import create_study_plan, run_openai_agent


# --------------------------------------------------
# Page configuration and visual theme
# --------------------------------------------------
st.set_page_config(
    page_title="Study Plan AI Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

BANNER_PATH = Path(__file__).with_name("study_plan_ai_banner.png")

st.markdown(
    """
    <style>
    :root {
        --primary: #5b4bdb;
        --primary-dark: #33258c;
        --ink: #18234b;
        --muted: #61708f;
        --surface: #ffffff;
        --line: #e3e8fb;
    }
    .stApp {
        background: linear-gradient(145deg, #f7f8ff 0%, #f0f5ff 50%, #fbf7ff 100%);
        color: var(--ink);
    }
    [data-testid="stHeader"] { background: rgba(255,255,255,0); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f0edff 0%, #edf6ff 100%);
        border-right: 1px solid #e2e6fb;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: var(--primary-dark); }
    h1, h2, h3 { color: var(--ink); letter-spacing: -0.025em; }
    p, label, .stCaption { color: var(--muted); }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #ffffff, #f3f5ff);
        border: 1px solid var(--line);
        padding: 16px 18px;
        border-radius: 18px;
        box-shadow: 0 5px 18px rgba(57, 61, 128, 0.05);
    }
    [data-testid="stMetricLabel"] { color: #5b6590; }
    [data-testid="stMetricValue"] { color: var(--primary-dark); }
    div.stButton > button[kind="primary"] {
        border: 0;
        border-radius: 14px;
        min-height: 3.15rem;
        color: white;
        font-weight: 700;
        background: linear-gradient(95deg, #3768f5, #7842e8);
        box-shadow: 0 8px 18px rgba(91, 75, 219, 0.20);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 11px 22px rgba(91, 75, 219, 0.27);
        color: white;
        border: 0;
    }
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {
        border-radius: 12px;
        border-color: #dbe2f7;
    }
    [data-testid="stExpander"] {
        background: rgba(255,255,255,0.82);
        border: 1px solid var(--line);
        border-radius: 14px;
        overflow: hidden;
    }
    .hero-fallback {
        padding: 26px 30px;
        border-radius: 20px;
        color: #fff;
        background: linear-gradient(110deg, #2f66f3, #7044dc 65%, #a16bea);
        margin-bottom: 1rem;
    }
    .hero-fallback h1 { color: white; margin: 0; }
    .hero-fallback p { color: #f1f1ff; margin: 8px 0 0; }
    .section-intro {
        padding: 18px 20px;
        border: 1px solid #e2e8fb;
        border-radius: 18px;
        background: linear-gradient(100deg, #ffffff, #f1f6ff);
        margin-bottom: 16px;
    }
    .section-intro p { margin-bottom: 0; }
    .small-note {
        padding: 12px 15px;
        border-radius: 12px;
        background: #f1edff;
        color: #493a9d;
        font-size: 0.92rem;
    }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown("""
<style>
div.stButton > button[kind="primary"] {
    background-color: #2878F0 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.2rem !important;
}

div.stButton > button[kind="primary"] * {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

div.stButton > button[kind="primary"]:hover {
    background-color: #1D5FCC !important;
}
</style>
""", unsafe_allow_html=True)

if BANNER_PATH.exists():
    st.image(str(BANNER_PATH), use_container_width=True)
else:
    st.markdown(
        """
        <div class="hero-fallback">
            <h1>📚 Study Plan AI Agent</h1>
            <p>Plan smarter · Learn better · Achieve more</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="section-intro">
        <h2 style="margin:0">Your personal study companion ✨</h2>
        <p>Build a daily study schedule, explore a learning roadmap, and discover useful books and learning resources.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# Sidebar settings
# --------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Study settings")
    mode = st.radio(
        "Choose planning mode",
        ["Basic planner (no API key)", "LLM-powered agent (OpenAI API)"],
        help=(
            "Basic mode uses Python only. AI mode uses OpenAI to create a learning roadmap and recommend resources."
        ),
    )

    st.markdown("---")
    st.markdown("### 💡 What this project demonstrates")
    st.markdown(
        "- User goals and study context\n"
        "- Python planning functions\n"
        "- Optional OpenAI-powered roadmap\n"
        "- Input validation and scheduling\n"
        "- Books, YouTube searches, and learning links"
    )
    st.markdown("---")
    if mode == "Basic planner (no API key)":
        st.success("Basic mode is local and does not need an API key.")
    else:
        st.info("AI mode needs a valid OPENAI_API_KEY.")

# --------------------------------------------------
# Student input
# --------------------------------------------------
st.markdown("## 📝 Tell the agent about your studies")
st.write("Enter your subjects, available time, and learning goal.")

left, right = st.columns(2, gap="large")
with left:
    subjects_text = st.text_input(
        "📘 Subjects (comma-separated)",
        "Python, Databases, AI",
        help="Example: Python, Data Structures, Machine Learning",
    )
    total_minutes = st.number_input(
        "⏱️ Total study time (minutes)",
        min_value=15,
        max_value=720,
        value=180,
        step=15,
        help="Total available study time across the whole plan.",
    )
    start_date = st.date_input("📅 Start date", value=date.today())

with right:
    days = st.slider("🗓️ Plan length (days)", min_value=1, max_value=14, value=3)
    break_minutes = st.number_input(
        "☕ Break between study blocks (minutes)",
        min_value=0,
        max_value=30,
        value=5,
        step=5,
    )
    if mode == "LLM-powered agent (OpenAI API)":
        level = st.selectbox(
            "🎯 Your current learning level",
            ["Beginner", "Intermediate", "Advanced"],
        )
    else:
        level = "Beginner"
        st.caption("Learning level selection is available in AI mode.")

goal = st.text_area(
    "🎯 Study goal / extra instructions",
    "Help me revise the important concepts and include practice questions.",
    height=100,
    help="For example: prepare for an exam, build a small project, or revise key concepts.",
)

subjects = [subject.strip() for subject in subjects_text.split(",") if subject.strip()]

if st.button("✨ Create my study plan", type="primary", use_container_width=True):
    if not subjects:
        st.error("Please enter at least one subject.")
        st.stop()

    request = {
        "subjects": subjects,
        "total_minutes": int(total_minutes),
        "days": int(days),
        "start_date": start_date.isoformat(),
        "break_minutes": int(break_minutes),
        "goal": goal.strip(),
    }

    # The basic planner does not accept a level argument.
    if mode == "LLM-powered agent (OpenAI API)":
        request["level"] = level

    with st.spinner("✨ Building your personalized study plan..."):
        if mode == "Basic planner (no API key)":
            try:
                result = create_study_plan(**request)
                st.session_state["last_plan"] = result
                st.session_state["last_mode"] = "Basic planner"
            except Exception as exc:
                st.error(f"Could not create the study plan: {exc}")
                st.stop()
        else:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key:
                try:
                    api_key = str(st.secrets.get("OPENAI_API_KEY", "")).strip()
                except Exception:
                    api_key = ""

            if not api_key:
                st.error(
                    "OPENAI_API_KEY was not found. Set it as an environment variable or in "
                    ".streamlit/secrets.toml. Basic planner mode is available without a key."
                )
                st.stop()

            try:
                result = run_openai_agent(request, api_key=api_key)
                st.session_state["last_plan"] = result
                st.session_state["last_mode"] = "OpenAI learning-roadmap agent"
            except Exception as exc:
                st.error(f"The AI agent could not complete the request: {exc}")
                st.info("Check your API key, network connection, model access, and study_agent.py implementation.")
                st.stop()

# --------------------------------------------------
# Results
# --------------------------------------------------
if "last_plan" in st.session_state:
    result = st.session_state["last_plan"]
    created_with = st.session_state.get("last_mode", "Study planner")
    resources = result.get("resources", {}) or {}
    schedule = result.get("schedule", []) or []
    topics = result.get("topics", []) or []
    tips = result.get("tips", []) or []

    st.markdown("---")
    st.markdown("## 🏆 Your personalized study plan")
    st.caption(f"Created with: {created_with}")
    st.write(result.get("summary", "Here is your suggested study plan."))

    total = result.get("total_minutes", int(total_minutes))
    plan_days = result.get("days", int(days))
    result_subjects = result.get("subjects", subjects)
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("📚 Subjects", len(result_subjects))
    metric2.metric("⏱️ Study minutes", total)
    metric3.metric("🗓️ Plan days", plan_days)
    metric4.metric("🧭 Roadmap topics", len(topics))

    if result.get("ai_explanation"):
        st.info(result["ai_explanation"])

    tab_overview, tab_schedule, tab_roadmap, tab_books, tab_youtube, tab_links, tab_json = st.tabs(
        ["✨ Overview", "📅 Daily Schedule", "🗺️ Learning Roadmap", "📚 Books", "▶️ YouTube", "🌐 More Resources", "🧾 JSON"]
    )

    with tab_overview:
        st.markdown("### Plan overview")
        st.markdown(
            f"<div class='small-note'><b>Goal:</b> {goal.strip() or 'Build a consistent study routine.'}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("### Quick study tips")
        if tips:
            for tip in tips:
                st.markdown(f"- ✅ {tip}")
        else:
            st.markdown(
                "- ✅ Start each session by recalling what you already know.\n"
                "- ✅ Use practice questions and active recall.\n"
                "- ✅ Adjust the plan when a topic needs more time."
            )
        st.markdown("### Your subjects")
        st.write(" · ".join(result_subjects))

    with tab_schedule:
        if schedule:
            for day_item in schedule:
                day_title = f"Day {day_item.get('day', '?')} — {day_item.get('date', '')}"
                with st.expander(day_title, expanded=(day_item.get("day") == 1)):
                    st.caption(f"Total study time: {day_item.get('total_minutes', 0)} minutes")
                    tasks = day_item.get("tasks", []) or []
                    if not tasks:
                        st.write("No tasks were assigned for this day.")
                    for task in tasks:
                        st.markdown(
                            f"**{task.get('subject', 'Study')}** · "
                            f"{task.get('duration_minutes', 0)} minutes"
                        )
                        st.caption(task.get("activity", "Review concepts and practise."))
                    if day_item.get("note"):
                        st.info(day_item["note"])
        else:
            st.info("No daily schedule was returned.")

    with tab_roadmap:
        if topics:
            st.write("Follow the topics in order, and complete the practice task for each one.")
            for index, topic in enumerate(topics, start=1):
                title = topic.get("title", f"Topic {index}")
                with st.expander(f"{index}. {title}"):
                    if topic.get("objective"):
                        st.write(f"**Learning objective:** {topic['objective']}")
                    concepts = topic.get("concepts", []) or []
                    if concepts:
                        st.write("**Key concepts**")
                        for concept in concepts:
                            st.markdown(f"- {concept}")
                    if topic.get("practice_task"):
                        st.write(f"**Practice task:** {topic['practice_task']}")
                    allocated = topic.get("allocated_minutes", topic.get("estimated_minutes"))
                    if allocated is not None:
                        st.caption(f"Allocated time: {allocated} minutes")
        else:
            st.info("The Basic Planner creates a daily schedule. Switch to AI mode to generate a topic-by-topic roadmap.")

    with tab_books:
        books = resources.get("books", []) or []
        if books:
            for index, book in enumerate(books, start=1):
                with st.container(border=True):
                    st.markdown(f"#### {index}. {book.get('title', 'Untitled book')}")
                    st.caption(f"Author: {book.get('author', 'Author not specified')}")
                    if book.get("why_read"):
                        st.write(book["why_read"])
                    if book.get("url"):
                        st.markdown(f"[🔎 Find this book online]({book['url']})")
        else:
            st.info("Personalized book suggestions are available in AI mode when the agent returns resource recommendations.")

    with tab_youtube:
        youtube_resources = resources.get("youtube", []) or []
        if youtube_resources:
            for item in youtube_resources:
                title = item.get("title", "Learning topic")
                url = item.get("url")
                if url:
                    st.markdown(f"- [▶️ {title}]({url})")
                else:
                    st.markdown(f"- {title}")
            st.caption("These links open YouTube search results; they are not guaranteed to point to a specific verified video.")
        else:
            st.info("Personalized YouTube searches are available in AI mode when the agent returns resource recommendations.")

    with tab_links:
        additional_links = resources.get("additional_links", []) or []
        if additional_links:
            for item in additional_links:
                title = item.get("title", "Learning resource")
                description = item.get("description", "")
                url = item.get("url")
                with st.container(border=True):
                    st.markdown(f"#### {title}")
                    if description:
                        st.write(description)
                    if url:
                        st.markdown(f"[Open resource ↗]({url})")
        else:
            st.info("Additional links are available in AI mode when the agent returns resource recommendations.")

    with tab_json:
        st.download_button(
            "⬇️ Download study plan as JSON",
            data=json.dumps(result, indent=2, ensure_ascii=False),
            file_name="study_plan.json",
            mime="application/json",
            use_container_width=True,
        )
        with st.expander("View raw result"):
            st.code(json.dumps(result, indent=2, ensure_ascii=False), language="json")

st.markdown("---")
st.caption(
    "📖 Learning project only · Verify recommended books and links, and adapt the schedule to your syllabus and personal needs."
)
