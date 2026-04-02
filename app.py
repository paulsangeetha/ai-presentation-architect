import streamlit as st
import requests
import json
import io
import re
from pptx import Presentation

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Sarvam AI Presentation", layout="wide")

CHAT_API_URL = "https://api.sarvam.ai/v1/chat/completions"
TRANSLATE_API_URL = "https://api.sarvam.ai/translate"

SUPPORTED_LANGUAGES = {
    'en-IN': 'English',
    'hi-IN': 'Hindi',
    'ta-IN': 'Tamil',
    'te-IN': 'Telugu',
    'bn-IN': 'Bengali',
    'kn-IN': 'Kannada',
    'mr-IN': 'Marathi',
    'gu-IN': 'Gujarati'
}

# ---------------- HELPERS ----------------

def clean_text(text):
    return re.sub(r"```json|```", "", text).strip()

def clean_for_ppt(text):
    if not text:
        return ""
    return text.replace("•", "-").replace("–", "-").replace("—", "-")

def safe_json_parse(text):
    try:
        return json.loads(text)
    except:
        return None

# ---------------- AI ----------------

def generate_slides(topic, api_key, slide_count):
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    prompt = f"""
    Create {slide_count} slides on "{topic}".
    Return ONLY JSON:
    [
      {{
        "title": "Title",
        "content": "- point1\\n- point2\\n- point3"
      }}
    ]
    """

    payload = {
        "model": "sarvam-m",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(CHAT_API_URL, headers=headers, json=payload)

    # DEBUG
    st.write("📡 Status:", response.status_code)
    st.write("📄 Response:", response.text[:800])

    if response.status_code != 200:
        raise Exception(f"API Error:\n{response.text}")

    try:
        data = response.json()
    except:
        raise Exception("Invalid JSON response")

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    if not content:
        raise Exception("Empty response from API")

    content = clean_text(content)

    slides = safe_json_parse(content)

    if slides is None:
        raise Exception(f"JSON parse failed:\n{content}")

    return slides


def translate(text, lang, api_key):
    if lang == "en-IN":
        return text

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "input": text,
        "source_language_code": "en-IN",
        "target_language_code": lang
    }

    try:
        response = requests.post(TRANSLATE_API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            return text

        return response.json().get("translated_text", text)

    except:
        return text


def create_ppt(slides, topic, lang):
    prs = Presentation()

    # Title
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = clean_for_ppt(topic)
    slide.placeholders[1].text = f"Generated in {lang}"

    # Slides
    for s in slides:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = clean_for_ppt(s["title"])
        slide.placeholders[1].text = clean_for_ppt(s["content"])

    buffer = io.BytesIO()
    prs.save(buffer)
    buffer.seek(0)

    return buffer

# ---------------- UI ----------------

st.title("🤖 Sarvam AI Presentation Generator")

if "stage" not in st.session_state:
    st.session_state.stage = "input"

if st.session_state.stage == "input":

    api_key = st.text_input("Enter Sarvam API Key", type="password")
    topic = st.text_input("Topic")

    language = st.selectbox(
        "Language",
        list(SUPPORTED_LANGUAGES.keys()),
        format_func=lambda x: SUPPORTED_LANGUAGES[x]
    )

    slides = st.slider("Slides", 2, 10, 5)

    if st.button("Generate"):

        if not api_key or not topic:
            st.warning("Enter all fields")
            st.stop()

        try:
            english_slides = generate_slides(topic, api_key, slides)

            translated_topic = translate(topic, language, api_key)

            translated_slides = []
            for s in english_slides:
                translated_slides.append({
                    "title": translate(s["title"], language, api_key),
                    "content": translate(s["content"], language, api_key)
                })

            ppt = create_ppt(
                translated_slides,
                translated_topic,
                SUPPORTED_LANGUAGES[language]
            )

            st.session_state.ppt = ppt
            st.session_state.file = f"{topic}.pptx"
            st.session_state.stage = "download"
            st.rerun()

        except Exception as e:
            st.error(e)

if st.session_state.stage == "download":

    st.success("Presentation Ready!")

    st.download_button(
        "Download PPT",
        st.session_state.ppt,
        st.session_state.file
    )

    if st.button("Start Again"):
        st.session_state.stage = "input"
        st.rerun()