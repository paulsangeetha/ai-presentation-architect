import streamlit as st
import requests
import json
import io
import re
from pptx import Presentation

# --- App Configuration ---
st.set_page_config(page_title="AI Presentation Architect", layout="wide")

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

# --- Helper Functions ---

def clean_json_text(text):
    """Remove markdown/code blocks"""
    text = re.sub(r"```json|```", "", text).strip()
    return text


def generate_english_presentation(topic: str, api_key: str, slide_count: int) -> list:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    Generate a {slide_count}-slide presentation on '{topic}'.
    Return ONLY a valid JSON array.
    Format:
    [
      {{
        "title": "Slide title",
        "content": "• point1\\n• point2\\n• point3"
      }}
    ]
    """

    payload = {
        "model": "sarvam-m",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(CHAT_API_URL, headers=headers, json=payload)

    # Debug logs
    print("CHAT STATUS:", response.status_code)
    print("CHAT RAW:", response.text)

    response.raise_for_status()

    data = response.json()

    if "choices" not in data:
        raise Exception(f"Invalid API response: {data}")

    response_text = data["choices"][0]["message"]["content"]

    response_text = clean_json_text(response_text)

    try:
        slides = json.loads(response_text)
    except Exception:
        raise Exception(f"JSON parsing failed.\nResponse:\n{response_text}")

    return slides


def translate_content(text: str, target_lang: str, api_key: str) -> str:
    if not text.strip() or target_lang == "en-IN":
        return text

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "input": text,
        "source_language_code": "en-IN",
        "target_language_code": target_lang
    }

    response = requests.post(TRANSLATE_API_URL, headers=headers, json=payload)

    print("TRANSLATE STATUS:", response.status_code)
    print("TRANSLATE RAW:", response.text)

    try:
        response.raise_for_status()
        data = response.json()

        if "translated_text" not in data:
            return text  # fallback

        return data["translated_text"]

    except Exception:
        return text  # fallback if translation fails


def create_powerpoint_presentation(slides, topic, lang_name):
    prs = Presentation()

    # Title Slide
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = topic
    slide.placeholders[1].text = f"Generated using AI ({lang_name})"

    # Content Slides
    for s in slides:
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = s["title"]
        slide.placeholders[1].text = s["content"]

    buffer = io.BytesIO()
    prs.save(buffer)
    buffer.seek(0)

    return buffer


# --- Streamlit UI ---

st.title("🤖 Multilingual AI Presentation Architect")

if "stage" not in st.session_state:
    st.session_state.stage = "input"


# --- INPUT STAGE ---
if st.session_state.stage == "input":

    st.header("Step 1: Enter Details")

    api_key = st.text_input("Sarvam API Key", type="password")
    topic = st.text_input("Presentation Topic")

    language = st.selectbox(
        "Select Language",
        list(SUPPORTED_LANGUAGES.keys()),
        format_func=lambda x: SUPPORTED_LANGUAGES[x]
    )

    slide_count = st.slider("Number of Slides", 2, 10, 5)

    if st.button("Generate Presentation"):

        if not api_key or not topic:
            st.warning("Please fill all fields")
            st.stop()

        with st.spinner("Generating presentation..."):

            try:
                st.info("Step 1: Generating English slides...")
                english_slides = generate_english_presentation(topic, api_key, slide_count)

                st.info("Step 2: Translating content...")
                translated_topic = translate_content(topic, language, api_key)

                translated_slides = []
                for slide in english_slides:
                    translated_slides.append({
                        "title": translate_content(slide["title"], language, api_key),
                        "content": translate_content(slide["content"], language, api_key)
                    })

                st.info("Step 3: Creating PowerPoint...")
                ppt_file = create_powerpoint_presentation(
                    translated_slides,
                    translated_topic,
                    SUPPORTED_LANGUAGES[language]
                )

                st.session_state.ppt = ppt_file
                st.session_state.filename = f"{topic.replace(' ', '_')}.pptx"
                st.session_state.stage = "download"

                st.rerun()

            except Exception as e:
                st.error(f"❌ Error: {e}")


# --- DOWNLOAD STAGE ---
if st.session_state.stage == "download":

    st.header("🎉 Your Presentation is Ready!")

    st.success("Download your file below")

    st.download_button(
        "Download PPT",
        data=st.session_state.ppt,
        file_name=st.session_state.filename,
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

    if st.button("Create Another"):
        st.session_state.stage = "input"
        st.rerun()