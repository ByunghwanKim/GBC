import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import io
import base64
import html
import textwrap
import urllib.parse
import requests
import datetime
import time
import google.generativeai as genai
from pypdf import PdfReader
from github import Github
from github.GithubException import UnknownObjectException

# 1. 페이지 설정
st.set_page_config(page_title="GBC 연구 논문 DB 관리 시스템", page_icon="📚", layout="wide")

custom_css = textwrap.dedent("""\
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

html, body, [class*="st-"] {
    font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important;
}

[data-testid="stStatusWidget"] {visibility: hidden;}
.stAppDeployButton {display: none;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

[data-testid="stIconMaterial"],
span.material-symbols-outlined,
span.material-icons {
    font-family: 'Material Symbols Rounded' !important;
}

html, body { font-size: 16px !important; }
h1 { font-size: 2rem !important; font-weight: 800 !important; }
h2 { font-size: 1.4rem !important; font-weight: 700 !important; }
h3 { font-size: 1.2rem !important; font-weight: 700 !important; }
h4 { font-size: 1.05rem !important; font-weight: 700 !important; margin-top: 0.4rem !important; margin-bottom: 0.6rem !important; }

[data-testid="stTab"] p { font-size: 15.5px !important; font-weight: 600 !important; }
[data-testid="stContainer"] { padding: 4px 2px; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px !important; }

[data-testid="stTextInput"] input, [data-testid="stTextInputRootElement"] input {
    font-size: 15.5px !important; padding: 10px 14px !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    font-size: 15.5px !important; min-height: 46px !important;
}
[data-testid="stButton"] button {
    font-size: 14.5px !important; padding: 10px 16px !important; border-radius: 8px !important; font-weight: 600 !important;
}
[data-testid="stAlertContainer"] {
    font-size: 15px !important; padding: 14px 18px !important; border-radius: 10px !important;
}
[data-testid="stAlertContainer"] p {
    font-size: 15px !important; line-height: 1.6 !important;
}

div[data-testid="stDialog"] div[role="dialog"] {
    width: 85vw !important; max-width: 1200px !important; border-radius: 16px; padding: 8px 12px !important;
}
div[data-testid="stDialog"] p, div[data-testid="stDialog"] li {
    font-size: 15.5px !important; line-height: 1.7 !important;
}

p, li, span, div { line-height: 1.6; color: #1E293B; }

.stTextArea textarea {
    font-size: 15.5px !important; line-height: 1.75 !important; background-color: #F8FAFC !important;
    color: #0F172A !important; border: 1px solid #CBD5E1 !important; border-radius: 10px !important; padding: 14px !important;
}
.stTextArea textarea:disabled {
    background-color: #F1F5F9 !important; color: #020617 !important; -webkit-text-fill-color: #020617 !important; opacity: 1 !important; cursor: text !important;
}

.badge {
    display: inline-block; padding: 6px 14px; border-radius: 7px; font-size: 14px; font-weight: 700; margin-right: 8px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.badge-iv { background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
.badge-dv { background-color: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }
.badge-m { background-color: #F0FDF4; color: #15803D; border: 1px solid #BBF7D0; }
.badge-mod { background-color: #FFF7ED; color: #C2410C; border: 1px solid #FED7AA; }

.var-text { font-size: 15px; font-weight: 600; color: #334155; margin-right: 18px; display: inline-block; margin-bottom: 8px; }

.custom-action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    background-color: #FFFFFF;
    color: #31333F !important;
    border: 1px solid #D6D6D8;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 14.5px;
    font-weight: 600;
    text-decoration: none !important;
    box-sizing: border-box;
    text-align: center;
    height: 43px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.custom-action-btn:hover {
    border-color: #FF4B4B;
    color: #FF4B4B !important;
    background-color: #FAFAFA;
}
.custom-action-disabled {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    background-color: #F8F9FA;
    color: #9CA3AF !important;
    border: 1px solid #E5E7EB;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    box-sizing: border-box;
    text-align: center;
    height: 43px;
}
</style>
""")
st.markdown(custom_css, unsafe_allow_html=True)

# 2. 시스템 시크릿 키 로드
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")
    S2_API_KEY = st.secrets.get("S2_API_KEY", "")
    APP_PASSWORD = st.secrets.get("APP_PASSWORD", "gbc1234!")
except Exception:
    st.error("⚠️ Streamlit Secrets 설정을 확인해주세요.")
    st.stop()


# ==========================================
# [전체 잠금 구현] 로그인 인증 로직
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    _, col_login, _ = st.columns([1, 2, 1])
    
    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.title("🔒 GBC 연구 논문 DB")
        st.markdown("이 시스템은 인가된 사용자만 접근할 수 있는 비공개 데이터베이스입니다.")
        
        with st.form("login_form"):
            pw = st.text_input("접속 비밀번호를 입력하세요", type="password", placeholder="비밀번호 입력")
            submitted = st.form_submit_button("로그인", use_container_width=True)
            
            if submitted:
                if pw == APP_PASSWORD:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 일치하지 않습니다.")
                    
    st.stop()
# ==========================================


# Gemini AI 설정
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_available_gemini_model():
    preferred_models = ['gemini-3.6-flash', 'gemini-3.7-flash', 'gemini-3.5-flash', 'gemini-2.5-flash']
    try:
        available_models = [
            m.name.replace("models/", "")
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        ]
        selected_model = None
        for pref in preferred_models:
            if pref in available_models:
                selected_model = pref
                break
        if not selected_model and available_models:
            selected_model = available_models[0]
        if selected_model:
            return genai.GenerativeModel(
                model_name=selected_model,
                generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
            )
    except Exception:
        pass
    return genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
    )

model = get_available_gemini_model()

# GitHub 저장소 설정
repo = Github(GITHUB_TOKEN).get_repo(GITHUB_REPO)
EXCEL_FILE_PATH = "database/GBC_연구논문_DB.xlsx"

DB_COLUMNS = [
    'No.', '저자', '발행 연도', '논문/도서 제목', 
    '학술지명/출처', '핵심 이론', '연구 모형', '가설 정리', 
    '독립변수(IV)', '종속변수(DV)', '매개변수(Mediator)', 
    '조절변수(Moderator)', '주요 발견(Key Findings)', '설문문항', '링크(DOI/URL)'
]

def build_paper_link(row):
    raw = str(row.get('링크(DOI/URL)', '')).strip()
    if raw and raw not in ('-', 'nan', 'None'):
        if raw.startswith('http://') or raw.startswith('https://'):
            return raw, "원문 링크"
        if raw.startswith('10.'):
            return f"https://doi.org/{raw}", "DOI 링크"
        return f"https://{raw}", "링크"
    title = str(row.get('논문/도서 제목', '')).strip()
    if not title or title in ('-', 'nan', 'None'):
        return None, None
    query = urllib.parse.quote(title)
    return f"https://scholar.google.com/scholar?q={query}", "Google Scholar 검색"

@st.cache_data(ttl=15, show_spinner=False)
def load_master_excel():
    try:
        file_content = repo.get_contents(EXCEL_FILE_PATH)
        decoded = base64.b64decode(file_content.content)
        df = pd.read_excel(io.BytesIO(decoded))
        if '메모' in df.columns and '설문문항' not in df.columns:
            df = df.rename(columns={'메모': '설문문항'})
        drop_targets = ['상태', '권/호', '실무적 시사점', '국내/해외', '연구 주제/키워드', '메모', '연구 방법론']
        df = df.drop(columns=[col for col in drop_targets if col in df.columns], errors='ignore')
        for col in DB_COLUMNS:
            if col not in df.columns:
                df[col] = "-"
        return df[DB_COLUMNS], file_content.sha
    except UnknownObjectException:
        empty_df = pd.DataFrame(columns=DB_COLUMNS)
        return empty_df, None

def save_master_excel(df, sha):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    content = buffer.getvalue()
    if sha:
        repo.update_file(EXCEL_FILE_PATH, "Update GBC 연구논문 DB", content, sha)
    else:
        repo.create_file(EXCEL_FILE_PATH, "Create GBC 연구논문 DB", content)

def normalize_title(title):
    import re
    s = str(title).strip().lower()
    s = re.sub(r'[^\w가-힣]', '', s)
    return s

def find_duplicate_row(title, master_df):
    norm_target = normalize_title(title)
    if norm_target == "":
        return None
    existing_norms = master_df['논문/도서 제목'].astype(str).apply(normalize_title)
    match = master_df[existing_norms == norm_target]
    if not match.empty:
        return match.iloc[0]
    return None

def calculate_completeness(row):
    check_cols = [c for c in DB_COLUMNS if c not in ('No.', '논문/도서 제목')]
    score = 0
    for c in check_cols:
        v = row.get(c, None)
        if pd.notna(v) and str(v).strip() not in ('-', ''):
            score += 1
    return score

def disp(val, default="-"):
    if pd.isna(val):
        return default
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "none", "-"):
        return default
    return s

def safe(text):
    return html.escape(str(text))

def parse_gemini_json(raw_text):
    text = raw_text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise

def scroll_to_results():
    components.html(
        """
        <script>
            (function() {
                var doc = window.parent.document;
                var anchor = doc.getElementById('db-search-results-anchor');
                if (!anchor) { return; }

                anchor.scrollIntoView({behavior: 'instant', block: 'start'});

                var scope = anchor.parentElement ? anchor.parentElement.parentElement : null;
                if (scope) {
                    var all = scope.querySelectorAll('div');
                    all.forEach(function(el) {
                        if (el.scrollHeight > el.clientHeight + 5) {
                            el.scrollTop = 0;
                        }
                    });
                }
            })();
        </script>
        """,
        height=0,
    )

class SearchAPIError(Exception):
    pass

def citations_per_year(paper, current_year=None):
    if current_year is None:
        current_year = datetime.datetime.now().year
    c = paper.get("citationCount") or 0
    y = paper.get("year")
    if not y:
        return c
    age = max(1, current_year - y + 1)
    return c / age

@st.cache_data(ttl=600, show_spinner=False)
def _search_semantic_scholar_cached(query, limit, year_range, fields_of_study, sort_by, max_retries,
                                     open_access_only=False, journal_only=False):
    query_stripped = query.strip()
    
    # [수정] Semantic Scholar의 스마트 알고리즘(오타 교정, 퍼지 매칭)이 정상 작동하도록
    # 강제로 따옴표("")를 씌우는 로직을 제거했습니다.
    # 이제 사용자가 입력한 그대로(띄어쓰기 등 무시하고) 엔진에 전달됩니다.
    query_for_api = query_stripped

    api_limit = 100 if sort_by != "순수 관련도순" else limit

    url = (f"[https://api.semanticscholar.org/graph/v1/paper/search?query=](https://api.semanticscholar.org/graph/v1/paper/search?query=){urllib.parse.quote(query_for_api)}"
           f"&limit={api_limit}&fields=title,authors,year,venue,abstract,url,citationCount,"
           f"isOpenAccess,openAccessPdf,tldr,publicationTypes")

    if year_range != "전체 기간":
        current_year = datetime.datetime.now().year
        if "5년" in year_range:
            start_year = current_year - 5
        elif "10년" in year_range:
            start_year = current_year - 10
        elif "15년" in year_range:
            start_year = current_year - 15
        elif "20년" in year_range:
            start_year = current_year - 20
        else:
            start_year = None

        if start_year:
            url += f"&year={start_year}-{current_year}"

    if fields_of_study:
        url += f"&fieldsOfStudy={urllib.parse.quote(fields_of_study)}"

    headers = {"User-Agent": "GBC-Research-App/1.0"}
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=12)
            if response.status_code == 200:
                res_json = response.json()
                papers = res_json.get("data") or []

                if open_access_only:
                    papers = [p for p in papers if (p.get("openAccessPdf") or {}).get("url")]

                if journal_only:
                    papers = [p for p in papers if p.get("publicationTypes") and "JournalArticle" in p.get("publicationTypes")]

                # [수정] 지나치게 엄격했던 클라이언트 측 필터링(띄어쓰기 제거 후 강제 100% 매칭 검사)을 완전 삭제.
                # S2의 자체 Relevance 검색 엔진이 찾아낸 결과를 그대로 신뢰하여 활용합니다.

                if sort_by == "관련도 + 연차대비 영향력 (기본)":
                    top_relevant = papers[:50]
                    top_relevant.sort(key=lambda x: citations_per_year(x), reverse=True)
                    papers = top_relevant
                elif sort_by == "최신순":
                    papers.sort(key=lambda x: x.get("year") or 0, reverse=True)

                res_json["data"] = papers[:limit]
                return res_json

            elif response.status_code == 429:
                if attempt < max_retries:
                    time.sleep(3.0 * (attempt + 1))
                    continue
                else:
                    raise SearchAPIError("API 요청 한도 초과 (429 Too Many Requests). 잠시 후 다시 시도해 주세요. (무료 서버 혼잡)")
            else:
                raise SearchAPIError(f"API 오류 (상태 코드: {response.status_code})")
        except SearchAPIError:
            raise
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise SearchAPIError(f"네트워크 오류: {str(e)}")
    raise SearchAPIError("알 수 없는 API 호출 실패")


def search_semantic_scholar(query, limit=10, year_range="전체 기간", fields_of_study="", sort_by="관련도 + 연차대비 영향력 (기본)", max_retries=3,
                             open_access_only=False, journal_only=False):
    try:
        return _search_semantic_scholar_cached(query, limit, year_range, fields_of_study, sort_by, max_retries,
                                                open_access_only, journal_only)
    except SearchAPIError as e:
        return {"error": str(e)}


@st.cache_data(ttl=3600, show_spinner=False)
def _translate_via_google_cached(text, max_retries):
    url = "[https://translate.googleapis.com/translate_a/single](https://translate.googleapis.com/translate_a/single)"
    params = {
        "client": "gtx",
        "sl": "en",
        "tl": "ko",
        "dt": "t",
        "q": text
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                res_json = response.json()
                translated_sentences = [s[0] for s in res_json[0] if s[0]]
                return "".join(translated_sentences)
            elif response.status_code == 429:
                if attempt < max_retries:
                    time.sleep(2.0)
                    continue
                else:
                    raise SearchAPIError("API 요청 한도 초과 (429 Too Many Requests). 잠시 후 다시 시도해 주세요.")
            else:
                raise SearchAPIError(f"구글 번역 서버 오류 (코드: {response.status_code})")
        except SearchAPIError:
            raise
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1.5)
                continue
            raise SearchAPIError(f"번역 중 오류가 발생했습니다: {str(e)}")

    raise SearchAPIError("알 수 없는 번역 오류")


def translate_via_google(text, max_retries=2):
    if not text or text.strip() in ("", "초록 정보가 없습니다."):
        return "번역할 초록 내용이 없습니다."
    try:
        return _translate_via_google_cached(text, max_retries)
    except SearchAPIError as e:
        return str(e)

@st.dialog("📖 연구 논문 상세 분석 리포트", width="large")
def show_detail_dialog(row):
    _title = disp(row.get('논문/도서 제목'))
    _link, _link_label = build_paper_link(row)
    if _link:
        st.markdown(
            f"### 📄 {safe(_title)} "
            f"<a href='{_link}' target='_blank' rel='noopener noreferrer' "
            f"style='font-size:0.6em; text-decoration:none
