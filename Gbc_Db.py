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
import numpy as np
from scipy import stats as scipy_stats
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
import pingouin as pg

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
# [수정] 사용자가 직접 확인한 지원 모델 전체 목록으로 갱신 (2026년 8월 기준).
# 순서는 최신/저비용 Flash 모델을 우선하고, 안 되면 상위 Pro 모델,
# 마지막으로 2.5 구세대 모델까지 전부 시도하도록 구성.
GEMINI_MODEL_PRIORITY = [
    'gemini-3.6-flash',
    'gemini-3.7-flash',
    'gemini-3.5-flash',
    'gemini-3.5-flash-lite',
    'gemini-3.1-flash-lite',
    'gemini-3-flash',
    'gemini-3.1-pro',
    'gemini-2.5-pro',
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
]

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

def cronbach_alpha(df_items):
    """Cronbach's α 신뢰도 계수를 직접 계산 (외부 라이브러리 불필요)."""
    k = df_items.shape[1]
    item_vars = df_items.var(ddof=1)
    total_var = df_items.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return np.nan
    return (k / (k - 1)) * (1 - item_vars.sum() / total_var)

def item_total_analysis(df_items):
    """문항-총점 상관 및 해당 문항 삭제 시 α 변화표."""
    rows = []
    for col in df_items.columns:
        rest = df_items.drop(columns=[col])
        total_rest = rest.sum(axis=1)
        item_total_corr = df_items[col].corr(total_rest)
        alpha_if_deleted = cronbach_alpha(rest) if rest.shape[1] >= 2 else np.nan
        rows.append({'문항': col, '문항-총점 상관': item_total_corr, '삭제 시 α': alpha_if_deleted})
    return pd.DataFrame(rows)

def compute_kmo(corr_matrix):
    """KMO(Kaiser-Meyer-Olkin) 표본적합도. 요인분석 라이브러리(factor_analyzer)가
    최신 scikit-learn(1.6+)과 호환되지 않는 문제가 있어(내부에서 제거된
    force_all_finite 인자를 그대로 씀) 직접 구현."""
    inv_corr = np.linalg.inv(corr_matrix)
    d = np.sqrt(np.diag(inv_corr))
    partial_corr = -inv_corr / np.outer(d, d)
    np.fill_diagonal(partial_corr, 0)
    r_matrix = corr_matrix.copy()
    np.fill_diagonal(r_matrix, 0)
    sum_r2 = np.sum(r_matrix ** 2)
    sum_partial2 = np.sum(partial_corr ** 2)
    return sum_r2 / (sum_r2 + sum_partial2)

def bartlett_sphericity(corr_matrix, n):
    """Bartlett의 구형성 검정 (요인분석 적합성 판단용)."""
    p = corr_matrix.shape[0]
    det = np.linalg.det(corr_matrix)
    chi2 = -((n - 1) - (2 * p + 5) / 6) * np.log(det)
    df_free = p * (p - 1) / 2
    p_val = 1 - scipy_stats.chi2.cdf(chi2, df_free)
    return chi2, df_free, p_val

def varimax_rotation(loadings, gamma=1.0, max_iter=100, tol=1e-6):
    """Kaiser 베리맥스(varimax) 직교회전."""
    p, k = loadings.shape
    if k < 2:
        return loadings
    R = np.eye(k)
    d = 0
    for _ in range(max_iter):
        Lambda = loadings @ R
        u, s, vt = np.linalg.svd(
            loadings.T @ (Lambda ** 3 - (gamma / p) * Lambda @ np.diag(np.diag(Lambda.T @ Lambda)))
        )
        R = u @ vt
        d_new = np.sum(s)
        if d_new < d * (1 + tol):
            break
        d = d_new
    return loadings @ R

def simple_efa(df_items, n_factors=None):
    """탐색적 요인분석(EFA). 주성분 추출(Principal Component) + 베리맥스 회전.
    SPSS의 '요인분석' 기본 추출방식(주성분)과 동일한 방식."""
    n = len(df_items)
    corr = df_items.corr().values
    kmo = compute_kmo(corr)
    chi2, dfree, p_val = bartlett_sphericity(corr, n)

    eigvals, eigvecs = np.linalg.eigh(corr)
    order = np.argsort(eigvals)[::-1]
    eigvals, eigvecs = eigvals[order], eigvecs[:, order]

    if n_factors is None:
        n_factors = max(1, int(np.sum(eigvals > 1)))
    n_factors = min(n_factors, df_items.shape[1])

    loadings = eigvecs[:, :n_factors] * np.sqrt(np.maximum(eigvals[:n_factors], 0))
    if n_factors >= 2:
        loadings = varimax_rotation(loadings)
    communalities = np.sum(loadings ** 2, axis=1)

    return {
        'kmo': kmo, 'bartlett_chi2': chi2, 'bartlett_df': dfree, 'bartlett_p': p_val,
        'eigenvalues': eigvals, 'n_factors': n_factors,
        'loadings': pd.DataFrame(loadings, index=df_items.columns,
                                  columns=[f'요인{i + 1}' for i in range(n_factors)]),
        'communalities': pd.Series(communalities, index=df_items.columns),
    }

def guess_scale_type(series):
    """[수정] 컬럼의 척도 유형을 자동 추정 (연속형 vs 범주형).
    리커트 척도(5점/7점이 가장 흔함)는 서열척도지만 사회과학 통계 관행상
    등간척도(연속형)로 취급하는 게 표준이므로, 1~10 범위의 정수형이면서
    고유값이 5~9개인 경우는 리커트 척도로 보고 연속형으로 판단한다.
    - 고유값 2개(이분 조건/성별 등)는 명확히 범주형
    - 고유값 3~4개는 리커트로 보기엔 드문 범위라 범주형(집단조건 등)으로 유지
    - 그 외 고유값이 많으면(10개 초과 또는 전체의 20% 초과) 연속형
    완벽한 판별은 아니며 1차 추천용임."""
    n_total = series.notna().sum()
    if n_total == 0:
        return "알수없음"
    if not pd.api.types.is_numeric_dtype(series):
        return "범주형"

    n_unique = series.nunique(dropna=True)
    if n_unique <= 2:
        return "범주형"

    values = series.dropna().unique()
    is_int_like = np.all(np.isclose(values, np.round(values)))
    if is_int_like and 5 <= n_unique <= 9 and values.min() >= 1 and values.max() <= 10:
        return "연속형"

    if n_unique > 10 or n_unique > n_total * 0.2:
        return "연속형"
    return "범주형"


def _pg_col(df, *candidates):
    """[추가] pingouin 라이브러리 버전에 따라 결과 컬럼명이
    'p-val'/'p_val', 'cohen-d'/'cohen_d', 'mean(A)'/'mean_A' 등으로 갈리기 때문에,
    실제 설치된 버전에 있는 이름을 찾아서 반환한다."""
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"{candidates} 중 어느 것도 컬럼에 없습니다: {list(df.columns)}")

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

# [수정] 예열(warm-up) 트리거를 tab2 안쪽이 아니라 여기(탭 생성 전)로 옮김.
# 이전 위치에서는 tab0/1의 위젯은 예열 '전'에, tab2/3/4의 위젯은 예열 '후'에
# 렌더링되는 불균형이 있었음. 여기로 옮기면 모든 탭의 모든 위젯이
# 예외 없이 예열 완료 이후에만 첫 렌더링되어, 파일 업로더가 여러 탭에
# 흩어져 있어도 동일하게 보호된다.
if not st.session_state.get('_app_warmed_up', False):
    st.session_state['_app_warmed_up'] = True
    st.rerun()

tab_names = ["🔍 연구 논문 DB 검색", "🌐 Semantic Scholar 검색", "🚀 논문 파일 업로드", "📊 통계 분석 (파일럿)"]
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

# [탭 4] 통계 분석 (파일럿 테스트)
with tabs[3]:
    st.subheader("📊 통계 분석 (파일럿 테스트)")
    st.warning(
        "⚠️ 이 도구는 **파일럿 테스트/사전 점검용**입니다. 정식 논문에 쓰실 분석은 "
        "반드시 SPSS 등 검증된 통계 소프트웨어로 다시 진행하시길 권장합니다."
    )

    stat_file = st.file_uploader(
        "분석할 데이터 파일 (CSV 또는 엑셀, 1행 = 응답자 1명)",
        type=['csv', 'xlsx', 'xls'],
        key="stat_data_uploader"
    )

    # [추가] 파일을 고르는 즉시 자동으로 읽어들이지 않고, 버튼을 눌러야
    # 실제 분석 화면이 시작되도록 함.
    if stat_file is not None:
        if st.button("▶️ 분석 시작 (파일 불러오기)", type="primary", key="btn_start_stat_analysis"):
            st.session_state['stat_analysis_started'] = True
    else:
        st.session_state['stat_analysis_started'] = False

    if stat_file is not None and st.session_state.get('stat_analysis_started'):
        try:
            if stat_file.name.lower().endswith('.csv'):
                stat_df = pd.read_csv(stat_file)
            else:
                stat_df = pd.read_excel(stat_file)
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
            stat_df = None

        if stat_df is not None and not stat_df.empty:
            st.success(f"✅ {len(stat_df)}행 × {len(stat_df.columns)}열 데이터를 불러왔습니다.")
            with st.expander("📋 데이터 미리보기"):
                st.dataframe(stat_df.head(20), use_container_width=True)

            numeric_cols = stat_df.select_dtypes(include=[np.number]).columns.tolist()
            all_cols = stat_df.columns.tolist()

            # -----------------------------------------------------
            # [추가] 척도 유형 기반 분석 추천 가이드
            # -----------------------------------------------------
            with st.expander("🧭 어떤 분석을 써야 할지 모르겠다면 - 변수 골라서 추천받기", expanded=False):
                st.caption("종속변수와 독립변수를 골라주시면, 두 변수의 척도 유형(연속형/범주형)을 "
                           "자동으로 판단해서 적합한 분석을 추천해드립니다. "
                           "(5~9점 사이 정수 응답은 리커트 척도로 보고 연속형으로 처리합니다.)")
                gc1, gc2 = st.columns(2)
                with gc1:
                    guide_dv = st.selectbox("종속변수(DV)", all_cols, key="guide_dv")
                with gc2:
                    guide_iv = st.multiselect("독립변수(IV) - 1~2개 선택", all_cols, key="guide_iv")

                if guide_dv and guide_iv:
                    auto_dv_type = guess_scale_type(stat_df[guide_dv])
                    st.markdown(f"##### 척도 유형 확인 (자동판단 기본값 · 필요시 수정 가능)")

                    dc1, dc2 = st.columns([2, 3])
                    with dc1:
                        st.write(f"**{guide_dv}** (DV)")
                        st.caption(f"자동판단: {auto_dv_type}")
                    with dc2:
                        dv_type = st.radio(
                            f"{guide_dv} 척도 유형", ["연속형", "범주형"],
                            index=0 if auto_dv_type == "연속형" else 1,
                            horizontal=True, key="guide_dv_type_override", label_visibility="collapsed"
                        )

                    iv_types = {}
                    n_groups = {c: stat_df[c].nunique(dropna=True) for c in guide_iv}
                    for c in guide_iv:
                        auto_type = guess_scale_type(stat_df[c])
                        ic1, ic2 = st.columns([2, 3])
                        with ic1:
                            st.write(f"**{c}** (IV)")
                            extra = f", 그룹 수 {n_groups[c]}개" if auto_type == "범주형" else ""
                            st.caption(f"자동판단: {auto_type}{extra}")
                        with ic2:
                            iv_types[c] = st.radio(
                                f"{c} 척도 유형", ["연속형", "범주형"],
                                index=0 if auto_type == "연속형" else 1,
                                horizontal=True, key=f"guide_iv_type_override_{c}", label_visibility="collapsed"
                            )

                    st.divider()

                    if dv_type != "연속형":
                        st.warning("종속변수가 범주형으로 감지되었습니다. 이 통계 탭은 현재 "
                                   "연속형 종속변수를 전제로 한 t-검정/ANOVA/회귀분석만 지원합니다. "
                                   "(카이제곱검정·로지스틱회귀는 아직 준비되지 않았습니다.)")
                    elif len(guide_iv) == 1 and iv_types[guide_iv[0]] == "범주형":
                        g = n_groups[guide_iv[0]]
                        if g == 2:
                            st.success("💡 추천: **독립표본 t-검정** (연속형 DV + 2개 그룹 범주형 IV)")
                        elif g >= 3:
                            st.success("💡 추천: **일원분산분석(One-way ANOVA)** (연속형 DV + 3개 이상 그룹 범주형 IV)")
                        else:
                            st.error("선택한 독립변수의 그룹이 1개뿐입니다. 그룹이 2개 이상인 변수를 선택해주세요.")
                    elif len(guide_iv) == 2 and all(iv_types[c] == "범주형" for c in guide_iv):
                        st.success("💡 추천: **이원분산분석(Two-way ANOVA)** (연속형 DV + 범주형 IV 2개, 상호작용효과까지 확인 가능)")
                    elif all(iv_types[c] == "연속형" for c in guide_iv):
                        st.success("💡 추천: **회귀분석** (연속형 DV + 연속형 IV)")
                        st.caption("↳ 다문항 설문 척도를 그대로 넣기 전에, 아래 '신뢰도분석/요인분석'으로 "
                                   "먼저 문항을 하나의 변수로 축소하시는 걸 권장합니다.")
                    else:
                        st.info("연속형과 범주형 독립변수가 섞여 있습니다. 이 경우 공분산분석(ANCOVA)이 "
                                "적합하지만 아직 이 탭에서 지원하지 않습니다. 범주형 변수만으로 ANOVA를, "
                                "또는 연속형 변수만으로 회귀분석을 별도로 진행해보세요.")

            analysis_type = st.selectbox(
                "🔬 분석 유형 선택",
                ["신뢰도분석 (Cronbach's α)", "탐색적 요인분석 (EFA)",
                 "독립표본 t-검정", "일원분산분석 (One-way ANOVA)",
                 "이원분산분석 (Two-way ANOVA / 2×2 요인설계)", "회귀분석 (다중회귀)"]
            )

            st.divider()

            # ---------------------------------------------------------
            # 0-A) 신뢰도분석 (Cronbach's α)
            # ---------------------------------------------------------
            if analysis_type == "신뢰도분석 (Cronbach's α)":
                st.caption("💡 회귀분석·ANOVA 등에 변수를 넣기 전, 같은 구성개념(construct)을 측정하는 "
                           "여러 문항이 일관되게 응답되었는지 먼저 확인하는 단계입니다.")
                item_cols = st.multiselect("같은 구성개념을 측정하는 문항들 선택 (3개 이상 권장)", numeric_cols, key="alpha_items")

                if st.button("▶️ 신뢰도분석 실행", type="primary", key="btn_run_alpha"):
                    if len(item_cols) < 2:
                        st.error("문항을 2개 이상 선택해주세요.")
                    else:
                        work = stat_df[item_cols].dropna()
                        alpha = cronbach_alpha(work)
                        st.markdown("##### 📋 전체 신뢰도")
                        st.dataframe(pd.DataFrame({'문항 수': [len(item_cols)], 'N': [len(work)], "Cronbach's α": [alpha]})
                                     .style.format({"Cronbach's α": '{:.3f}'}), use_container_width=True)

                        st.markdown("##### 📋 문항-총점 분석")
                        item_table = item_total_analysis(work)
                        st.dataframe(item_table.style.format({'문항-총점 상관': '{:.3f}', '삭제 시 α': '{:.3f}'}),
                                     use_container_width=True)

                        level = "우수" if alpha >= 0.9 else ("양호" if alpha >= 0.8 else ("수용 가능" if alpha >= 0.7 else "낮음 - 재검토 필요"))
                        low_items = item_table[item_table['문항-총점 상관'] < 0.3]['문항'].tolist()
                        msg = f"**해석**: 전체 신뢰도 α = {alpha:.3f}로 **{level}** 수준입니다 (통상 α ≥ .70을 기준으로 봅니다)."
                        if low_items:
                            msg += f" 문항-총점 상관이 낮은(.30 미만) 문항: {', '.join(low_items)} — 삭제를 고려해볼 수 있습니다."
                        st.info(msg)

            # ---------------------------------------------------------
            # 0-B) 탐색적 요인분석 (EFA)
            # ---------------------------------------------------------
            elif analysis_type == "탐색적 요인분석 (EFA)":
                st.caption("💡 여러 문항이 실제로 몇 개의 하위요인(개념)으로 나뉘는지 확인하는 단계입니다. "
                           "이미 검증된 척도를 그대로 쓰신다면 생략하셔도 됩니다.")
                efa_items = st.multiselect("요인분석할 문항들 선택 (최소 4개 이상 권장)", numeric_cols, key="efa_items")
                auto_n = st.checkbox("요인 수 자동 결정 (고유값 > 1 기준, Kaiser 기준)", value=True, key="efa_auto_n")
                manual_n = None
                if not auto_n:
                    manual_n = st.number_input("추출할 요인 수 직접 지정", min_value=1, max_value=10, value=2, key="efa_manual_n")

                if st.button("▶️ 요인분석 실행", type="primary", key="btn_run_efa"):
                    if len(efa_items) < 3:
                        st.error("문항을 3개 이상 선택해주세요.")
                    else:
                        work = stat_df[efa_items].dropna()
                        result = simple_efa(work, n_factors=None if auto_n else int(manual_n))

                        st.markdown("##### 📋 표본적합도")
                        kmo_level = "매우 좋음" if result['kmo'] >= 0.9 else ("좋음" if result['kmo'] >= 0.8 else
                                    ("보통" if result['kmo'] >= 0.7 else ("평범" if result['kmo'] >= 0.6 else "부적합")))
                        st.dataframe(pd.DataFrame({
                            'KMO': [result['kmo']], 'KMO 판정': [kmo_level],
                            'Bartlett χ²': [result['bartlett_chi2']], 'df': [result['bartlett_df']],
                            'p': [result['bartlett_p']]
                        }).style.format({'KMO': '{:.3f}', 'Bartlett χ²': '{:.2f}', 'df': '{:.0f}', 'p': '{:.5f}'}),
                            use_container_width=True)

                        st.markdown("##### 📋 고유값(Eigenvalues) - Kaiser 기준(>1) 요인 수 판단")
                        eig_table = pd.DataFrame({
                            '요인': [f'{i+1}' for i in range(len(result['eigenvalues']))],
                            '고유값': result['eigenvalues'],
                        })
                        st.dataframe(eig_table.style.format({'고유값': '{:.3f}'}), use_container_width=True)
                        st.caption(f"↳ 추출된 요인 수: {result['n_factors']}개")

                        st.markdown("##### 📋 요인적재량 (베리맥스 회전 후)")
                        st.dataframe(result['loadings'].style.format('{:.3f}').background_gradient(
                            cmap='Blues', vmin=0, vmax=1, axis=None
                        ), use_container_width=True)

                        st.markdown("##### 📋 공통성 (Communalities)")
                        st.dataframe(result['communalities'].to_frame('공통성').style.format({'공통성': '{:.3f}'}),
                                     use_container_width=True)

                        kmo_txt = "요인분석에 적합한 데이터입니다" if result['kmo'] >= 0.6 else "요인분석에 적합하지 않을 수 있습니다 (KMO < .6)"
                        bartlett_txt = "유의하여 요인분석이 타당합니다" if result['bartlett_p'] < 0.05 else "유의하지 않아 요인분석이 부적절할 수 있습니다"
                        st.info(
                            f"**해석**: KMO = {result['kmo']:.3f}로 {kmo_txt}. "
                            f"Bartlett 구형성 검정은 p = {result['bartlett_p']:.4f}로 **{bartlett_txt}**. "
                            f"Kaiser 기준(고유값 > 1)으로 {result['n_factors']}개 요인이 추출되었습니다. "
                            f"각 문항은 적재량이 가장 높은 요인에 속한다고 해석하며, 보통 .40 이상을 유의미한 적재량으로 봅니다."
                        )

            # ---------------------------------------------------------
            # 1) 독립표본 t-검정
            # ---------------------------------------------------------
            elif analysis_type == "독립표본 t-검정":
                st.markdown("#### ⚙️ 변수 설정")
                c1, c2 = st.columns(2)
                with c1:
                    dv_col = st.selectbox("종속변수 (연속형)", numeric_cols, key="ttest_dv")
                with c2:
                    group_col = st.selectbox("집단변수 (그룹 2개)", [c for c in all_cols if c != dv_col], key="ttest_group")

                if st.button("▶️ t-검정 실행", type="primary", key="btn_run_ttest"):
                    groups = stat_df[group_col].dropna().unique()
                    if len(groups) != 2:
                        st.error(f"집단변수는 정확히 2개 그룹이어야 합니다. 현재 {len(groups)}개 그룹입니다: {list(groups)}")
                    else:
                        g1_name, g2_name = groups[0], groups[1]
                        g1 = stat_df.loc[stat_df[group_col] == g1_name, dv_col].dropna()
                        g2 = stat_df.loc[stat_df[group_col] == g2_name, dv_col].dropna()

                        desc_table = pd.DataFrame({
                            '집단': [str(g1_name), str(g2_name)],
                            'N': [len(g1), len(g2)],
                            '평균': [g1.mean(), g2.mean()],
                            '표준편차': [g1.std(), g2.std()],
                            '표준오차': [g1.sem(), g2.sem()],
                        })
                        st.markdown("##### 📋 집단기술통계량")
                        st.dataframe(desc_table.style.format(
                            {'평균': '{:.3f}', '표준편차': '{:.3f}', '표준오차': '{:.3f}'}
                        ), use_container_width=True)

                        levene_stat, levene_p = scipy_stats.levene(g1, g2)
                        equal_var = levene_p > 0.05
                        st.markdown("##### 📋 등분산 검정 (Levene)")
                        st.dataframe(pd.DataFrame({
                            'F': [levene_stat], 'p': [levene_p],
                            '등분산 가정': ['가정됨 (등분산 t 사용)' if equal_var else '가정 안 됨 (Welch t 사용)']
                        }).style.format({'F': '{:.3f}', 'p': '{:.3f}'}), use_container_width=True)

                        pg_result = pg.ttest(g1, g2, correction=not equal_var)
                        col_p = _pg_col(pg_result, 'p-val', 'p_val')
                        col_d = _pg_col(pg_result, 'cohen-d', 'cohen_d')
                        col_power = _pg_col(pg_result, 'power')
                        st.markdown("##### 📋 t-검정 결과")
                        st.dataframe(pg_result.style.format({
                            'T': '{:.3f}', 'dof': '{:.2f}', col_p: '{:.4f}',
                            col_d: '{:.3f}', col_power: '{:.3f}'
                        }), use_container_width=True)

                        t_val = pg_result['T'].iloc[0]
                        p_val = pg_result[col_p].iloc[0]
                        dof = pg_result['dof'].iloc[0]
                        d_val = pg_result[col_d].iloc[0]
                        sig_txt = "통계적으로 유의합니다" if p_val < 0.05 else "통계적으로 유의하지 않습니다"
                        st.info(
                            f"**해석**: {g1_name} 집단(M={g1.mean():.2f}, SD={g1.std():.2f})과 "
                            f"{g2_name} 집단(M={g2.mean():.2f}, SD={g2.std():.2f}) 간 평균 차이는 "
                            f"t({dof:.1f}) = {t_val:.3f}, p = {p_val:.3f}로 **{sig_txt}** (p {'<' if p_val < 0.05 else '≥'} .05). "
                            f"효과크기(Cohen's d = {d_val:.3f})는 "
                            f"{'작은' if abs(d_val) < 0.5 else ('중간' if abs(d_val) < 0.8 else '큰')} 편입니다."
                        )

            # ---------------------------------------------------------
            # 2) 일원분산분석
            # ---------------------------------------------------------
            elif analysis_type == "일원분산분석 (One-way ANOVA)":
                st.markdown("#### ⚙️ 변수 설정")
                c1, c2 = st.columns(2)
                with c1:
                    dv_col = st.selectbox("종속변수 (연속형)", numeric_cols, key="anova1_dv")
                with c2:
                    factor_col = st.selectbox("요인(집단)변수 (3개 이상 그룹 권장)", [c for c in all_cols if c != dv_col], key="anova1_factor")

                if st.button("▶️ 일원분산분석 실행", type="primary", key="btn_run_anova1"):
                    work = stat_df[[dv_col, factor_col]].dropna()
                    groups = work[factor_col].unique()
                    if len(groups) < 2:
                        st.error("요인변수에 그룹이 2개 이상 있어야 합니다.")
                    else:
                        desc = work.groupby(factor_col)[dv_col].agg(['count', 'mean', 'std']).reset_index()
                        desc.columns = ['집단', 'N', '평균', '표준편차']
                        st.markdown("##### 📋 집단별 기술통계량")
                        st.dataframe(desc.style.format({'평균': '{:.3f}', '표준편차': '{:.3f}'}), use_container_width=True)

                        aov = pg.anova(data=work, dv=dv_col, between=factor_col, detailed=True)
                        st.markdown("##### 📋 분산분석표 (ANOVA)")
                        st.dataframe(aov.style.format({
                            'SS': '{:.3f}', 'MS': '{:.3f}', 'F': '{:.3f}', 'p_unc': '{:.4f}', 'np2': '{:.3f}'
                        }, na_rep='-'), use_container_width=True)

                        f_val = aov['F'].iloc[0]
                        p_val = aov['p_unc'].iloc[0]
                        eta2 = aov['np2'].iloc[0]
                        df1, df2 = aov['DF'].iloc[0], aov['DF'].iloc[1]
                        sig_txt = "통계적으로 유의한 차이가 있습니다" if p_val < 0.05 else "통계적으로 유의한 차이가 없습니다"
                        st.info(
                            f"**해석**: {factor_col}에 따른 {dv_col}의 평균은 F({df1:.0f}, {df2:.0f}) = {f_val:.3f}, "
                            f"p = {p_val:.3f}로 집단 간 **{sig_txt}** (p {'<' if p_val < 0.05 else '≥'} .05). "
                            f"효과크기(partial η² = {eta2:.3f})."
                        )

                        if p_val < 0.05 and len(groups) > 2:
                            st.markdown("##### 📋 사후검정 (Tukey HSD)")
                            posthoc = pg.pairwise_tukey(data=work, dv=dv_col, between=factor_col)
                            col_meanA = _pg_col(posthoc, 'mean(A)', 'mean_A')
                            col_meanB = _pg_col(posthoc, 'mean(B)', 'mean_B')
                            col_ptukey = _pg_col(posthoc, 'p-tukey', 'p_tukey', 'p-corr', 'p_corr')
                            st.dataframe(posthoc.style.format(
                                {col_meanA: '{:.3f}', col_meanB: '{:.3f}', 'diff': '{:.3f}',
                                 'se': '{:.3f}', 'T': '{:.3f}', col_ptukey: '{:.4f}'}
                            ), use_container_width=True)
                            st.caption("↳ 유의(p < .05)한 쌍이 실제로 서로 다른 집단입니다.")

            # ---------------------------------------------------------
            # 3) 이원분산분석 (2×2 요인설계)
            # ---------------------------------------------------------
            elif analysis_type == "이원분산분석 (Two-way ANOVA / 2×2 요인설계)":
                st.markdown("#### ⚙️ 변수 설정")
                c1, c2, c3 = st.columns(3)
                with c1:
                    dv_col = st.selectbox("종속변수 (연속형)", numeric_cols, key="anova2_dv")
                with c2:
                    factor1_col = st.selectbox("요인 1", [c for c in all_cols if c != dv_col], key="anova2_f1")
                with c3:
                    factor2_col = st.selectbox("요인 2", [c for c in all_cols if c != dv_col and c != factor1_col], key="anova2_f2")

                if st.button("▶️ 이원분산분석 실행", type="primary", key="btn_run_anova2"):
                    if factor1_col == factor2_col:
                        st.error("요인 1과 요인 2는 서로 다른 변수를 선택해주세요.")
                    else:
                        work = stat_df[[dv_col, factor1_col, factor2_col]].dropna()

                        desc = work.groupby([factor1_col, factor2_col])[dv_col].agg(['count', 'mean', 'std']).reset_index()
                        desc.columns = [factor1_col, factor2_col, 'N', '평균', '표준편차']
                        st.markdown("##### 📋 셀별(요인 조합별) 기술통계량")
                        st.dataframe(desc.style.format({'평균': '{:.3f}', '표준편차': '{:.3f}'}), use_container_width=True)

                        aov2 = pg.anova(data=work, dv=dv_col, between=[factor1_col, factor2_col], detailed=True)
                        st.markdown("##### 📋 분산분석표 (주효과 + 상호작용효과)")
                        st.dataframe(aov2.style.format({
                            'SS': '{:.3f}', 'MS': '{:.3f}', 'F': '{:.3f}', 'p_unc': '{:.4f}', 'np2': '{:.3f}'
                        }, na_rep='-'), use_container_width=True)

                        interaction_row = aov2[aov2['Source'].str.contains(r'\*', regex=True)]
                        if not interaction_row.empty:
                            p_int = interaction_row['p_unc'].iloc[0]
                            f_int = interaction_row['F'].iloc[0]
                            int_sig = "유의한 상호작용효과가 있습니다" if p_int < 0.05 else "유의한 상호작용효과가 없습니다"
                            st.info(
                                f"**해석 (상호작용)**: {factor1_col} × {factor2_col} 상호작용은 "
                                f"F = {f_int:.3f}, p = {p_int:.3f}로 **{int_sig}** (p {'<' if p_int < 0.05 else '≥'} .05). "
                                + ("상호작용이 유의하므로, 두 요인의 주효과를 개별 해석하기보다 "
                                   "단순주효과분석(simple effects) 또는 조건별 평균 그래프로 패턴을 먼저 확인하시길 권장합니다."
                                   if p_int < 0.05 else
                                   "상호작용이 유의하지 않으므로 각 요인의 주효과를 독립적으로 해석하셔도 무방합니다.")
                            )

                        st.markdown("##### 📊 셀 평균 그래프 (상호작용 패턴 확인용)")
                        pivot = work.groupby([factor1_col, factor2_col])[dv_col].mean().reset_index()
                        chart_series = []
                        f2_values = pivot[factor2_col].unique()
                        f1_values = sorted(pivot[factor1_col].unique().tolist(), key=str)
                        for f2v in f2_values:
                            sub = pivot[pivot[factor2_col] == f2v].set_index(factor1_col).reindex(f1_values)
                            chart_series.append({
                                "name": f"{factor2_col}={f2v}",
                                "values": [str(round(v, 3)) if pd.notna(v) else "0" for v in sub[dv_col]]
                            })
                        st.line_chart(pivot.pivot(index=factor1_col, columns=factor2_col, values=dv_col))

            # ---------------------------------------------------------
            # 4) 회귀분석
            # ---------------------------------------------------------
            elif analysis_type == "회귀분석 (다중회귀)":
                st.markdown("#### ⚙️ 변수 설정")
                c1, c2 = st.columns(2)
                with c1:
                    dv_col = st.selectbox("종속변수 (연속형)", numeric_cols, key="reg_dv")
                with c2:
                    # [수정] 이전에는 numeric_cols(숫자형)만 독립변수로 고를 수 있어서
                    # 범주형(문자열) 변수는 선택지에 아예 안 나타났음.
                    # 이제 전체 컬럼을 고를 수 있게 하고, 범주형이면 자동으로 더미변수로 변환한다.
                    iv_cols = st.multiselect(
                        "독립변수 (1개 이상 선택, 범주형도 선택 가능 - 자동으로 더미변수 처리됨)",
                        [c for c in all_cols if c != dv_col],
                        key="reg_iv"
                    )

                if iv_cols:
                    iv_type_preview = {c: guess_scale_type(stat_df[c]) for c in iv_cols}
                    preview_txt = " / ".join([f"{c}({t})" for c, t in iv_type_preview.items()])
                    st.caption(f"🔎 척도 판단: {preview_txt}")

                if st.button("▶️ 회귀분석 실행", type="primary", key="btn_run_reg"):
                    if not iv_cols:
                        st.error("독립변수를 1개 이상 선택해주세요.")
                    else:
                        work = stat_df[[dv_col] + iv_cols].dropna()

                        # [추가] 독립변수별 척도 유형 판단 -> 범주형은 더미변수(가변수)로 변환
                        design_parts = []
                        continuous_iv_cols = []   # 표준화계수 계산 시 그대로 표준화할 변수
                        dummy_ref_notes = []      # 해석 문장에 쓸 "기준집단" 안내
                        for c in iv_cols:
                            scale = guess_scale_type(work[c])
                            if scale == "범주형":
                                dummies = pd.get_dummies(work[c], prefix=c, drop_first=True, dtype=float)
                                all_categories = sorted(work[c].dropna().unique().tolist(), key=str)
                                dummy_categories = [col.split(f"{c}_", 1)[1] for col in dummies.columns]
                                ref_category = [cat for cat in all_categories if str(cat) not in dummy_categories]
                                ref_category = ref_category[0] if ref_category else all_categories[0]
                                dummy_ref_notes.append(f"{c}(기준집단: {ref_category})")
                                design_parts.append(dummies)
                            else:
                                design_parts.append(work[[c]])
                                continuous_iv_cols.append(c)

                        X_design = pd.concat(design_parts, axis=1)
                        final_iv_names = list(X_design.columns)
                        X = sm.add_constant(X_design)
                        y = work[dv_col]
                        reg_model = sm.OLS(y, X).fit()

                        if dummy_ref_notes:
                            st.caption(f"📌 범주형 변수는 더미코딩되었습니다 — {', '.join(dummy_ref_notes)} "
                                       f"(계수는 기준집단 대비 차이로 해석)")

                        st.markdown("##### 📋 모델 요약")
                        r_val = np.sqrt(reg_model.rsquared)
                        summary_table = pd.DataFrame({
                            'R': [r_val], 'R²': [reg_model.rsquared],
                            '수정된 R²': [reg_model.rsquared_adj],
                            '표준오차(SE)': [np.sqrt(reg_model.mse_resid)]
                        })
                        st.dataframe(summary_table.style.format('{:.3f}'), use_container_width=True)

                        st.markdown("##### 📋 분산분석표 (ANOVA)")
                        anova_reg = pd.DataFrame({
                            '': ['회귀', '잔차', '전체'],
                            '제곱합': [reg_model.ess, reg_model.ssr, reg_model.ess + reg_model.ssr],
                            '자유도': [reg_model.df_model, reg_model.df_resid, reg_model.df_model + reg_model.df_resid],
                            'F': [reg_model.fvalue, None, None],
                            'p': [reg_model.f_pvalue, None, None],
                        })
                        st.dataframe(anova_reg.style.format(
                            {'제곱합': '{:.3f}', '자유도': '{:.0f}', 'F': '{:.3f}', 'p': '{:.4f}'}, na_rep='-'
                        ), use_container_width=True)

                        st.markdown("##### 📋 계수표")
                        # [수정] 표준화계수는 원래 연속형 변수의 의미(1SD 변화당 효과)를 갖기 때문에,
                        # 더미(0/1) 변수까지 포함해서 표준화해도 계산은 되지만 해석이 애매해질 수 있음.
                        # 그래도 SPSS 등 실무 관행에 맞춰 전체 변수(더미 포함)를 표준화해 함께 제공하되,
                        # 더미 변수의 표준화계수는 해석 시 주의가 필요하다는 점을 안내한다.
                        std_work = pd.concat([y, X_design], axis=1).copy()
                        for col in std_work.columns:
                            sd = std_work[col].std()
                            std_work[col] = (std_work[col] - std_work[col].mean()) / sd if sd not in (0, None) else 0
                        X_std = std_work[final_iv_names]
                        y_std = std_work[dv_col]
                        beta_model = sm.OLS(y_std, X_std).fit()

                        vif_vals = ["-"] + [
                            round(variance_inflation_factor(X.values, i), 3)
                            for i in range(1, X.shape[1])
                        ]
                        coef_table = pd.DataFrame({
                            '변수': ['(상수)'] + final_iv_names,
                            'B': reg_model.params.values,
                            'SE': reg_model.bse.values,
                            'β(표준화)': [None] + list(beta_model.params.values),
                            't': reg_model.tvalues.values,
                            'p': reg_model.pvalues.values,
                            'VIF': vif_vals,
                        })
                        st.dataframe(coef_table.style.format(
                            {'B': '{:.3f}', 'SE': '{:.3f}', 'β(표준화)': '{:.3f}', 't': '{:.3f}', 'p': '{:.4f}'},
                            na_rep='-'
                        ), use_container_width=True)
                        if len(final_iv_names) > len(iv_cols):
                            st.caption("↳ 더미변수의 표준화계수(β)는 '1표준편차 변화당 효과'라는 원래 의미가 "
                                       "잘 들어맞지 않을 수 있어 참고용으로만 봐주세요. B(비표준화계수)가 더 정확한 해석입니다.")

                        sig_txt = "통계적으로 유의합니다" if reg_model.f_pvalue < 0.05 else "통계적으로 유의하지 않습니다"
                        high_vif = [v for v, x in zip(vif_vals[1:], final_iv_names) if isinstance(v, (int, float)) and v > 10]
                        st.info(
                            f"**해석**: 회귀모형은 F({reg_model.df_model:.0f}, {reg_model.df_resid:.0f}) = "
                            f"{reg_model.fvalue:.3f}, p = {reg_model.f_pvalue:.3f}로 **{sig_txt}** "
                            f"(p {'<' if reg_model.f_pvalue < 0.05 else '≥'} .05). "
                            f"독립변수들은 종속변수 분산의 {reg_model.rsquared*100:.1f}%를 설명합니다(R² = {reg_model.rsquared:.3f}). "
                            + (f"⚠️ VIF가 10을 넘는 변수({', '.join(map(str, high_vif))})가 있어 다중공선성을 의심해볼 필요가 있습니다."
                               if high_vif else "VIF는 모두 10 미만으로 다중공선성 문제는 크지 않아 보입니다.")
                        )
        elif stat_df is not None:
            st.warning("업로드한 파일에 데이터가 없습니다.")
    elif stat_file is not None:
        st.info("파일이 선택되었습니다. 위의 '▶️ 분석 시작' 버튼을 눌러주세요.")
    else:
        st.info("CSV 또는 엑셀 파일을 업로드하면 t-검정 · 분산분석 · 회귀분석을 실행할 수 있습니다.")

# [탭 4] 관리자 전용 관리
if is_admin:
    with tabs[4]:
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
