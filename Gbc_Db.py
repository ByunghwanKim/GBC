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
from google.api_core.exceptions import ResourceExhausted, NotFound
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

# [추가] 무료 티어 할당량이 모델마다 다르므로, 할당량 초과 시 순서대로 넘어갈 수 있게
# 우선순위 리스트를 별도로 보관 (get_available_gemini_model은 이 중 '가장 좋은' 1개만
# 선택하지만, 할당량 소진 시 generate_content_with_fallback()이 이 리스트를 순회한다)
# [수정] gemini-2.5-flash, gemini-2.0-flash는 이미 단종되어 404를 반환하므로 목록에서 제거.
# 현재 유효한 모델만 남김.
GEMINI_MODEL_PRIORITY = ['gemini-3.6-flash', 'gemini-3.7-flash', 'gemini-3.5-flash', 'gemini-3.5-flash-lite', 'gemini-1.5-pro', 'gemini-1.5-flash']

@st.cache_resource
def get_available_gemini_model():
    preferred_models = GEMINI_MODEL_PRIORITY
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
        model_name='gemini-3.6-flash',
        generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
    )

model = get_available_gemini_model()

@st.cache_resource
def _get_fallback_model_pool():
    """[추가] GEMINI_MODEL_PRIORITY에 있는 모델들을 미리 GenerativeModel 객체로 만들어둠.
    기본 모델(model)이 할당량 초과로 막히면 이 풀에서 순서대로 다음 모델을 시도한다."""
    pool = {}
    for name in GEMINI_MODEL_PRIORITY:
        try:
            pool[name] = genai.GenerativeModel(
                model_name=name,
                generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
            )
        except Exception:
            continue
    return pool

def generate_content_with_fallback(prompt, max_retries_per_model=2):
    """[수정] Gemini 할당량 초과(ResourceExhausted, 429)뿐 아니라
    모델 단종(NotFound, 404)도 함께 대응.
    1) 할당량 초과(일시적/분당) -> 같은 모델로 짧게 재시도
    2) 할당량 초과(일일 한도 소진) -> 우선순위상 다음 모델로 자동 전환
    3) 모델 자체가 단종(404 NotFound) -> 재시도해도 절대 성공할 수 없으므로
       즉시 다음 모델로 넘어감 (이 부분이 빠져 있어서 단종 모델을 만나면
       폴백 없이 바로 에러가 올라갔던 문제를 수정)
    4) 모든 모델이 다 막히면 마지막 에러를 그대로 올려서 호출부가 사용자에게 알리게 함
    """
    pool = _get_fallback_model_pool()
    ordered_models = [model] + [m for name, m in pool.items() if m is not model]

    last_error = None
    for candidate in ordered_models:
        try:
            for attempt in range(max_retries_per_model):
                try:
                    return candidate.generate_content(prompt)
                except ResourceExhausted as e:
                    last_error = e
                    msg = str(e)
                    # 메시지에 담긴 "Please retry in X.Xs" 힌트를 읽어서 그만큼만 대기 (없으면 기본 backoff)
                    wait_s = 5.0 * (attempt + 1)
                    if "retry in" in msg:
                        try:
                            wait_s = float(msg.split("retry in")[1].split("s")[0].strip())
                        except Exception:
                            pass
                    # 하루 단위 할당량(PerDay)까지 소진된 경우는 같은 모델을 더 기다려봐야 소용없으므로
                    # 바로 다음 모델로 넘어감. 분당/짧은 한도로 보이면 안내된 시간만큼 대기 후 재시도.
                    if "PerDay" in msg:
                        break
                    time.sleep(min(wait_s, 15.0))
                    continue
        except NotFound as e:
            # [추가] 모델이 단종되어 404가 난 경우: 이 모델은 재시도 자체가 무의미하므로
            # 즉시 다음 우선순위 모델로 넘어간다.
            last_error = e
            continue
        except Exception as e:
                # 할당량 문제가 아닌 다른 오류는 폴백해도 소용없으므로 즉시 올림
                raise
    # 모든 모델/재시도가 실패
    raise last_error if last_error else RuntimeError("Gemini 모델 호출에 모두 실패했습니다.")

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
    """Gemini 응답을 JSON으로 파싱. 두 종류의 흔한 문제를 방어한다:
    1) 마크다운 코드펜스(```json ... ```)로 감싸서 응답하는 경우 -> 벗겨냄
    2) 문자열 값 안에 실제 줄바꿈 문자가 이스케이프(\\n) 없이 그대로 들어간 경우
       -> "Expecting ',' delimiter" / "Invalid control character" 에러로 이어짐.
          survey_items, hypotheses처럼 여러 줄 형식을 요청한 필드에서 특히 자주 발생.
          json.loads(text, strict=False)로 재시도하면 이런 원문 그대로의 제어문자를
          허용해서 파싱에 성공한다."""
    text = raw_text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    def _try_loads(s):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return json.loads(s, strict=False)

    try:
        return _try_loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return _try_loads(text[start:end + 1])
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

    # Semantic Scholar의 스마트 알고리즘(오타 교정, 퍼지 매칭)이 정상 작동하도록
    # 강제로 따옴표("")를 씌우는 로직을 제거했습니다.
    # 이제 사용자가 입력한 그대로(띄어쓰기 등 무시하고) 엔진에 전달됩니다.
    query_for_api = query_stripped

    api_limit = 100 if sort_by != "순수 관련도순" else limit

    # [수정] 마크다운 링크 문법이 문자열 안에 그대로 섞여 들어가 있던 것을 제거.
    # ("[https://...](https://...)"처럼 되어 있으면 실제 URL이 아니라 텍스트라서
    # 요청 자체가 실패합니다.)
    url = (f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(query_for_api)}"
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
    # [수정] 마크다운 링크 문법이 섞여 들어가 있던 것을 제거 (실제 URL로 복구)
    url = "https://translate.googleapis.com/translate_a/single"
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
            f"style='font-size:0.6em; text-decoration:none;'>🔗 {safe(_link_label)}</a>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(f"### 📄 {_title}")
    
    col_m1, col_m2, col_m3 = st.columns([1, 1, 2])
    col_m1.info(f"👤 **저자:** {disp(row.get('저자'))}")
    col_m2.info(f"📅 **발행 연도:** {disp(row.get('발행 연도'))}")
    col_m3.info(f"🏛️ **학술지명/출처:** {disp(row.get('학술지명/출처'))}")
    
    st.divider()
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("#### 💡 핵심 이론")
        st.info(disp(row.get('핵심 이론')))
        
        st.markdown("#### 📊 연구 모형")
        st.success(disp(row.get('연구 모형')))
        
        st.markdown("#### 🔗 연구 변수 구성")
        iv = disp(row.get('독립변수(IV)'))
        m = disp(row.get('매개변수(Mediator)'))
        mod = disp(row.get('조절변수(Moderator)'))
        dv = disp(row.get('종속변수(DV)'))
        
        html_vars = "<div style='line-height:2.0;'>"
        if iv not in ['-', '']: html_vars += f"<span class='badge badge-iv'>IV</span> <span class='var-text'>{safe(iv)}</span><br>"
        if m not in ['-', '']: html_vars += f"<span class='badge badge-m'>Med</span> <span class='var-text'>{safe(m)}</span><br>"
        if mod not in ['-', '']: html_vars += f"<span class='badge badge-mod'>Mod</span> <span class='var-text'>{safe(mod)}</span><br>"
        if dv not in ['-', '']: html_vars += f"<span class='badge badge-dv'>DV</span> <span class='var-text'>{safe(dv)}</span>"
        html_vars += "</div>"
        st.markdown(html_vars, unsafe_allow_html=True)
        
    with col_right:
        st.markdown("#### 📌 가설 체계")
        st.text_area("가설 정리", value=disp(row.get('가설 정리')), height=150, disabled=True, label_visibility="collapsed")
        
        st.markdown("#### 🎯 주요 발견 (Key Findings)")
        st.warning(disp(row.get('주요 발견(Key Findings)')))

    st.divider()
    
    st.markdown("#### 📝 측정 척도 및 설문 문항 원문")
    survey_content = disp(row.get('설문문항'))
    if survey_content != "-":
        st.text_area("설문문항 상세", value=survey_content, height=450, label_visibility="collapsed")
    else:
        st.error("등록된 세부 설문문항 데이터가 없습니다.")

@st.dialog("🇰🇷 구글 번역 논문 초록 한글 번역", width="large")
def show_s2_abstract_dialog(title, abstract):
    st.markdown(f"### 📄 {safe(title)}")
    st.divider()
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### 🇺🇸 영문 원본 초록 (Original Abstract)")
        st.text_area("영문 초록", value=abstract, height=350, disabled=True, label_visibility="collapsed")
        
    with col_t2:
        st.markdown("#### 🇰🇷 구글 한글 번역 초록 (Google Translation)")
        with st.spinner("구글 번역 엔진으로 번역 중입니다..."):
            korean_abstract = translate_via_google(abstract)
                
        st.text_area("한글 번역 초록", value=korean_abstract, height=350, disabled=True, label_visibility="collapsed")

# 사이드바 관리자 인증
st.sidebar.title("🔐 관리자 모드")
input_pw = st.sidebar.text_input("관리자 비밀번호", type="password", placeholder="비밀번호 입력")
is_admin = bool(ADMIN_PASSWORD and input_pw == ADMIN_PASSWORD)

if is_admin:
    st.sidebar.success("관리자 권한이 활성화되었습니다.")
elif input_pw:
    st.sidebar.error("비밀번호가 일치하지 않습니다.")

# 메인 화면 구성
st.title("📚 GBC 연구 논문 DB 관리 시스템")

tab_names = ["🔍 연구 논문 DB 검색", "🌐 Semantic Scholar 검색", "🚀 논문 파일 업로드"]
if is_admin:
    tab_names.append("⚙️ 관리자 전용 관리 (DB/다운로드)")

tabs = st.tabs(tab_names)

# [탭 1] 연구 논문 DB 검색
with tabs[0]:
    st.subheader("🔍 연구 논문 DB 정밀 검색")
    
    master_df, _ = load_master_excel()
    
    if master_df.empty:
        st.info("현재 DB에 저장된 논문 데이터가 없습니다. [논문 파일 업로드] 탭에서 논문을 먼저 추가해 보세요.")
    else:
        with st.container(border=True):
            col_f1, col_f2 = st.columns([1, 2])
            with col_f1:
                search_field = st.selectbox(
                    "🎯 검색 필드 선택", 
                    ["전체 (통합 검색)", "저자", "발행년도", "제목", "변수 (IV/DV/매개/조절)", "가설", "출처", "핵심 이론"]
                )
            with col_f2:
                search_kw = st.text_input("🔎 검색어 입력", placeholder="검색어를 입력하세요 (띄어쓰기 무시 적용)")

        filtered_df = master_df.copy()
        
        if search_kw.strip():
            kw_clean = search_kw.replace(" ", "").lower()
            
            if search_field == "전체 (통합 검색)":
                mask = filtered_df.fillna("").astype(str).apply(
                    lambda col: col.str.replace(" ", "", regex=False).str.lower().str.contains(kw_clean, na=False, regex=False)
                ).any(axis=1)
                filtered_df = filtered_df[mask]
            elif search_field == "저자":
                target_col = '저자'
                if target_col in filtered_df.columns:
                    mask = filtered_df[target_col].fillna("").astype(str).str.replace(" ", "", regex=False).str.lower().str.contains(kw_clean, na=False, regex=False)
                    filtered_df = filtered_df[mask]
            elif search_field == "발행년도":
                target_col = '발행 연도'
                if target_col in filtered_df.columns:
                    mask = filtered_df[target_col].fillna("").astype(str).str.replace(" ", "", regex=False).str.lower().str.contains(kw_clean, na=False, regex=False)
                    filtered_df = filtered_df[mask]
            elif search_field == "제목":
                target_col = '논문/도서 제목'
                if target_col in filtered_df.columns:
                    mask = filtered_df[target_col].fillna("").astype(str).str.replace(" ", "", regex=False).str.lower().str.contains(kw_clean, na=False, regex=False)
                    filtered_df = filtered_df[mask]
            elif search_field == "변수 (IV/DV/매개/조절)":
                var_cols = ['독립변수(IV)', '종속변수(DV)', '매개변수(Mediator)', '조절변수(Moderator)']
                mask = filtered_df[var_cols].fillna("").astype(str).apply(
                    lambda col: col.str.replace(" ", "", regex=False).str.lower().str.contains(kw_clean, na=False, regex=False)
                ).any(axis=1)
                filtered_df = filtered_df[mask]
            elif search_field == "가설":
                target_col = '가설 정리'
                if target_col in filtered_df.columns:
                    mask = filtered_df[target_col].fillna("").astype(str).str.replace(" ", "", regex=False).str.lower().str.contains(kw_clean, na=False, regex=False)
                    filtered_df = filtered_df[mask]
            elif search_field == "출처":
                target_col = '학술지명/출처'
                if target_col in filtered_df.columns:
                    mask = filtered_df[target_col].fillna("").astype(str).str.replace(" ", "", regex=False).str.lower().str.contains(kw_clean, na=False, regex=False)
                    filtered_df = filtered_df[mask]
            elif search_field == "핵심 이론":
                target_col = '핵심 이론'
                if target_col in filtered_df.columns:
                    mask = filtered_df[target_col].fillna("").astype(str).str.replace(" ", "", regex=False).str.lower().str.contains(kw_clean, na=False, regex=False)
                    filtered_df = filtered_df[mask]

        st.markdown('<div id="db-search-results-anchor"></div>', unsafe_allow_html=True)
        if st.session_state.pop('scroll_to_top', False):
            scroll_to_results()

        st.markdown(f"##### 📌 조회 결과: 총 **{len(filtered_df)}** 건")
        
        if filtered_df.empty:
            st.warning("조건에 맞는 논문이 없습니다. 검색어 또는 필드를 변경해 보세요.")
        else:
            ITEMS_PER_PAGE = 20
            total_items = len(filtered_df)
            total_pages = (total_items - 1) // ITEMS_PER_PAGE + 1
            
            if 'db_page' not in st.session_state:
                st.session_state['db_page'] = 1
            if 'last_search_kw' not in st.session_state:
                st.session_state['last_search_kw'] = search_kw
                st.session_state['last_search_field'] = search_field
                
            if (st.session_state['last_search_kw'] != search_kw) or (st.session_state['last_search_field'] != search_field):
                st.session_state['db_page'] = 1
                st.session_state['last_search_kw'] = search_kw
                st.session_state['last_search_field'] = search_field
                
            if st.session_state['db_page'] > total_pages:
                st.session_state['db_page'] = total_pages
            if st.session_state['db_page'] < 1:
                st.session_state['db_page'] = 1
                
            start_idx = (st.session_state['db_page'] - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            render_df = filtered_df.iloc[start_idx:end_idx]

            with st.container(height=750, border=False):
                for idx, row in render_df.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([6, 1])
                        
                        with c1:
                            _title = disp(row.get('논문/도서 제목'))
                            _link, _link_label = build_paper_link(row)
                            if _link:
                                st.markdown(
                                    f"#### 📄 {safe(_title)} "
                                    f"<a href='{_link}' target='_blank' rel='noopener noreferrer' "
                                    f"style='font-size:0.55em; text-decoration:none;'>🔗 {safe(_link_label)}</a>",
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(f"#### 📄 {_title}")
                            st.markdown(f"<span style='color:#64748B; font-size:15px;'>👤 **{safe(disp(row.get('저자')))}** &nbsp;|&nbsp; 📅 **{safe(disp(row.get('발행 연도')))}** &nbsp;|&nbsp; 🏛️ **{safe(disp(row.get('학술지명/출처')))}**</span>", unsafe_allow_html=True)
                            
                            iv = disp(row.get('독립변수(IV)'))
                            m = disp(row.get('매개변수(Mediator)'))
                            mod = disp(row.get('조절변수(Moderator)'))
                            dv = disp(row.get('종속변수(DV)'))
                            
                            html_vars = "<div style='margin-top: 12px; margin-bottom: 5px;'>"
                            if iv not in ['-', '']: html_vars += f"<span class='badge badge-iv'>IV</span><span class='var-text'>{safe(iv)}</span>"
                            if m not in ['-', '']: html_vars += f"<span class='badge badge-m'>Med</span><span class='var-text'>{safe(m)}</span>"
                            if mod not in ['-', '']: html_vars += f"<span class='badge badge-mod'>Mod</span><span class='var-text'>{safe(mod)}</span>"
                            if dv not in ['-', '']: html_vars += f"<span class='badge badge-dv'>DV</span><span class='var-text'>{safe(dv)}</span>"
                            html_vars += "</div>"
                            
                            st.markdown(html_vars, unsafe_allow_html=True)
                            
                        with c2:
                            st.write("") 
                            if st.button("🔍 상세보기", key=f"btn_detail_{idx}_{row['No.']}", use_container_width=True):
                                show_detail_dialog(row)

            if total_pages > 1:
                st.divider()
                cp4, cp5, cp6 = st.columns([1, 4, 1])
                with cp4:
                    if st.button("◀ 이전 20건", key="prev_bot", disabled=(st.session_state['db_page'] == 1), use_container_width=True):
                        st.session_state['db_page'] -= 1
                        st.session_state['scroll_to_top'] = True
                        st.rerun()
                with cp5:
                    st.markdown(f"<div style='text-align:center; padding-top:8px; font-weight:600; color:#475569;'>페이지 {st.session_state['db_page']} / {total_pages}</div>", unsafe_allow_html=True)
                with cp6:
                    if st.button("다음 20건 ▶", key="next_bot", disabled=(st.session_state['db_page'] == total_pages), use_container_width=True):
                        st.session_state['db_page'] += 1
                        st.session_state['scroll_to_top'] = True
                        st.rerun()

# [탭 2] Semantic Scholar 검색 기능
with tabs[1]:
    st.subheader("🌐 Semantic Scholar 글로벌 논문 검색")

    field_options = {
        "전체 분야 (All Fields)": "",
        "경영학 (Business)": "Business",
        "경제학 (Economics)": "Economics",
        "경영/경제 통합 (Business & Economics)": "Business,Economics",
        "심리학 (Psychology)": "Psychology",
        "컴퓨터공학 (Computer Science)": "Computer Science",
        "사회학 (Sociology)": "Sociology",
        "정치학 (Political Science)": "Political Science",
        "수학/통계 (Mathematics)": "Mathematics"
    }

    with st.container(border=True):
        s2_query = st.text_input("🔎 Semantic Scholar 검색어 입력", placeholder="예: Technology Acceptance Model, Generative AI advertising 등", key="s2_input_query")
        
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            s2_limit = st.selectbox("📊 가져올 결과 수", [5, 10, 15, 20, 30], index=1)
        with col_f2:
            s2_year_range = st.selectbox("📅 검색 연도 범위", ["전체 기간", "최근 5년", "최근 10년", "최근 15년", "최근 20년"], index=0)
        with col_f3:
            s2_field_label = st.selectbox("📚 연구 분야 (Category)", list(field_options.keys()), index=3)
        with col_f4:
            s2_sort_label = st.selectbox("⬇️ 정렬 기준 (Sort By)", ["관련도 + 연차대비 영향력 (기본)", "순수 관련도순", "최신순"], index=0)

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            s2_open_access_only = st.checkbox("🔓 원문 무료 열람 가능(Open Access)만 보기")
        with col_c2:
            s2_journal_only = st.checkbox("📖 학술지(Journal Article) 논문만 보기")

    if st.button("🚀 Semantic Scholar 검색", type="primary", key="btn_s2_search"):
        if not s2_query.strip():
            st.warning("검색어를 입력해주세요.")
        else:
            with st.spinner("Semantic Scholar에서 논문을 검색하고 있습니다..."):
                selected_field_value = field_options[s2_field_label]
                result_json = search_semantic_scholar(
                    s2_query, limit=s2_limit, year_range=s2_year_range,
                    fields_of_study=selected_field_value, sort_by=s2_sort_label,
                    open_access_only=s2_open_access_only, journal_only=s2_journal_only
                )
                st.session_state['s2_last_result'] = result_json
                st.session_state['s2_queried'] = True

    if st.session_state.get('s2_queried', False):
        res_data = st.session_state.get('s2_last_result', {})
        
        if "error" in res_data:
            st.error(f"⚠️ 검색 실패: {res_data['error']}")
        else:
            papers = res_data.get("data", [])
            total = res_data.get("total", len(papers))
            st.markdown(f"##### 📌 Semantic Scholar 검색 결과 (상위 {len(papers)}건 표시)")

            if not papers:
                st.info("검색된 논문이 없습니다. 검색어 또는 연구 분야를 변경해 보세요.")
            else:
                s2_dup_check_df, _ = load_master_excel()

                for i, paper in enumerate(papers):
                    p_title = paper.get("title", "제목 없음")
                    p_year = paper.get("year", "-")
                    p_venue = paper.get("venue", "-")
                    p_citations = paper.get("citationCount", 0)
                    p_url = paper.get("url", "#")
                    
                    authors_list = paper.get("authors", [])
                    authors_str = ", ".join([a.get("name", "") for a in authors_list]) if authors_list else "저자 정보 없음"
                    
                    p_abstract = paper.get("abstract", "초록 정보가 없습니다.")
                    if not p_abstract:
                        p_abstract = "초록 정보가 없습니다."

                    p_tldr = paper.get("tldr")
                    p_tldr_text = p_tldr.get("text") if p_tldr else None

                    pdf_info = paper.get("openAccessPdf")
                    pdf_url = pdf_info.get("url") if pdf_info else None

                    dup_row = find_duplicate_row(p_title, s2_dup_check_df) if not s2_dup_check_df.empty else None

                    with st.container(border=True):
                        title_line = f"#### 📄 {p_title}"
                        if dup_row is not None:
                            title_line += (f" <span style='font-size:0.5em; background-color:#DCFCE7; color:#15803D; "
                                           f"padding:3px 8px; border-radius:6px; font-weight:700;'>"
                                           f"✅ DB에 있음 (No.{dup_row['No.']})</span>")
                        st.markdown(title_line, unsafe_allow_html=True)
                        st.markdown(f"<span style='color:#64748B; font-size:14.5px;'>👤 **{authors_str}** &nbsp;|&nbsp; 📅 **{p_year}** &nbsp;|&nbsp; 🏛️ 출처: **{p_venue}** &nbsp;|&nbsp; 📈 피인용: **{p_citations}회**</span>", unsafe_allow_html=True)
                        if p_tldr_text:
                            st.caption(f"🤖 TL;DR: {p_tldr_text}")
                        
                        with st.expander("📖 초록(Abstract) 및 링크 보기"):
                            st.write(p_abstract)
                            st.divider()
                            
                            c_l1, c_l2, c_l3, c_l4 = st.columns(4)
                            
                            with c_l1:
                                st.markdown(f"<a class='custom-action-btn' href='{p_url}' target='_blank' rel='noopener noreferrer'>🔗 Semantic Scholar</a>", unsafe_allow_html=True)
                                
                            with c_l2:
                                if pdf_url:
                                    st.markdown(f"<a class='custom-action-btn' href='{pdf_url}' target='_blank' rel='noopener noreferrer'>📄 원문 페이지</a>", unsafe_allow_html=True)
                                else:
                                    st.markdown("<div class='custom-action-disabled'>📄 원문 없음</div>", unsafe_allow_html=True)
                                    
                            with c_l3:
                                if pdf_url:
                                    st.markdown(f"<a class='custom-action-btn' href='{pdf_url}' target='_blank' rel='noopener noreferrer'>📥 PDF 다운로드</a>", unsafe_allow_html=True)
                                else:
                                    st.markdown("<div class='custom-action-disabled'>📥 PDF 없음</div>", unsafe_allow_html=True)
                                    
                            with c_l4:
                                if st.button("🇰🇷 구글 번역", key=f"btn_trans_{i}_{paper.get('paperId', i)}", use_container_width=True):
                                    show_s2_abstract_dialog(p_title, p_abstract)

# [탭 3] 논문 파일 업로드 및 분석
with tabs[2]:
    st.subheader("🚀 논문 파일을 업로드 하세요.")
    st.caption("📂 파일을 올리면 동일 논문 유무를 자동으로 판단하여, 더 충실한 내용으로 스마트 업데이트되거나 신규 등록됩니다.")

    if 'uploader_key_counter' not in st.session_state:
        st.session_state['uploader_key_counter'] = 0

    if st.session_state.get('last_upload_summary'):
        summary = st.session_state.pop('last_upload_summary')
        st.success(summary['message'])
        if summary['logs']:
            with st.expander("📋 상세 처리 결과 로그 보기"):
                for log in summary['logs']:
                    st.write(log)
        if summary['new_entries']:
            st.dataframe(pd.DataFrame(summary['new_entries']), use_container_width=True)
    
    uploaded_files = st.file_uploader(
        "PDF 또는 Excel 파일을 선택하세요 (다중 선택 가능)", 
        accept_multiple_files=True,
        key=f"file_uploader_{st.session_state['uploader_key_counter']}",
        help="모바일 기기에서 파일이 보이지 않는 문제를 해결하기 위해 모든 파일 선택이 허용되도록 설정되었습니다. PDF(.pdf) 또는 엑셀(.xlsx) 파일을 선택해주세요."
    )

    # [추가] 자동 초기화가 기대만큼 안 될 경우를 대비한 수동 초기화 버튼.
    # 업로더 key를 강제로 바꿔서 완전히 새 위젯(빈 목록)으로 재생성한다.
    if uploaded_files:
        if st.button("🗑️ 선택 파일 목록 초기화", key="btn_clear_uploader"):
            st.session_state['uploader_key_counter'] += 1
            st.rerun()
    
    if st.button("파일 처리 및 마스터 DB에 누적 저장", type="primary"):
        if uploaded_files:
            master_df, sha = load_master_excel()
            current_max_no = 0
            if not master_df.empty and 'No.' in master_df.columns:
                valid_nos = pd.to_numeric(master_df['No.'], errors='coerce').dropna()
                if not valid_nos.empty:
                    current_max_no = int(valid_nos.max())

            new_entries = []
            updated_entries = {}
            processed_logs = []
            titles_seen_this_batch = set()
            
            with st.status("🔍 데이터를 스마트 분석하고 있습니다...", expanded=True) as status:
                for idx, file in enumerate(uploaded_files):
                    file_ext = file.name.split('.')[-1].lower()
                    
                    if file_ext in ['xlsx', 'xls']:
                        st.write(f"📊 [{idx+1}/{len(uploaded_files)}] '{file.name}' 엑셀 파일 데이터 병합 중...")
                        try:
                            excel_df = pd.read_excel(file)
                            if '메모' in excel_df.columns and '설문문항' not in excel_df.columns:
                                excel_df = excel_df.rename(columns={'메모': '설문문항'})
                                
                            drop_targets = ['상태', '권/호', '실무적 시사점', '국내/해외', '연구 주제/키워드', '메모', '연구 방법론']
                            excel_df = excel_df.drop(columns=[col for col in drop_targets if col in excel_df.columns], errors='ignore')
                            
                            for col in DB_COLUMNS:
                                if col not in excel_df.columns:
                                    excel_df[col] = "-"
                                    
                            excel_df = excel_df[DB_COLUMNS]
                            
                            for _, row in excel_df.iterrows():
                                row_dict = row.to_dict()
                                title = row_dict.get('논문/도서 제목', '')
                                norm_title = normalize_title(title)

                                if norm_title != "" and norm_title in titles_seen_this_batch:
                                    processed_logs.append(f"⏭️ [배지 중복 건너뜀] {title}")
                                    continue

                                existing_row = find_duplicate_row(title, master_df)
                                if existing_row is not None:
                                    existing_no = existing_row['No.']
                                    old_score = calculate_completeness(existing_row)
                                    new_score = calculate_completeness(row_dict)

                                    if new_score > old_score:
                                        row_dict['No.'] = existing_no
                                        updated_entries[existing_no] = row_dict
                                        processed_logs.append(f"🔄 [스마트 업데이트] No.{existing_no} '{title}' (기존 완성도 {old_score} ➔ 신규 {new_score})")
                                    else:
                                        processed_logs.append(f"⏭️ [기존 정보가 더 충실하여 유지] '{title}'")
                                    continue

                                current_max_no += 1
                                row_dict['No.'] = current_max_no
                                new_entries.append(row_dict)
                                if norm_title:
                                    titles_seen_this_batch.add(norm_title)
                                processed_logs.append(f"✅ [신규 등록] No.{current_max_no} '{title}'")

                            st.write(f"✅ '{file.name}' 엑셀 처리 완료!")
                        except Exception as e:
                            st.error(f"'{file.name}' 엑셀 읽기 오류: {str(e)}")

                    elif file_ext == 'pdf':
                        st.write(f"⏳ [{idx+1}/{len(uploaded_files)}] '{file.name}' PDF AI 심층 분석 중...")
                        try:
                            reader = PdfReader(file)
                            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                        except Exception as e:
                            st.error(f"'{file.name}' PDF 텍스트 추출 실패: {str(e)}")
                            continue
                            
                        if not text.strip():
                            st.warning(f"'{file.name}'에서 텍스트를 읽지 못했습니다. (스캔 이미지 PDF일 수 있음)")
                            continue

                        prompt = f"""
                        당신은 경영학 및 소비자 행동 연구 방법론 최고 전문가입니다.
                        아래 제공된 연구 논문 텍스트를 정밀 분석하여 다음 13개 항목을 JSON 형식으로 추출해주세요.
                        특히, 연구 방법론(Methodology) 및 부록(Appendix)을 꼼꼼히 살펴 변수별 측정 문항을 'survey_items'에 상세히 기재하세요.
                        (주의: 5점 척도, 7점 척도 등 점수 체계에 대한 설명은 절대 포함하지 말고 오직 문항만 작성하세요.)
                        (매우 중요: 설문 문항을 작성할 때는 각 문항마다 [영문 원문] 바로 아래 줄에 [국문 번역문]을 괄호로 감싸서 총 2줄 형태로 구성하세요. 예시:
                        - Consumers perceived high utility when using the AI service.
                        (소비자는 AI 서비스를 사용할 때 높은 유효성을 지각하였다.)
                        )
                        
                        추출 형식(JSON):
                        {{
                            "authors": "저자명 (예: 김완석, 유연재)",
                            "year": "발행 연도 (예: 2023)",
                            "title": "논문 제목",
                            "journal": "학술지명 (예: 마케팅연구)",
                            "theories": "핵심 이론 (예: 조절초점이론, 신호이론 등)",
                            "model": "연구 모형 요약 (예: [IV] -> [Mediator] -> [DV])",
                            "hypotheses": "가설 정리 (H1, H2 형식으로 줄바꿈 정리)",
                            "iv": "독립변수(IV)",
                            "dv": "종속변수(DV)",
                            "mediator": "매개변수(Mediator, 없으면 '-')",
                            "moderator": "조절변수(Moderator, 없으면 '-')",
                            "findings": "주요 발견(Key Findings)",
                            "survey_items": "변수별 측정에 사용된 실제 설문 문항 원문. 각 문항은 영문 아래에 (국문 번역)이 2줄 형태로 오도록 줄바꿈하여 작성 (척도/점수 체계 제외)",
                            "doi_or_url": "논문 원문에 표기된 DOI(예: 10.1086/209231) 또는 접근 가능한 URL. 없으면 '-'"
                        }}

                        [논문 원문 텍스트]:
                        {text[:100000]}
                        """
                        
                        try:
                            # [수정] model.generate_content() 직접 호출 대신
                            # generate_content_with_fallback() 사용 - 할당량 초과 시
                            # 자동으로 재시도하거나 다른 모델로 넘어감
                            response = generate_content_with_fallback(prompt)
                            res_json = parse_gemini_json(response.text)

                            pdf_title = res_json.get('title', file.name)
                            norm_title = normalize_title(pdf_title)

                            if norm_title != "" and norm_title in titles_seen_this_batch:
                                processed_logs.append(f"⏭️ [배지 중복 건너뜀] {pdf_title}")
                                continue

                            entry = {
                                '저자': res_json.get('authors', '-'),
                                '발행 연도': res_json.get('year', '-'),
                                '논문/도서 제목': pdf_title,
                                '학술지명/출처': res_json.get('journal', '-'),
                                '핵심 이론': res_json.get('theories', '-'),
                                '연구 모형': res_json.get('model', '-'),
                                '가설 정리': res_json.get('hypotheses', '-'),
                                '독립변수(IV)': res_json.get('iv', '-'),
                                '종속변수(DV)': res_json.get('dv', '-'),
                                '매개변수(Mediator)': res_json.get('mediator', '-'),
                                '조절변수(Moderator)': res_json.get('moderator', '-'),
                                '주요 발견(Key Findings)': res_json.get('findings', '-'),
                                '설문문항': res_json.get('survey_items', '-'),
                                '링크(DOI/URL)': res_json.get('doi_or_url', '-')
                            }

                            existing_row = find_duplicate_row(pdf_title, master_df)
                            if existing_row is not None:
                                existing_no = existing_row['No.']
                                old_score = calculate_completeness(existing_row)
                                new_score = calculate_completeness(entry)

                                if new_score > old_score:
                                    entry['No.'] = existing_no
                                    updated_entries[existing_no] = entry
                                    processed_logs.append(f"🔄 [스마트 업데이트] No.{existing_no} '{pdf_title}' (기존 완성도 {old_score} ➔ 신규 {new_score})")
                                else:
                                    processed_logs.append(f"⏭️ [기존 정보가 더 충실하여 유지] '{pdf_title}'")
                                continue

                            current_max_no += 1
                            entry['No.'] = current_max_no
                            new_entries.append(entry)
                            if norm_title:
                                titles_seen_this_batch.add(norm_title)
                            processed_logs.append(f"✅ [신규 등록] No.{current_max_no} '{pdf_title}'")
                            st.write(f"✅ '{file.name}' 분석 완료!")
                        except ResourceExhausted:
                            # [추가] 모든 폴백 모델까지 다 막힌 경우의 사용자 안내
                            st.error(f"'{file.name}' 분석 실패: Gemini API 할당량이 모두 소진되었습니다. "
                                     f"Google AI Studio에서 결제(빌링)를 활성화하시거나, 잠시(보통 다음날) 후 다시 시도해주세요.")
                        except NotFound:
                            # [추가] 폴백 목록의 모든 모델이 단종된 경우의 사용자 안내
                            st.error(f"'{file.name}' 분석 실패: 사용 가능한 Gemini 모델을 찾지 못했습니다 "
                                     f"(등록된 모델들이 모두 단종되었을 수 있습니다). GEMINI_MODEL_PRIORITY 목록을 "
                                     f"최신 모델명으로 업데이트해야 할 수 있습니다.")
                        except Exception as e:
                            st.error(f"'{file.name}' 분석 중 오류: {str(e)}")

                    else:
                        st.warning(f"⚠️ '{file.name}'은 지원하지 않는 파일 형식입니다. PDF(.pdf) 또는 엑셀(.xlsx) 파일만 업로드해주세요.")

                if new_entries or updated_entries:
                    updated_df = master_df.copy()

                    for dup_no, row_dict in updated_entries.items():
                        mask = updated_df['No.'] == dup_no
                        for k, v in row_dict.items():
                            if k == 'No.':
                                continue
                            updated_df.loc[mask, k] = v

                    if new_entries:
                        new_df = pd.DataFrame(new_entries)
                        updated_df = pd.concat([updated_df, new_df], ignore_index=True)

                    save_master_excel(updated_df, sha)
                    load_master_excel.clear()
                    status.update(label="전체 파일 처리 및 스마트 DB 저장 완료!", state="complete", expanded=False)

                    st.session_state['last_upload_summary'] = {
                        'message': f"신규 등록 {len(new_entries)}건, 스마트 업데이트 {len(updated_entries)}건이 완료되었습니다.",
                        'logs': processed_logs,
                        'new_entries': new_entries,
                    }
                    # [수정] 성공 직후 자동으로 업로더 key를 바꿔 목록을 비우던 로직을 제거.
                    # 이 자동 리마운트가 모바일(안드로이드 Chrome)에서 바로 이어지는 다중 파일
                    # 선택과 타이밍이 겹치면서, 새로 고른 파일이 아예 서버로 안 올라가는
                    # (파일 처리 버튼을 눌러도 "업로드할 파일을 선택해주세요"가 뜨는) 문제를 일으켰음.
                    # 목록이 안 지워지는 건 불편하지만, 파일 선택 자체가 안 되는 것보다는 낫기 때문에
                    # 자동 초기화는 끄고 아래의 수동 "선택 파일 목록 초기화" 버튼만 남긴다.
                    st.rerun()
                else:
                    status.update(label="추출/병합된 데이터 없음", state="error")
                    if processed_logs:
                        with st.expander("📋 상세 처리 결과 로그 보기"):
                            for log in processed_logs:
                                st.write(log)
        else:
            st.warning("업로드할 파일을 선택해주세요.")

# [탭 4] 관리자 전용 관리
if is_admin:
    with tabs[3]:
        st.subheader("⚙️ 관리자 전용 마스터 DB 관리")
        master_df, sha = load_master_excel()
        
        st.write(f"현재 DB 총 등록 건수: **{len(master_df)}건**")
        st.dataframe(master_df, use_container_width=True)
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("### 📥 마스터 엑셀 백업 다운로드")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                master_df.to_excel(writer, index=False, sheet_name='Sheet1')
            st.download_button(
                label="마스터 DB 원본 엑셀 다운로드",
                data=buffer.getvalue(),
                file_name="GBC_연구논문_마스터DB_백업.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
        with col_b:
            st.markdown("### 🗑️ 특정 논문 데이터 삭제")
            if not master_df.empty:
                del_target_no = st.selectbox("삭제할 No. 선택", master_df['No.'].tolist())
                if st.button("선택한 항목 영구 삭제", type="secondary"):
                    new_df = master_df[master_df['No.'] != del_target_no].reset_index(drop=True)
                    new_df['No.'] = range(1, len(new_df) + 1)
                    save_master_excel(new_df, sha)
                    load_master_excel.clear()
                    st.success(f"No. {del_target_no} 데이터가 삭제되었습니다. 페이지를 새로고침하세요.")

        st.divider()

        st.markdown("### 🧹 중복 논문 정리")
        st.caption("제목(공백·구두점·대소문자 무시)이 같은 논문을 찾아, 각 그룹에서 가장 내용이 충실한 항목 하나만 남기고 나머지를 삭제합니다.")

        def build_dup_plan(df):
            work = df.copy()
            work['_norm_title'] = work['논문/도서 제목'].astype(str).apply(normalize_title)
            check_cols = [c for c in DB_COLUMNS if c not in ('No.', '논문/도서 제목')]
            def completeness(row):
                score = 0
                for c in check_cols:
                    v = row.get(c, None)
                    if pd.notna(v) and str(v).strip() not in ('-', ''):
                        score += 1
                return score
            work['_완성도'] = work.apply(completeness, axis=1)

            groups = work[work['_norm_title'] != ''].groupby('_norm_title')
            keep_rows = []
            drop_rows = []
            group_previews = []
            for norm_title, g in groups:
                if len(g) <= 1:
                    continue
                g_sorted = g.sort_values(by=['_완성도', 'No.'], ascending=[False, True])
                keep = g_sorted.iloc[0]
                drops = g_sorted.iloc[1:]
                keep_rows.append(keep['No.'])
                drop_rows.extend(drops['No.'].tolist())
                group_previews.append({
                    'title': keep['논문/도서 제목'],
                    'keep_no': keep['No.'],
                    'drop_nos': drops['No.'].tolist(),
                    'keep_completeness': keep['_완성도'],
                    'drop_completeness': drops['_완성도'].tolist(),
                })
            return keep_rows, drop_rows, group_previews

        if st.button("🔍 중복 항목 미리보기", type="secondary"):
            keep_rows, drop_rows, previews = build_dup_plan(master_df)
            st.session_state['dup_preview'] = previews
            st.session_state['dup_drop_nos'] = drop_rows

        if st.session_state.get('dup_preview'):
            previews = st.session_state['dup_preview']
            drop_nos = st.session_state['dup_drop_nos']
            if not previews:
                st.info("중복으로 판단되는 논문이 없습니다.")
            else:
                st.warning(f"총 {len(previews)}개 그룹, {len(drop_nos)}건이 삭제 대상입니다. 삭제 전 아래 내용을 꼭 확인해주세요.")
                for p in previews:
                    with st.container(border=True):
                        st.markdown(f"**📄 {p['title']}**")
                        st.write(f"✅ 유지: No.{p['keep_no']} (완성도 {p['keep_completeness']}개 필드)")
                        for dno, dcomp in zip(p['drop_nos'], p['drop_completeness']):
                            st.write(f"🗑️ 삭제 예정: No.{dno} (완성도 {dcomp}개 필드)")

                if st.button("⚠️ 위 목록대로 중복 삭제 실행 (되돌릴 수 없음)", type="primary"):
                    load_master_excel.clear()
                    fresh_df, fresh_sha = load_master_excel()
                    cleaned = fresh_df[~fresh_df['No.'].isin(drop_nos)].reset_index(drop=True)
                    cleaned['No.'] = range(1, len(cleaned) + 1)
                    save_master_excel(cleaned, fresh_sha)
                    load_master_excel.clear()
                    st.success(f"중복 {len(drop_nos)}건을 삭제하고 No.를 다시 정렬했습니다. 페이지를 새로고침하세요.")
                    del st.session_state['dup_preview']
                    del st.session_state['dup_drop_nos']
