import streamlit as st
import pandas as pd
import json
import io
import base64
import google.generativeai as genai
from pypdf import PdfReader
from github import Github
from github.GithubException import UnknownObjectException

# 1. 페이지 설정 및 타이틀
st.set_page_config(page_title="GBC 연구 논문 DB 관리 시스템", page_icon="📚", layout="wide")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
except KeyError:
    st.error("⚠️ Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

# Gemini AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name='gemini-3.7-flash',
    generation_config={"response_mime_type": "application/json", "temperature": 0.1}
)

# GitHub 저장소 설정
repo = Github(GITHUB_TOKEN).get_repo(GITHUB_REPO)
EXCEL_FILE_PATH = "database/GBC_연구논문_DB.xlsx"

# '연구 방법론', '설문문항'이 제외된 최종 정예 13개 컬럼 정의
DB_COLUMNS = [
    'No.', '저자', '발행 연도', '논문/도서 제목', 
    '학술지명/출처', '핵심 이론', '연구 모형', '가설 정리', 
    '독립변수(IV)', '종속변수(DV)', '매개변수(Mediator)', 
    '조절변수(Moderator)', '주요 발견(Key Findings)'
]

# GitHub에서 마스터 엑셀 파일 불러오기
def load_master_excel():
    try:
        file_content = repo.get_contents(EXCEL_FILE_PATH)
        decoded = base64.b64decode(file_content.content)
        df = pd.read_excel(io.BytesIO(decoded))
        
        # 불필요 컬럼들 정리
        drop_targets = [
            '상태', '권/호', '실무적 시사점', '국내/해외', 
            '연구 주제/키워드', '메모', '연구 방법론', '설문문항'
        ]
        df = df.drop(columns=[col for col in drop_targets if col in df.columns], errors='ignore')
        
        # 누락된 컬럼 보정
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

# 2. UI 화면 구성
st.title("📚 GBC 연구 논문 DB 관리 시스템")

tab1, tab2 = st.tabs(["🚀 파일 분석 및 DB 누적", "🔍 연구 논문 DB 검색 및 관리"])

# [탭 1] 파일 업로드 및 DB 누적
with tab1:
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
                    
                    # 1. 엑셀 파일인 경우 -> 직접 읽어서 병합
                    if file_ext in ['xlsx', 'xls']:
                        st.write(f"📊 [{idx+1}/{len(uploaded_files)}] '{file.name}' 엑셀 파일 데이터 병합 중...")
                        try:
                            excel_df = pd.read_excel(file)
                            
                            # 불필요 컬럼 제거
                            drop_targets = [
                                '상태', '권/호', '실무적 시사점', '국내/해외', 
                                '연구 주제/키워드', '메모', '연구 방법론', '설문문항'
                            ]
                            excel_df = excel_df.drop(columns=[col for col in drop_targets if col in excel_df.columns], errors='ignore')
                            
                            # 필요한 컬럼 채우기
                            for col in DB_COLUMNS:
                                if col not in excel_df.columns:
                                    excel_df[col] = "-"
                                    
                            excel_df = excel_df[DB_COLUMNS]
                            
                            # No. 재정렬
                            for _, row in excel_df.iterrows():
                                current_max_no += 1
                                row_dict = row.to_dict()
                                row_dict['No.'] = current_max_no
                                new_entries.append(row_dict)
                                
                            st.write(f"✅ '{file.name}' - {len(excel_df)}건의 데이터 등록 완료!")
                        except Exception as e:
                            st.error(f"'{file.name}' 엑셀 읽기 오류: {str(e)}")

                    # 2. PDF 파일인 경우 -> Gemini AI 분석 (설문문항 제외)
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

                        # 설문문항 및 연구방법론 제외 프롬프트
                        prompt = f"""
                        당신은 경영학 및 소비자 행동 연구 방법론 최고 전문가입니다.
                        아래 제공된 연구 논문 텍스트를 정밀 분석하여 다음 11개 항목을 JSON 형식으로 추출해주세요.
                        
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
                            "findings": "주요 발견(Key Findings)"
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
                                '주요 발견(Key Findings)': res_json.get('findings', '-')
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

# [탭 2] 완전DB 검색 및 관리
with tab2:
    st.subheader("🔍 GBC 연구 논문 DB 다차원 검색")
    
    master_df, _ = load_master_excel()
    
    if master_df.empty:
        st.info("현재 DB에 저장된 논문 데이터가 없습니다. [탭 1]에서 파일(PDF/엑셀)을 먼저 추가해 보세요.")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            search_kw = st.text_input("🔎 통합 키워드 검색", placeholder="이론, 변수(IV/DV/매개/조절), 저자, 논문 제목 등")
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
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            filtered_df.to_excel(writer, index=False, sheet_name='Sheet1')
            
        st.download_button(
            label="📥 검색 결과 엑셀(Excel) 다운로드",
            data=buffer.getvalue(),
            file_name="GBC_연구논문_검색결과.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
