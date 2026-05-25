"""My Profile page — Outreach CRM.

Allows the user to view and update their background profile.
Claude uses this profile as context when drafting cold emails.

FOUND-03: Profile must be persisted and surfaced for every email draft.
"""
import streamlit as st

st.set_page_config(
    page_title="Outreach CRM",
    page_icon=":outbox_tray:",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.session import init_session_state

init_session_state()

from models.profile import get_profile, save_profile

st.title("My Profile")
st.write("Your background is used as context in every email Claude drafts. Keep it current.")
st.divider()

profile = get_profile()

if profile == {}:
    st.info("Fill in your profile before starting outreach — Claude uses this to personalize every email.")

with st.form(key="my_profile_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full Name", value=profile.get("full_name", ""))
        school = st.text_input("School", value=profile.get("school", ""))
        degree = st.text_input("Degree", value=profile.get("degree", ""))
    with col2:
        gpa = st.number_input(
            "GPA",
            min_value=0.0,
            max_value=4.0,
            step=0.01,
            value=float(profile.get("gpa") or 0.0),
        )
        years_exp = st.number_input(
            "Years of Experience",
            min_value=0,
            max_value=20,
            step=1,
            value=int(profile.get("years_experience") or 0),
        )
        ml_focus = st.text_input("ML/NLP Focus Area", value=profile.get("ml_nlp_focus", ""))

    st.divider()

    skills = st.text_area(
        "Skills (comma-separated)",
        height=80,
        value=profile.get("skills", ""),
        help="e.g. Python, PyTorch, LLM fine-tuning, RAG",
    )
    bio = st.text_area(
        "Bio / Profile Summary",
        height=150,
        value=profile.get("bio", ""),
        help="Used verbatim as context in every Claude email draft. Write in first person, under 200 words.",
    )

    submitted = st.form_submit_button("Save Profile", type="primary")

if submitted:
    if not name.strip() or not school.strip():
        st.error("Full Name and School are required.")
    else:
        save_profile(
            {
                "full_name": name.strip(),
                "school": school.strip(),
                "degree": degree.strip(),
                "gpa": gpa,
                "years_experience": years_exp,
                "skills": skills.strip(),
                "ml_nlp_focus": ml_focus.strip(),
                "bio": bio.strip(),
            }
        )
        st.success("Profile saved.")
        st.toast("Profile saved.", icon="✅")
