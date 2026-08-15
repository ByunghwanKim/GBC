import streamlit as st
import pandas as pd
import json
import io
import base64
import google.generativeai as genai
from pypdf import PdfReader
from github import Github
from github.GithubException import UnknownObjectException

# 1. 페이지 설정
st.set_page_config(page_title="GBC 연구 논문 DB 관리 시스템", page_icon="📚", layout="wide")

# CSS: 팝업창 최대화 및 기본 UI 가리기
custom_css = """
    <style>
    [data-testid="stStatusWidget"] {visibility: hidden;}
    .stAppDeployButton {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    div[data-testid="stDialog"] div[role="dialog"] {
        width: 85vw !important;
        max-width: 1200px !important;
        border-radius: 12px;
    }
    </style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")
except KeyError:
    st.error("⚠️ Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

# -----------------------------------------------------------------------------
# 🤖 Gemini AI 설정
# -----------------------------------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_available_gemini_model():
    preferred_models = [
        'gemini-3.7-flash',
        'gemini-3.5-flash',
        'gemini-3.5-flash-lite',
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash'
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
    
    return genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        generation_config={"response_mime_type": "application/json", "temperature": 0.1}
    )

model = get_available_gemini_model()

# GitHub 저장소 설정
repo = Github(GITHUB_TOKEN).get_repo(GITHUB_REPO)
EXCEL_FILE_PATH = "database/GBC_연구논문_DB.xlsx"

# 14개 표준 컬럼 정의
DB_COLUMNS = [
    'No.', '저자', '발행 연도', '논문/도서 제목', 
    '학술지명/출처', '핵심 이론', '연구 모형', '가설 정리', 
    '독립변수(IV)', '종속변수(DV)', '매개변수(Mediator)', 
    '조절변수(Moderator)', '주요 발견(Key Findings)', '설문문항'
]

# GitHub에서 마스터 엑셀 파일 불러오기
def load_master_excel():
    try:
        file_content = repo.get_contents(EXCEL_FILE_PATH)
        decoded = base64.b64decode(file_content.content)
        df = pd.read_excel(io.BytesIO(decoded))
        
        if '메모' in df.columns and '설문문항' not in df.columns:
            df = df.rename(columns={'메모': '설문문항'})
            
        drop_targets = [
            '상태', '권/호', '실무적 시사점', '국내/해외', 
            '연구 주제/키워드', '메모', '연구 방법론'
        ]
        df = df.drop(columns=[col for col in drop_targets if col in df.columns], errors='ignore')
        
        for col in DB_COLUMNS:
            if col not in df.columns:
                df[col] = "-"
        return df[DB_COLUMNS], file_content.sha
    except UnknownObjectException:
        empty_df = pd.DataFrame(columns=DB_COLUMNS)
        return empty_df, None

# GitHub에 마스터 엑셀 저장
def save_master_excel(df, sha):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    content = buffer.getvalue()
    
    if sha:
        repo.update_file(EXCEL_FILE_PATH, "Update GBC 연구논문 DB", content, sha)
    else:
        repo.create_file(EXCEL_FILE_PATH, "Create GBC 연구논문 DB", content)

# 팝업 모달창 (클릭 시 호출됨)
@st.dialog("📖 연구 논문 상세 분석 리포트", width="large")
def show_detail_dialog(row):
    st.markdown(f"## 📄 {row.get('논문/도서 제목', '-')}")
    
    col_m1, col_m2, col_m3 = st.columns([1, 1, 2])
    col_m1.info(f"👤 **저자:** {row.get('저자', '-')}")
    col_m2.info(f"📅 **발행 연도:** {row.get('발행 연도', '-')}")
    col_m3.info(f"🏛️ **학술지명/출처:** {row.get('학술지명/출처', '-')}")
    
    st.divider()
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("#### 💡 핵심 이론")
        st.markdown(f"> {row.get('핵심 이론', '-')}")
        
        st.markdown("#### 📊 연구 모형")
        st.code(row.get('연구 모형', '-'), language=None)
        
        st.markdown("#### 🔗 변수 구성")
        st.markdown(f"- **독립변수(IV):** `{row.get('독립변수(IV)', '-')}`")
        st.markdown(f"- **종속변수(DV):** `{row.get('종속변수(DV)', '-')}`")
        st.markdown(f"- **매개변수(Mediator):** `{row.get('매개변수(Mediator)', '-')}`")
        st.markdown(f"- **조절변수(Moderator):** `{row.get('조절변수(Moderator)', '-')}`")
        
    with col_right:
        st.markdown("#### 📌 가설 체계")
        st.text_area("가설 정리", value=str(row.get('가설 정리', '-')), height=130, disabled=True)
        
        st.markdown("#### 🎯 주요 발견 (Key Findings)")
        st.success(row.get('주요 발견(Key Findings)', '-'))

    st.divider()
    
    st.markdown("### 📝 측정 척도 및 설문 문항 원문 (영문/국문)")
    survey_content = str(row.get('설문문항', '-'))
    if survey_content and survey_content != "-":
        st.text_area("설문문항 상세 (클릭하여 전체 복사 가능)", value=survey_content, height=350)
    else:
        st.warning("등록된 세부 설문문항 데이터가 없습니다.")

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
    st.subheader("🔍 연구 논문 DB 검색 및 상세 열람")
    
    master_df, _ = load_master_excel()
    
    if master_df.empty:
        st.info("현재 DB에 저장된 논문 데이터가 없습니다. [논문 파일 업로드] 탭에서 논문을 먼저 추가해 보세요.")
    else:
        # 검색 필터부
        col1, col2 = st.columns([2, 1])
        with col1:
            search_kw = st.text_input("🔎 통합 키워드 검색", placeholder="이론, 변수(IV/DV), 저자, 설문문항, 논문 제목 등")
        with col2:
            all_theories = master_df["핵심 이론"].dropna().str.split('\n').explode().str.strip().unique()
            theory_filter = st.selectbox("💡 핵심 이론별 필터", ["전체 보기"] + [t for t in all_theories if t and t != '-'])

        filtered_df = master_df.copy()
        
        if search_kw.strip():
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_kw, case=False, na=False)).any(axis=1)
            filtered_df = filtered_df[mask]
            
        if theory_filter != "전체 보기":
            filtered_df = filtered_df[filtered_df["핵심 이론"].str.contains(theory_filter, na=False)]

        st.write(f"조회 결과: 총 **{len(filtered_df)}건**")
        st.info("💡 **팁:** 아래 표에서 원하시는 논문의 **아무 곳(제목, 저자 등)**이나 한 번만 클릭하시면 즉시 대형 창이 열립니다.")
        
        # ---------------------------------------------------------
        # [핵심 변경] 표(Dataframe) 직접 클릭 방식 복구
        # ---------------------------------------------------------
        selection_event = st.dataframe(
            filtered_df, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",           # 행 클릭 시 팝업을 위한 화면 갱신
            selection_mode="single-row"  # 단일 행 클릭 활성화
        )
        
        # 행이 선택된 경우 팝업 다이얼로그 호출
        if selection_event.selection.rows:
            selected_index = selection_event.selection.rows[0]
            selected_row_data = filtered_df.iloc[selected_index]
            show_detail_dialog(selected_row_data)

# [탭 2] 논문 파일 업로드 및 분석
with tabs[1]:
    st.subheader("논문 파일을 업로드 하세요.")
    uploaded_files = st.file_uploader(
        "PDF 또는 Excel 파일을 선택하세요 (다중 선택 가능)", 
        type=['pdf', 'xlsx', 'xls'], 
        accept_multiple_files=True
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
            
            with st.status("🔍 데이터를 처리하고 있습니다...", expanded=True) as status:
                for idx, file in enumerate(uploaded_files):
                    file_ext = file.name.split('.')[-1].lower()
                    
                    if file_ext in ['xlsx', 'xls']:
                        st.write(f"📊 [{idx+1}/{len(uploaded_files)}] '{file.name}' 엑셀 파일 데이터 병합 중...")
                        try:
                            excel_df = pd.read_excel(file)
                            if '메모' in excel_df.columns and '설문문항' not in excel_df.columns:
                                excel_df = excel_df.rename(columns={'메모': '설문문항'})
                                
                            drop_targets = [
                                '상태', '권/호', '실무적 시사점', '국내/해외', 
                                '연구 주제/키워드', '메모', '연구 방법론'
                            ]
                            excel_df = excel_df.drop(columns=[col for col in drop_targets if col in excel_df.columns], errors='ignore')
                            
                            for col in DB_COLUMNS:
                                if col not in excel_df.columns:
                                    excel_df[col] = "-"
                                    
                            excel_df = excel_df[DB_COLUMNS]
                            
                            for _, row in excel_df.iterrows():
                                current_max_no += 1
                                row_dict = row.to_dict()
                                row_dict['No.'] = current_max_no
                                new_entries.append(row_dict)
                                
                            st.write(f"✅ '{file.name}' - {len(excel_df)}건의 데이터 등록 완료!")
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
                            
                            current_max_no += 1
                            entry = {
                                'No.': current_max_no,
                                '저자': res_json.get('authors', '-'),
                                '발행 연도': res_json.get('year', '-'),
                                '논문/도서 제목': res_json.get('title', file.name),
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
                            new_entries.append(entry)
                            st.write(f"✅ '{file.name}' 분석 완료!")
                        except Exception as e:
                            st.error(f"'{file.name}' 분석 중 오류: {str(e)}")

                if new_entries:
                    new_df = pd.DataFrame(new_entries)
                    updated_df = pd.concat([master_df, new_df], ignore_index=True)
                    save_master_excel(updated_df, sha)
                    status.update(label="전체 파일 처리 및 DB 누적 저장 완료!", state="complete", expanded=False)
                    st.success(f"총 {len(new_entries)}건의 연구 데이터가 'GBC_연구논문_DB'에 완벽하게 누적되었습니다.")
                    st.dataframe(new_df, use_container_width=True)
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
