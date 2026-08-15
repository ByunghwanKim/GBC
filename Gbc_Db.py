import streamlit as st
import pandas as pd
import json
import io
import base64
import html
import textwrap
import google.generativeai as genai
from pypdf import PdfReader
from github import Github
from github.GithubException import UnknownObjectException

# 1. 페이지 설정
st.set_page_config(page_title="GBC 연구 논문 DB 관리 시스템", page_icon="📚", layout="wide")

# CSS: 폰트 및 UI 스타일 정의 (내부 폰트 아이콘 텍스트 노출 원천 차단)
# [수정] Streamlit의 st.markdown()은 unsafe_allow_html=True를 줘도 내부적으로
# Markdown 파서(react-markdown)를 거치는데, Markdown 스펙상 "공백 4칸 이상 들여쓰기된 줄"은
# 코드 블록으로 인식되어 CSS가 적용되지 않고 그대로 텍스트로 화면에 노출된다.
# 따라서 CSS 문자열은 반드시 왼쪽 정렬(들여쓰기 없음)로 작성하고, textwrap.dedent()로
# 한 번 더 안전하게 들여쓰기를 제거한다.
custom_css = textwrap.dedent("""\
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

html, body, [class*="st-"] {
font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important;
}

/* Material Symbols 아이콘(드롭다운 화살표, 비밀번호 눈 아이콘 등)은
   아이콘 전용 폰트를 유지해야 "visibility", "arrow_drop_down" 같은
   텍스트가 아이콘 대신 그대로 노출되는 것을 막을 수 있음.
   [수정] Streamlit 번들에 실제로 로드되는 폰트명은 'Material Symbols Rounded' 임
   (Outlined가 아님 - 잘못된 폰트명이라 조용히 무시되고 있었음) */
[data-testid="stIconMaterial"],
span.material-symbols-outlined,
span.material-icons {
font-family: 'Material Symbols Rounded' !important;
}

[data-testid="stStatusWidget"] {visibility: hidden;}
.stAppDeployButton {display: none;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* 불필요한 시스템 텍스트나 내부 속성 숨기기 */
.element-container:empty { display: none; }

/* ===== [추가] 기본 페이지 - 전체 글자 크기 및 여백 조정 ===== */

/* 본문 기본 폰트: 기본보다 살짝 키워서 가독성 향상 */
html, body {
font-size: 16px !important;
}

/* 페이지 타이틀(st.title) */
h1 {
font-size: 2rem !important;
font-weight: 800 !important;
}

/* st.subheader, 카드/다이얼로그 안 소제목(####) */
h2 {
font-size: 1.4rem !important;
font-weight: 700 !important;
}
h3 {
font-size: 1.2rem !important;
font-weight: 700 !important;
}
h4 {
font-size: 1.05rem !important;
font-weight: 700 !important;
margin-top: 0.4rem !important;
margin-bottom: 0.6rem !important;
}

/* 탭 라벨 글자 크기 */
[data-testid="stTab"] p {
font-size: 15.5px !important;
font-weight: 600 !important;
}

/* 검색 결과 카드(st.container(border=True)) 박스 크기 - 패딩/여백 확대 */
[data-testid="stContainer"] {
padding: 4px 2px;
}
[data-testid="stVerticalBlockBorderWrapper"] {
border-radius: 14px !important;
}

/* 텍스트 입력창 / 셀렉트박스 - 글자 크기, 박스 높이(패딩) 확대 */
[data-testid="stTextInput"] input,
[data-testid="stTextInputRootElement"] input {
font-size: 15.5px !important;
padding: 10px 14px !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] {
font-size: 15.5px !important;
min-height: 46px !important;
}

/* 버튼 - 글자 크기, 박스 패딩 확대 */
[data-testid="stButton"] button {
font-size: 15px !important;
padding: 8px 18px !important;
border-radius: 8px !important;
}

/* st.info / st.success / st.warning / st.error 박스 - 글자 크기, 내부 여백 확대 */
[data-testid="stAlertContainer"] {
font-size: 15px !important;
padding: 14px 18px !important;
border-radius: 10px !important;
}
[data-testid="stAlertContainer"] p {
font-size: 15px !important;
line-height: 1.6 !important;
}

div[data-testid="stDialog"] div[role="dialog"] {
width: 85vw !important;
max-width: 1200px !important;
border-radius: 16px;
padding: 8px 12px !important;
}

/* 상세페이지(다이얼로그) 안 본문/캡션 글자 크기 확대 */
div[data-testid="stDialog"] p,
div[data-testid="stDialog"] li {
font-size: 15.5px !important;
line-height: 1.7 !important;
}
div[data-testid="stDialog"] h3 {
font-size: 1.35rem !important;
}
div[data-testid="stDialog"] h4 {
font-size: 1.1rem !important;
}

p, li, span, div {
line-height: 1.6;
color: #1E293B;
}

.stTextArea textarea {
font-size: 15.5px !important;
line-height: 1.75 !important;
background-color: #F8FAFC !important;
color: #0F172A !important;
border: 1px solid #CBD5E1 !important;
border-radius: 10px !important;
padding: 14px !important;
}

.stTextArea textarea:disabled {
background-color: #F1F5F9 !important;
color: #020617 !important;
-webkit-text-fill-color: #020617 !important;
opacity: 1 !important;
cursor: text !important;
}

.badge {
display: inline-block;
padding: 6px 14px;
border-radius: 7px;
font-size: 14px;
font-weight: 700;
margin-right: 8px;
margin-bottom: 8px;
box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.badge-iv { background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
.badge-dv { background-color: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }
.badge-m { background-color: #F0FDF4; color: #15803D; border: 1px solid #BBF7D0; }
.badge-mod { background-color: #FFF7ED; color: #C2410C; border: 1px solid #FED7AA; }

.var-text {
font-size: 15px;
font-weight: 600;
color: #334155;
margin-right: 18px;
display: inline-block;
margin-bottom: 8px;
}
</style>
""")
st.markdown(custom_css, unsafe_allow_html=True)

# [수정] secrets.toml 파일 자체가 없는 경우 Streamlit은 KeyError가 아니라
# StreamlitSecretNotFoundError(구버전은 FileNotFoundError)를 던지므로
# 넓게 Exception으로 잡아야 안내 메시지가 정상적으로 표시됨
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")
except Exception:
    st.error("⚠️ Streamlit Secrets 설정을 확인해주세요. (GEMINI_API_KEY / GITHUB_TOKEN / GITHUB_REPO)")
    st.stop()

# -----------------------------------------------------------------------------
# 🤖 Gemini AI 설정
# -----------------------------------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_available_gemini_model():
    # [수정] 이미 서비스가 종료된 모델(gemini-1.5-*, gemini-2.0-flash)을 제거하고
    # 최신 안정 모델(gemini-3.6-flash)을 최우선으로 추가
    preferred_models = [
        'gemini-3.6-flash',
        'gemini-3.7-flash',
        'gemini-3.5-flash',
        'gemini-3.5-flash-lite',
        'gemini-2.5-flash',
        'gemini-2.5-flash-lite',
    ]
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
                generation_config={"response_mime_type": "application/json", "temperature": 0.1}
            )
    except Exception:
        pass
    
    # [수정] list_models() 자체가 실패했을 때 쓰는 최종 폴백도
    # 서비스 종료된 모델이 아닌 현재 사용 가능한 모델로 교체
    return genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        generation_config={"response_mime_type": "application/json", "temperature": 0.1}
    )

model = get_available_gemini_model()

# GitHub 저장소 설정
repo = Github(GITHUB_TOKEN).get_repo(GITHUB_REPO)
EXCEL_FILE_PATH = "database/GBC_연구논문_DB.xlsx"

DB_COLUMNS = [
    'No.', '저자', '발행 연도', '논문/도서 제목', 
    '학술지명/출처', '핵심 이론', '연구 모형', '가설 정리', 
    '독립변수(IV)', '종속변수(DV)', '매개변수(Mediator)', 
    '조절변수(Moderator)', '주요 발견(Key Findings)', '설문문항'
]

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
    """[추가] 중복 논문 판별을 위해 제목을 정규화.
    공백/구두점/대소문자 차이 때문에 같은 논문이 다르게 인식되는 것을 방지."""
    import re
    s = str(title).strip().lower()
    s = re.sub(r'[^\w가-힣]', '', s)  # 공백, 쉼표, 마침표 등 특수문자 전부 제거
    return s

def find_duplicate_no(title, master_df):
    """제목이 이미 마스터 DB에 존재하면 해당 No.를 반환, 없으면 None."""
    norm_target = normalize_title(title)
    if norm_target == "":
        return None
    existing_norms = master_df['논문/도서 제목'].astype(str).apply(normalize_title)
    match = master_df[existing_norms == norm_target]
    if not match.empty:
        return match.iloc[0]['No.']
    return None

def disp(val, default="-"):
    """[추가] 결측값(NaN/None) 및 빈 문자열을 안전하게 처리해서 화면에 뿌릴 문자열을 만듦.
    pandas가 빈 셀을 NaN(float)으로 읽어오면 str(NaN) == 'nan'이 되어 화면에 그대로
    'nan' 텍스트가 노출되는 문제를 막기 위함. 이미 문자열화된 'nan'/'none'도 함께 방어."""
    if pd.isna(val):
        return default
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "none", "-"):
        return default
    return s

def safe(text):
    """[추가] AI가 논문에서 추출한 텍스트를 HTML에 삽입하기 전 이스케이프 처리.
    <, >, & 등이 원문에 섞여 있어도 뱃지 레이아웃이 깨지지 않도록 함."""
    return html.escape(str(text))

# 팝업 모달창
@st.dialog("📖 연구 논문 상세 분석 리포트", width="large")
def show_detail_dialog(row):
    st.markdown(f"### 📄 {disp(row.get('논문/도서 제목'))}")
    
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

# 2. 사이드바 관리자 인증
st.sidebar.title("🔐 관리자 모드")
input_pw = st.sidebar.text_input("관리자 비밀번호", type="password", placeholder="비밀번호 입력")
is_admin = bool(ADMIN_PASSWORD and input_pw == ADMIN_PASSWORD)

if is_admin:
    st.sidebar.success("관리자 권한이 활성화되었습니다.")
elif input_pw:
    st.sidebar.error("비밀번호가 일치하지 않습니다.")

# 3. 메인 화면 구성
st.title("📚 GBC 연구 논문 DB 관리 시스템")

tab_names = ["🔍 연구 논문 DB 검색", "🚀 논문 파일 업로드"]
if is_admin:
    tab_names.append("⚙️ 관리자 전용 관리 (DB/다운로드)")

tabs = st.tabs(tab_names)

# [탭 1] 연구 논문 DB 검색
with tabs[0]:
    st.subheader("🔍 연구 논문 DB 다차원 검색")
    
    master_df, _ = load_master_excel()
    
    if master_df.empty:
        st.info("현재 DB에 저장된 논문 데이터가 없습니다. [논문 파일 업로드] 탭에서 논문을 먼저 추가해 보세요.")
    else:
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                search_kw = st.text_input("🔎 통합 검색어 입력", placeholder="이론, 변수명, 저자, 논문 제목 (띄어쓰기 무시 적용)")
            with col2:
                all_theories = master_df["핵심 이론"].dropna().str.split('\n').explode().str.strip().unique()
                theory_filter = st.selectbox("💡 핵심 이론별 필터링", ["전체 보기"] + [t for t in all_theories if t and t != '-'])

        filtered_df = master_df.copy()
        
        if search_kw.strip():
            kw_clean = search_kw.replace(" ", "").lower()
            # [수정] fillna('')로 결측값을 빈 문자열 처리하여 "nan" 오탐 방지
            mask = filtered_df.fillna("").astype(str).apply(
                lambda col: col.str.replace(" ", "", regex=False).str.lower().str.contains(kw_clean, na=False, regex=False)
            ).any(axis=1)
            filtered_df = filtered_df[mask]
            
        if theory_filter != "전체 보기":
            # [수정] regex=False 추가: 이론명에 괄호 등 정규식 특수문자가 있어도
            # re.error가 나지 않고 정확히 일치하는 부분 문자열만 검색됨
            filtered_df = filtered_df[filtered_df["핵심 이론"].str.contains(theory_filter, na=False, regex=False)]

        st.markdown(f"##### 📌 조회 결과: 총 **{len(filtered_df)}** 건")
        
        if filtered_df.empty:
            st.warning("조건에 맞는 논문이 없습니다. 검색어를 변경해 보세요.")
        else:
            with st.container(height=750, border=False):
                for idx, row in filtered_df.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([6, 1])
                        
                        with c1:
                            st.markdown(f"#### 📄 {disp(row.get('논문/도서 제목'))}")
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
                            # [수정] key에 데이터프레임 인덱스(idx)를 함께 포함하여
                            # No. 값이 비어있거나(NaN) 중복되어도 key 충돌이 나지 않도록 함
                            if st.button("🔍 상세보기\n(설문문항)", key=f"btn_detail_{idx}_{row['No.']}", use_container_width=True):
                                show_detail_dialog(row)

# [탭 2] 논문 파일 업로드 및 분석
with tabs[1]:
    st.subheader("🚀 논문 파일을 업로드 하세요.")
    uploaded_files = st.file_uploader(
        "PDF 또는 Excel 파일을 선택하세요 (다중 선택 가능)", 
        type=['pdf', 'xlsx', 'xls'], 
        accept_multiple_files=True
    )

    # [추가] 제목이 같은(=이미 DB에 있는) 논문을 만났을 때 처리 방식 선택
    dup_policy = st.radio(
        "🔁 이미 DB에 있는 논문(제목 기준 중복)을 발견하면?",
        ["건너뛰기 (중복 추가 방지)", "기존 항목 덮어쓰기 (내용 업데이트)"],
        horizontal=True,
        help="같은 논문 PDF/엑셀을 다시 올렸을 때 새 행으로 중복 추가되는 것을 막기 위한 옵션입니다."
    )
    
    if st.button("파일 처리 및 마스터 DB에 누적 저장", type="primary"):
        if uploaded_files:
            master_df, sha = load_master_excel()
            current_max_no = 0
            if not master_df.empty and 'No.' in master_df.columns:
                valid_nos = pd.to_numeric(master_df['No.'], errors='coerce').dropna()
                if not valid_nos.empty:
                    current_max_no = int(valid_nos.max())

            new_entries = []
            updated_entries = {}  # {No.: row_dict} - 덮어쓰기 대상
            skipped_titles = []   # 건너뛴(또는 업데이트된) 논문 제목 기록
            # 이번 배치 안에서 같은 파일들끼리도 중복 체크가 되도록 별도 세트로 추적
            titles_seen_this_batch = set()
            
            with st.status("🔍 데이터를 처리하고 있습니다...", expanded=True) as status:
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
                            
                            added_count = 0
                            for _, row in excel_df.iterrows():
                                row_dict = row.to_dict()
                                title = row_dict.get('논문/도서 제목', '')
                                norm_title = normalize_title(title)

                                # [추가] 마스터 DB 기존 항목과 중복 검사
                                dup_no = find_duplicate_no(title, master_df)
                                # [추가] 같은 배치 안에서 방금 추가한 항목과도 중복 검사
                                is_batch_dup = norm_title != "" and norm_title in titles_seen_this_batch

                                if dup_no is not None or is_batch_dup:
                                    if dup_policy.startswith("건너뛰기"):
                                        skipped_titles.append(f"{title} (기존 No.{dup_no})" if dup_no else f"{title} (같은 배치 내 중복)")
                                        continue
                                    elif dup_no is not None:
                                        # 덮어쓰기: 기존 No.를 유지한 채 내용만 갱신
                                        row_dict['No.'] = dup_no
                                        updated_entries[dup_no] = row_dict
                                        skipped_titles.append(f"{title} (No.{dup_no} 업데이트됨)")
                                        continue

                                current_max_no += 1
                                row_dict['No.'] = current_max_no
                                new_entries.append(row_dict)
                                if norm_title:
                                    titles_seen_this_batch.add(norm_title)
                                added_count += 1
                                
                            st.write(f"✅ '{file.name}' - {added_count}건 신규 등록 "
                                     f"(중복 {len(excel_df) - added_count}건 처리)")
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
                        아래 제공된 연구 논문 텍스트를 정밀 분석하여 다음 12개 항목을 JSON 형식으로 추출해주세요.
                        특히, 연구 방법론(Methodology) 및 부록(Appendix)을 꼼꼼히 살펴 변수별 측정 문항을 'survey_items'에 상세히 기재하세요. (주의: 5점 척도, 7점 척도 등 점수 체계에 대한 설명은 절대 포함하지 말고 오직 문항만 작성하세요.)
                        
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
                            "survey_items": "변수별 측정에 사용된 실제 설문 문항 원문(영문/국문 번역 병기)만을 줄바꿈하여 작성 (척도/점수 체계 제외)"
                        }}

                        [논문 원문 텍스트]:
                        {text[:100000]}
                        """
                        
                        try:
                            response = model.generate_content(prompt)
                            res_json = json.loads(response.text)

                            pdf_title = res_json.get('title', file.name)
                            norm_title = normalize_title(pdf_title)

                            # [추가] 마스터 DB 기존 항목 및 같은 배치 내 중복 검사
                            dup_no = find_duplicate_no(pdf_title, master_df)
                            is_batch_dup = norm_title != "" and norm_title in titles_seen_this_batch

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
                                '설문문항': res_json.get('survey_items', '-')
                            }

                            if dup_no is not None or is_batch_dup:
                                if dup_policy.startswith("건너뛰기"):
                                    skipped_titles.append(f"{pdf_title} (기존 No.{dup_no})" if dup_no else f"{pdf_title} (같은 배치 내 중복)")
                                    st.write(f"⏭️ '{file.name}' — 이미 DB에 있는 논문이라 건너뜀 (제목: {pdf_title})")
                                    continue
                                elif dup_no is not None:
                                    entry['No.'] = dup_no
                                    updated_entries[dup_no] = entry
                                    skipped_titles.append(f"{pdf_title} (No.{dup_no} 업데이트됨)")
                                    st.write(f"🔄 '{file.name}' — 기존 No.{dup_no} 항목 업데이트")
                                    continue

                            current_max_no += 1
                            entry['No.'] = current_max_no
                            new_entries.append(entry)
                            if norm_title:
                                titles_seen_this_batch.add(norm_title)
                            st.write(f"✅ '{file.name}' 분석 완료! (신규 등록)")
                        except Exception as e:
                            st.error(f"'{file.name}' 분석 중 오류: {str(e)}")

                if new_entries or updated_entries:
                    updated_df = master_df.copy()

                    # [추가] 덮어쓰기 대상 반영: 기존 No.에 해당하는 행의 내용을 갱신
                    for dup_no, row_dict in updated_entries.items():
                        mask = updated_df['No.'] == dup_no
                        for k, v in row_dict.items():
                            if k == 'No.':
                                continue
                            updated_df.loc[mask, k] = v

                    # 신규 항목 추가
                    if new_entries:
                        new_df = pd.DataFrame(new_entries)
                        updated_df = pd.concat([updated_df, new_df], ignore_index=True)

                    save_master_excel(updated_df, sha)
                    status.update(label="전체 파일 처리 및 DB 저장 완료!", state="complete", expanded=False)

                    msg = f"신규 등록 {len(new_entries)}건"
                    if updated_entries:
                        msg += f", 기존 항목 업데이트 {len(updated_entries)}건"
                    if skipped_titles:
                        msg += f", 중복 처리 {len(skipped_titles)}건"
                    st.success(msg)

                    if new_entries:
                        st.dataframe(pd.DataFrame(new_entries), use_container_width=True)
                    if skipped_titles:
                        with st.expander(f"🔁 중복으로 처리된 {len(skipped_titles)}건 보기"):
                            for t in skipped_titles:
                                st.write(f"- {t}")
                else:
                    status.update(label="추출/병합된 데이터 없음", state="error")
        else:
            st.warning("업로드할 PDF 또는 엑셀 파일을 선택해주세요.")

# [탭 3] 관리자 전용 관리
if is_admin:
    with tabs[2]:
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
                    st.success(f"No. {del_target_no} 데이터가 삭제되었습니다. 페이지를 새로고침하세요.")

        st.divider()

        # [추가] 중복 논문 정리 기능
        st.markdown("### 🧹 중복 논문 정리")
        st.caption("제목(공백·구두점·대소문자 무시)이 같은 논문을 찾아, 각 그룹에서 가장 내용이 "
                   "충실한(빈 칸이 적은) 항목 하나만 남기고 나머지를 삭제합니다.")

        def build_dup_plan(df):
            """중복 그룹을 찾고, 그룹별로 남길 행/지울 행을 결정한 계획(plan)을 만든다."""
            work = df.copy()
            work['_norm_title'] = work['논문/도서 제목'].astype(str).apply(normalize_title)
            # 필드가 얼마나 채워져 있는지(=충실도) 점수 계산: '-' 나 결측이 아닌 필드 개수
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
                # 완성도가 가장 높은 행을 남기고, 동률이면 No.가 가장 작은(먼저 등록된) 행을 남김
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
                st.warning(f"총 {len(previews)}개 그룹, {len(drop_nos)}건이 삭제 대상입니다. "
                           f"삭제 전 아래 내용을 꼭 확인해주세요.")
                for p in previews:
                    with st.container(border=True):
                        st.markdown(f"**📄 {p['title']}**")
                        st.write(f"✅ 유지: No.{p['keep_no']} (완성도 {p['keep_completeness']}개 필드)")
                        for dno, dcomp in zip(p['drop_nos'], p['drop_completeness']):
                            st.write(f"🗑️ 삭제 예정: No.{dno} (완성도 {dcomp}개 필드)")

                if st.button("⚠️ 위 목록대로 중복 삭제 실행 (되돌릴 수 없음)", type="primary"):
                    fresh_df, fresh_sha = load_master_excel()  # 최신 상태 다시 로드 (동시 수정 대비)
                    cleaned = fresh_df[~fresh_df['No.'].isin(drop_nos)].reset_index(drop=True)
                    cleaned['No.'] = range(1, len(cleaned) + 1)
                    save_master_excel(cleaned, fresh_sha)
                    st.success(f"중복 {len(drop_nos)}건을 삭제하고 No.를 다시 정렬했습니다. 페이지를 새로고침하세요.")
                    del st.session_state['dup_preview']
                    del st.session_state['dup_drop_nos']
