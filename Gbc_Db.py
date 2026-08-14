import streamlit as st
import requests
import pandas as pd
import json
import concurrent.futures
import io
import datetime
from openai import OpenAI

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="논문 설문문항 추출기",
    page_icon="📄",
    layout="wide"
)

# ---------------------------------------------------------
# [API 키 설정] 
# Streamlit Cloud의 Advanced settings -> Secrets에 아래 두 키를 등록해야 합니다.
# ---------------------------------------------------------
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"] # sk- 로 시작하는 키
    S2_API_KEY = st.secrets["S2_API_KEY"]         # s2k- 로 시작하는 키
except KeyError:
    st.error("⚠️ Streamlit Secrets에 API 키가 설정되지 않았습니다. 설정을 확인해주세요.")
    st.stop()

# 커스텀 CSS
st.markdown("""
    <style>
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    .stButton>button { width: 100%; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📄 논문 설문문항 자동 추출 시스템")
st.markdown("입력한 키워드와 관련된 논문을 검색하고, AI가 연구 변수와 측정 문항을 1:1로 매칭하여 표(Excel)로 추출합니다.")

col1, col2 = st.columns([1, 1])
with col1:
    year_filter = st.selectbox(
        "📅 출판 연도", 
        ["전체", "최근 5년", "최근 10년", "최근 15년", "최근 20년"]
    )
with col2:
    limit = st.slider("📑 검색할 논문 수", min_value=1, max_value=5, value=3)

query = st.text_input("🔍 검색 키워드 (예: Generative AI advertising)")

# 3. 개별 논문 AI 추출 함수
def extract_single_paper(paper, client):
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    citation_count = paper.get("citationCount", 0)

    if not abstract:
        return {"status": "error", "title": title, "msg": "초록 정보가 없습니다."}

    prompt = f"""
    당신은 경영학 및 소비자 행동 연구 방법론 전문가입니다.
    아래 논문 정보를 바탕으로, 연구 변수(Constructs), 설문 문항(Survey Items), 척도(Scale)를 JSON 형식으로 추출해주세요.

    [논문 제목]: {title}
    [초록]: {abstract}

    응답 형식(JSON만 출력):
    {{
        "items": [
            {{
                "variable": "변수명",
                "item_en": "영문 문항 내용",
                "item_ko": "국문 문항 내용",
                "scale": "척도 유형"
            }}
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You output strictly JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {"status": "error", "title": title, "msg": "AI 응답(JSON) 형식이 올바르지 않습니다."}

        items = result.get("items", [])
        for item in items:
            item["paper_title"] = title
            item["citation_count"] = citation_count
            
        return {"status": "success", "items": items}

    except Exception as e:
        return {"status": "error", "title": title, "msg": f"오류: {str(e)}"}


# 4. 검색 및 추출 실행 로직
if st.button("검색 및 문항 추출 실행", type="primary"):
    if not query.strip():
        st.warning("검색 키워드나 논문 제목을 입력해주세요.")
    else:
        with st.status("🔍 데이터를 추출하고 있습니다...", expanded=True) as status:
            try:
                st.write("1. Semantic Scholar 학술 DB에서 논문 검색 중...")
                
                # API 호출 파라미터 세팅
                url = "https://api.semanticscholar.org/graph/v1/paper/search"
                params = {
                    "query": query,
                    "limit": limit,
                    "fields": "title,abstract,citationCount"
                }
                
                if year_filter != "전체":
                    current_year = datetime.datetime.now().year
                    if year_filter == "최근 5년":
                        params["year"] = f"{current_year - 5}-"
                    elif year_filter == "최근 10년":
                        params["year"] = f"{current_year - 10}-"
                    elif year_filter == "최근 15년":
                        params["year"] = f"{current_year - 15}-"
                    elif year_filter == "최근 20년":
                        params["year"] = f"{current_year - 20}-"

                # 💡 가이드에 명시된 부분: x-api-key 헤더에 S2 키 탑재
                headers = {"x-api-key": S2_API_KEY}
                res = requests.get(url, params=params, headers=headers)
                
                # 에러 디버깅 로직 추가
                if res.status_code == 429:
                    status.update(label="요청 한도 초과 (잠시 후 다시 시도해주세요)", state="error")
                    st.stop()
                elif res.status_code != 200:
                    status.update(label=f"서버 에러 (상태코드: {res.status_code})", state="error")
                    st.error(f"상세 로그: {res.text}")
                    st.stop()
                elif res.json().get("total", 0) == 0:
                    status.update(label="조건에 맞는 논문을 찾을 수 없습니다.", state="error")
                    st.info("💡 팁: 검색어를 '영문'으로 짧게(예: Generative AI advertising) 입력하시고, 출판 연도를 '전체'로 변경해 보세요.")
                    st.stop()

                papers = res.json().get("data", [])
                st.write(f"✅ {len(papers)}개의 논문 발견! AI 분석을 시작합니다 (병렬 처리)...")
                
                # 💡 OpenAI 분석용 클라이언트에는 OpenAI 전용 키 탑재
                client = OpenAI(api_key=OPENAI_API_KEY)
                all_extracted_items = []
                error_logs = []

                # ThreadPoolExecutor 병렬 처리
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(extract_single_paper, paper, client) for paper in papers]
                    
                    for future in concurrent.futures.as_completed(futures):
                        res_data = future.result()
                        if res_data["status"] == "success":
                            all_extracted_items.extend(res_data["items"])
                        else:
                            error_logs.append(f"- **{res_data['title'][:30]}...**: {res_data['msg']}")

                if not all_extracted_items and error_logs:
                    status.update(label="문항 추출 실패", state="error")
                    st.error("\n".join(error_logs))
                    st.stop()

                status.update(label="추출 완료!", state="complete", expanded=False)

            except Exception as e:
                status.update(label="시스템 오류", state="error")
                st.error(f"오류가 발생했습니다: {str(e)}")
                st.stop()

        # 5. 결과 화면 출력 및 엑셀 다운로드
        if error_logs:
            st.warning("⚠️ 일부 논문에서 데이터를 추출하지 못했습니다.\n" + "\n".join(error_logs))

        st.subheader(f"📊 추출된 설문 문항 (총 {len(all_extracted_items)}개)")
        
        df = pd.DataFrame(all_extracted_items)
        df_display = df.rename(columns={
            "paper_title": "논문 제목",
            "citation_count": "피인용 수",
            "variable": "연구 변수",
            "item_en": "설문 문항(영문)",
            "item_ko": "설문 문항(국문)",
            "scale": "척도"
        })
        df_display = df_display[["논문 제목", "피인용 수", "연구 변수", "설문 문항(영문)", "설문 문항(국문)", "척도"]]
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_display.to_excel(writer, index=False, sheet_name='Survey Items')
        
        st.download_button(
            label="📥 엑셀(Excel) 파일로 다운로드",
            data=buffer.getvalue(),
            file_name=f"survey_items.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )