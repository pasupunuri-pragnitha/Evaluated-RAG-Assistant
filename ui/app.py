import os
import requests
import streamlit as st

st.set_page_config(page_title="Evaluated RAG Assistant", page_icon="📖", layout="centered")

API_URL = os.environ.get("API_URL", "http://localhost:8001").rstrip("/")


def make_fastapi_url(source_path: str) -> str:
    path = source_path.replace("\\", "/").strip()
    if path.startswith("docs/fastapi/"):
        path = path[len("docs/fastapi/") :]
    elif path.startswith("fastapi/"):
        path = path[len("fastapi/") :]
    if path.endswith("/index.md"):
        path = path[: -len("index.md")]
    elif path == "index.md":
        path = ""
    elif path.endswith(".md"):
        path = path[:-3] + "/"
    if path and not path.endswith("/"):
        path += "/"
    return f"https://fastapi.tiangolo.com/{path}"


st.title("Evaluated RAG Assistant")
st.caption(
    "Answers come from the FastAPI documentation, from a local Llama 3.1 8B model. "
    "It may be wrong; check the cited sources."
)

if "result" not in st.session_state:
    st.session_state.result = None

with st.form(key="query_form"):
    query = st.text_input(
        "Question",
        value="",
        placeholder="How do I declare optional query parameters?",
        label_visibility="collapsed",
    )
    submit_button = st.form_submit_button("Ask")

if submit_button and query.strip():
    try:
        with st.spinner("Searching documentation and generating answer (answers can take up to a minute)..."):
            response = requests.post(
                f"{API_URL}/ask",
                json={"query": query.strip()},
                timeout=300,
            )

        if response.status_code == 200:
            st.session_state.result = response.json()
        else:
            st.session_state.result = None
            st.error(f"API returned HTTP {response.status_code}: {response.text}")

    except requests.exceptions.Timeout:
        st.session_state.result = None
        st.error("Request timed out after 300 seconds. The local model took too long to respond.")
    except requests.exceptions.ConnectionError:
        st.session_state.result = None
        st.error(f"Could not connect to the API at {API_URL}. Please ensure the server is running.")
    except Exception as exc:
        st.session_state.result = None
        st.error(f"An unexpected error occurred: {exc}")

if st.session_state.result:
    data = st.session_state.result

    # Warning notifications if any
    for warning_msg in data.get("warnings", []):
        st.warning(warning_msg)

    # Refusal or Answer display
    if data.get("refused", False):
        st.info("No answer: the documentation did not contain enough evidence")
    else:
        st.markdown(data.get("answer", ""))

    # Cited sources
    sources_cited = data.get("sources_cited", [])
    if sources_cited and not data.get("refused", False):
        st.markdown("### Cited sources")
        for src in sources_cited:
            sp = src.get("source_path", "")
            hp = src.get("heading_path", "")
            url = make_fastapi_url(sp)
            link_text = f"{sp} ({hp})" if hp else sp
            st.markdown(f"- [{link_text}]({url})")

    # Retrieved sources (all 5)
    sources_retrieved = data.get("sources_retrieved", [])
    num_retrieved = len(sources_retrieved)
    with st.expander(f"Retrieved sources (all {num_retrieved})", expanded=False):
        for src in sources_retrieved:
            sp = src.get("source_path", "")
            hp = src.get("heading_path", "")
            vs = src.get("vector_score")
            rrf = src.get("rrf_score")
            vs_str = f"{vs:.4f}" if vs is not None else "N/A"
            rrf_str = f"{rrf:.4f}" if rrf is not None else "N/A"
            st.markdown(f"- **`{sp}`** ({hp}) — vector: `{vs_str}`, rrf: `{rrf_str}`")

    # Metadata caption
    retriever_name = data.get("retriever", "unknown")
    tvs = data.get("top_vector_score")
    tvs_str = f"{tvs:.4f}" if tvs is not None else "N/A"
    latency = data.get("latency_ms", {})
    total_lat = latency.get("total") if isinstance(latency, dict) else None
    lat_str = f"{total_lat:.1f} ms" if total_lat is not None else "N/A"

    st.caption(
        f"Retriever: `{retriever_name}` | Top Vector Score: `{tvs_str}` | Total Latency: `{lat_str}`"
    )
