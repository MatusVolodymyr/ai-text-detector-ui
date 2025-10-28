import streamlit as st
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import os

# MUST BE FIRST: Configure the page
st.set_page_config(
    page_title="AI Text Detector - GPTZero Style",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Force light theme
st.markdown(
    """
<script>
    const stApp = window.parent.document.querySelector('.stApp');
    if (stApp) {
        stApp.style.backgroundColor = '#ffffff';
    }
</script>
""",
    unsafe_allow_html=True,
)

# Get API URLs from environment variables (for Docker) or use RunPod defaults
API_URL = os.getenv(
    "API_URL", "https://localhost:8000/api/v1/predict"
)
FEEDBACK_URL = os.getenv(
    "FEEDBACK_URL", "https://localhost:8000/api/v1/feedback"
)

# Custom CSS for GPTZero-like styling with light theme override
st.markdown(
    """
<style>
    /* Force light theme */
    .stApp {
        background-color: #ffffff !important;
        color: #262730 !important;
    }
    
    /* Main container styling */
    .main .block-container {
        background-color: #ffffff !important;
        color: #262730 !important;
        padding-top: 2rem !important;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa !important;
    }
    
    .main-header {
        text-align: center;
        color: #2c3e50 !important;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        background: none !important;
    }
    .sub-header {
        text-align: center;
        color: #7f8c8d !important;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        background: none !important;
    }
    .result-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        padding: 1.5rem;
        border-radius: 15px;
        color: white !important;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white !important;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        color: #262730 !important;
    }
    .highlighted-text {
        font-family: 'Georgia', serif;
        font-size: 1.1rem;
        line-height: 1.8;
        padding: 1.5rem;
        background: white !important;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        color: #262730 !important;
    }
    .sentence-tooltip {
        position: relative;
        cursor: pointer;
    }
    .legend-item {
        display: inline-block;
        margin: 0 15px;
        font-weight: 600;
        color: inherit !important;
    }
    .legend-box {
        background: #f8f9fa !important;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        color: #262730 !important;
        border: 1px solid #e0e0e0;
    }
    
    /* Override Streamlit's default text colors */
    h1, h2, h3, h4, h5, h6, p, div, span {
        color: #262730 !important;
    }
    
    /* Text input and button styling */
    .stTextArea textarea {
        background-color: white !important;
        color: #262730 !important;
        border: 1px solid #e0e0e0 !important;
    }
    
    .stButton button {
        background-color: #667eea !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
    }
    
    .stCheckbox {
        color: #262730 !important;
    }
    
    /* Markdown content */
    .stMarkdown {
        color: #262730 !important;
    }
    
    /* Ensure selectbox and other widgets are visible */
    .stSelectbox label {
        color: #262730 !important;
    }
    
    .stSelectbox div[data-baseweb="select"] {
        background-color: white !important;
        color: #262730 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Header
st.markdown('<h1 class="main-header">🤖 AI Text Detector</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Detect AI-generated content with sentence-level analysis</p>',
    unsafe_allow_html=True,
)

# Initialize session state for storing results
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "analyzed_text" not in st.session_state:
    st.session_state.analyzed_text = None
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False

# Main content area
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("### 📝 Enter Text to Analyze")
    text_input = st.text_area(
        "",
        height=300,
        placeholder="Paste your text here for AI detection analysis...",
        key="text_input",
    )

    analyze_col1, analyze_col2 = st.columns([1, 3])
    with analyze_col1:
        analyze_button = st.button(
            "🔍 Analyze", type="primary", use_container_width=True
        )
    with analyze_col2:
        show_highlights = st.checkbox("Show sentence highlighting", value=True)

with col2:
    st.markdown("### 📊 AI Probability Overview")
    st.markdown("### 🎨 Color Legend")
    st.markdown(
        """
    <div class="legend-box">
        <span class="legend-item" style="color: #e74c3c;">🔴 Likely AI-Generated</span><br>
        <span class="legend-item" style="color: #f39c12;">🟡 Mixed/Uncertain</span><br>
        <span class="legend-item" style="color: #27ae60;">🟢 Likely Human-Written</span>
    </div>
    """,
        unsafe_allow_html=True,
    )


def get_highlight_color(probability):
    """Get background color based on AI probability."""
    if probability >= 0.75:
        return "#ffebee", "#c62828"  # Red background, dark red text
    elif probability >= 0.5:
        return "#fff3e0", "#ef6c00"  # Orange background, dark orange text
    elif probability >= 0.25:
        return "#fffde7", "#f57f17"  # Yellow background, dark yellow text
    else:
        return "#e8f5e8", "#2e7d32"  # Green background, dark green text


def create_highlighted_text(sentences_data):
    """Create highlighted text with sentence-level coloring."""
    highlighted_html = '<div class="highlighted-text">'

    for sentence_data in sentences_data:
        sentence = sentence_data["sentence"].strip()
        probability = sentence_data["ai_probability"]
        bg_color, text_color = get_highlight_color(probability)

        # Create tooltip with probability
        tooltip_text = f"AI Probability: {probability:.1%}"

        highlighted_html += f"""
        <span 
            style="
                background-color: {bg_color}; 
                color: {text_color}; 
                padding: 2px 4px; 
                margin: 1px;
                border-radius: 4px;
                font-weight: 500;
                transition: all 0.3s ease;
            "
            title="{tooltip_text}"
            class="sentence-tooltip"
        >{sentence}</span> """

    highlighted_html += "</div>"
    return highlighted_html


def create_probability_chart(sentences_data):
    """Create a probability distribution chart."""
    sentences = [f"S{i+1}" for i in range(len(sentences_data))]
    probabilities = [s["ai_probability"] for s in sentences_data]

    # Color mapping
    colors = []
    for prob in probabilities:
        if prob >= 0.75:
            colors.append("#e74c3c")
        elif prob >= 0.5:
            colors.append("#f39c12")
        elif prob >= 0.25:
            colors.append("#f1c40f")
        else:
            colors.append("#27ae60")

    fig = go.Figure(
        data=[
            go.Bar(
                x=sentences,
                y=probabilities,
                marker_color=colors,
                text=[f"{p:.1%}" for p in probabilities],
                textposition="auto",
                hovertemplate="<b>%{x}</b><br>AI Probability: %{y:.1%}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title="AI Probability by Sentence",
        xaxis_title="Sentences",
        yaxis_title="AI Probability",
        height=400,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    fig.add_hline(
        y=0.5, line_dash="dash", line_color="gray", annotation_text="Threshold (50%)"
    )

    return fig


def submit_feedback(
    text, prediction_result, feedback_type, failed_sentences=None, user_comment=None
):
    """Submit feedback about prediction accuracy."""
    try:
        feedback_data = {
            "text": text,
            "prediction_result": prediction_result,
            "feedback_type": feedback_type,
            "failed_sentences": failed_sentences,
            "user_comment": user_comment,
            "user_id": st.session_state.get("user_id", "streamlit_user"),
        }

        response = requests.post(FEEDBACK_URL, json=feedback_data, timeout=30)

        if response.status_code == 200:
            return True, response.json().get(
                "message", "Feedback submitted successfully!"
            )
        else:
            return False, f"Failed to submit feedback: {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}"


def show_feedback_section(text, prediction_result, sentences_data):
    """Display feedback section for users to report issues."""
    st.markdown("---")
    st.markdown("### 💬 Help Us Improve")
    st.markdown(
        "Was this prediction accurate? Your feedback helps us improve the AI detector."
    )

    if not st.session_state.feedback_submitted:
        feedback_col1, feedback_col2 = st.columns([2, 1])

        with feedback_col1:
            feedback_options = {
                "incorrect_overall": "❌ Overall prediction is wrong",
                "false_positive": "🚫 Incorrectly flagged as AI (false positive)",
                "false_negative": "🤖 Missed AI-generated content (false negative)",
                "incorrect_sentence": "📝 Some sentences incorrectly classified",
                "mixed_accuracy": "⚖️ Mixed results - some right, some wrong",
            }

            selected_feedback = st.selectbox(
                "What type of issue did you encounter?",
                options=list(feedback_options.keys()),
                format_func=lambda x: feedback_options[x],
                index=None,
                placeholder="Select an issue type...",
            )

            user_comment = st.text_area(
                "Additional comments (optional):",
                placeholder="Please describe the issue or provide context about why the prediction is wrong...",
                max_chars=1000,
            )

            # For sentence-level feedback, let users select problem sentences
            failed_sentences = None
            if selected_feedback == "incorrect_sentence" and sentences_data:
                st.markdown("**Select sentences that were incorrectly classified:**")
                failed_sentences = []
                for i, sentence_data in enumerate(sentences_data):
                    sentence = sentence_data["sentence"].strip()
                    is_ai = sentence_data["is_ai"]
                    prob = sentence_data["ai_probability"]

                    if st.checkbox(
                        f"Sentence {i+1}: {'🤖 AI' if is_ai else '👤 Human'} ({prob:.1%}) - \"{sentence[:50]}{'...' if len(sentence) > 50 else ''}\"",
                        key=f"sentence_feedback_{i}",
                    ):
                        failed_sentences.append(sentence)

        with feedback_col2:
            st.markdown("#### Quick Stats")
            if st.button("📊 View Feedback Statistics", type="secondary"):
                try:
                    response = requests.get(f"{FEEDBACK_URL}/stats", timeout=10)
                    if response.status_code == 200:
                        stats = response.json()
                        st.json(stats)
                    else:
                        st.error("Failed to load statistics")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

        # Submit feedback button
        if st.button(
            "📝 Submit Feedback", type="primary", disabled=not selected_feedback
        ):
            if selected_feedback:
                with st.spinner("Submitting feedback..."):
                    success, message = submit_feedback(
                        text=text,
                        prediction_result=prediction_result,
                        feedback_type=selected_feedback,
                        failed_sentences=failed_sentences if failed_sentences else None,
                        user_comment=user_comment if user_comment.strip() else None,
                    )

                if success:
                    st.success(f"✅ {message}")
                    st.session_state.feedback_submitted = True
                    st.balloons()
                else:
                    st.error(f"❌ {message}")
            else:
                st.warning("Please select a feedback type before submitting.")
    else:
        st.info(
            "✅ Thank you for your feedback! You can refresh the page to submit more feedback."
        )
        if st.button("🔄 Submit Another Feedback"):
            st.session_state.feedback_submitted = False
            st.rerun()


# Analysis logic
if analyze_button:
    if not text_input.strip():
        st.warning("⚠️ Please enter some text to analyze.")
    else:
        with st.spinner("🔄 Analyzing text with AI models..."):
            try:
                response = requests.post(
                    API_URL,
                    json={
                        "text": text_input,
                        "detailed_response": True,  # Always get detailed response for highlighting
                    },
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()

                # Store results in session state
                st.session_state.analysis_result = result
                st.session_state.analyzed_text = text_input

            except requests.exceptions.Timeout:
                st.error("⏰ Request timed out. Please try again.")
                st.stop()
            except requests.exceptions.ConnectionError:
                st.error(
                    "🔌 Cannot connect to the API. Make sure the RunPod service is running."
                )
                st.stop()
            except Exception as e:
                st.error(f"❌ Error analyzing text: {e}")
                st.stop()

# Display results if available (either from new analysis or session state)
if st.session_state.analysis_result is not None:
    result = st.session_state.analysis_result
    analyzed_text = st.session_state.analyzed_text

    # Add a clear button
    if st.button("🗑️ Clear Results", type="secondary"):
        st.session_state.analysis_result = None
        st.session_state.analyzed_text = None
        st.session_state.feedback_submitted = False
        st.rerun()

    # Overall result card
    st.markdown("---")

    overall_prob = result.get("ai_probability", 0)
    is_ai = result.get("is_ai", False)
    is_humanized = result.get("is_humanized", False)
    humanizer_prob = result.get("humanizer_probability", 0) * 100

    if is_ai:
        result_emoji = "🤖"
        result_text = "AI-Generated Content Detected"
        result_color = "#e74c3c"
    else:
        result_emoji = "👤"
        result_text = "Human-Written Content Detected"
        result_color = "#27ae60"

    st.markdown(
        f"""
    <div class="result-card" style="background: linear-gradient(135deg, {result_color} 0%, {result_color}aa 100%);">
        <h2>{result_emoji} {result_text}</h2>
        <h1 style="margin: 0.5rem 0; font-size: 3rem;">{overall_prob:.1%}</h1>
        <p style="margin: 0; opacity: 0.9;">Overall AI Probability (API)</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Add comparison between API probability and sentence-count-based probability
    if "sentence_level_results" in result and result["sentence_level_results"]:
        sentences_data = result["sentence_level_results"]
        total_sentences = len(sentences_data)
        ai_sentences = sum(1 for s in sentences_data if s["is_ai"])
        sentence_based_prob = (
            ai_sentences / total_sentences if total_sentences > 0 else 0
        )

        # Show comparison only if there's a significant difference
        prob_difference = abs(overall_prob - sentence_based_prob)
        if prob_difference > 0.1:  # Show if difference is more than 10%
            comparison_color = "#f39c12" if prob_difference > 0.2 else "#3498db"
            st.markdown(
                f"""
            <div style="background: {comparison_color}22; padding: 1rem; border-radius: 10px; margin: 1rem 0; border-left: 4px solid {comparison_color};">
                <h4 style="color: {comparison_color}; margin: 0 0 0.5rem 0;">📊 Probability Comparison</h4>
                <p style="margin: 0; color: #262730;">
                    <strong>API-based probability:</strong> {overall_prob:.1%} | 
                    <strong>Sentence-count-based probability:</strong> {sentence_based_prob:.1%} | 
                    <strong>Difference:</strong> {prob_difference:.1%}
                </p>
                <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.9rem;">
                    {"🔍 Significant difference detected - consider reviewing individual sentence classifications." if prob_difference > 0.2 else "ℹ️ Moderate difference between calculation methods."}
                </p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Metrics row
    if "sentence_level_results" in result and result["sentence_level_results"]:
        sentences_data = result["sentence_level_results"]

        # Create 6 columns for the metrics
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            total_sentences = len(sentences_data)
            st.markdown(
                f"""
            <div class="metric-card">
                <h3 style="color: #3498db; margin: 0;">{total_sentences}</h3>
                <p style="margin: 0; color: #7f8c8d;">Total Sentences</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            ai_sentences = sum(1 for s in sentences_data if s["is_ai"])
            st.markdown(
                f"""
            <div class="metric-card">
                <h3 style="color: #e74c3c; margin: 0;">{ai_sentences}</h3>
                <p style="margin: 0; color: #7f8c8d;">AI Sentences</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col3:
            human_sentences = total_sentences - ai_sentences
            st.markdown(
                f"""
            <div class="metric-card">
                <h3 style="color: #27ae60; margin: 0;">{human_sentences}</h3>
                <p style="margin: 0; color: #7f8c8d;">Human Sentences</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col4:
            # Calculate AI probability based on sentence count (new metric)
            sentence_based_ai_prob = (
                ai_sentences / total_sentences if total_sentences > 0 else 0
            )
            st.markdown(
                f"""
            <div class="metric-card">
                <h3 style="color: #f39c12; margin: 0;">{sentence_based_ai_prob:.1%}</h3>
                <p style="margin: 0; color: #7f8c8d;">AI Prob. (Sentence Count)</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col5:
            avg_prob = sum(s["ai_probability"] for s in sentences_data) / len(
                sentences_data
            )
            st.markdown(
                f"""
            <div class="metric-card">
                <h3 style="color: #9b59b6; margin: 0;">{avg_prob:.1%}</h3>
                <p style="margin: 0; color: #7f8c8d;">Avg. AI Probability</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col6:
            humanizer_res = ("Yes" if is_humanized else "No") + (f" ({humanizer_prob:.1f}%)")
            st.markdown(
                f"""
            <div class="metric-card">
                <h3 style="color: #9b59b6; margin: 0;">{humanizer_res}</h3>
                <p style="margin: 0; color: #7f8c8d;">Humanizer Applied</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Highlighted text display
        if show_highlights:
            st.markdown("### 🎨 Highlighted Text Analysis")
            st.markdown("*Hover over highlighted sentences to see AI probability*")
            highlighted_text = create_highlighted_text(sentences_data)
            st.markdown(highlighted_text, unsafe_allow_html=True)

        # Probability chart
        st.markdown("### 📊 Sentence-by-Sentence Analysis")
        chart = create_probability_chart(sentences_data)
        st.plotly_chart(chart, use_container_width=True)

        # Detailed table
        with st.expander("📋 Detailed Sentence Analysis"):
            for i, sentence_data in enumerate(sentences_data, 1):
                prob = sentence_data["ai_probability"]
                is_ai_sentence = sentence_data["is_ai"]
                sentence = sentence_data["sentence"].strip()

                status = "🤖 AI" if is_ai_sentence else "👤 Human"
                confidence = (
                    "High"
                    if abs(prob - 0.5) > 0.3
                    else "Medium" if abs(prob - 0.5) > 0.1 else "Low"
                )

                st.markdown(
                    f"""
                **Sentence {i}**: {status} ({prob:.1%} probability, {confidence} confidence)
                
                > *{sentence}*
                """
                )

        # Add feedback section after detailed analysis
        show_feedback_section(
            text=analyzed_text,
            prediction_result={
                "is_ai": result["is_ai"],
                "ai_probability": result["ai_probability"],
                "sentence_level_results": sentences_data,
            },
            sentences_data=sentences_data,
        )
    else:
        st.warning(
            "⚠️ No sentence-level analysis available. The text might be too short or the analysis failed."
        )

        # Show feedback section even if no detailed analysis
        show_feedback_section(
            text=analyzed_text,
            prediction_result={
                "is_ai": result["is_ai"],
                "ai_probability": result["ai_probability"],
                "sentence_level_results": [],
            },
            sentences_data=[],
        )
