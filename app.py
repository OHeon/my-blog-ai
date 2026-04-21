import streamlit as st
import google.generativeai as genai
import re

# --- [1. 설정 영역] ---
# 발급받으신 Gemini API 키를 여기에 입력하세요
GEMINI_API_KEY = "AIzaSyA7P6zK88idFjqGzKU-eX8UM_SvwJB6QMI"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# 1-1. 수정된 시스템 프롬프트 (강조 금지 및 해시태그 형식 지정)
SYSTEM_PROMPT = """
너는 네이버 블로그 포스팅 전문가다. 아래 지침을 엄격히 준수해라.

■ 출력 형식 (반드시 이 태그를 포함할 것)
[TITLE] 메인 키워드가 포함된 제목
[CONTENT] 본문 내용
[HASHTAGS] #해시태그1 #해시태그2 #해시태그3 (띄어쓰기로 구분)

■ 본문 작성 규칙
1. 글자수: 공백 제외 1000자 이상 (필수)
2. 강조 금지: 텍스트에 **(별표)를 사용한 굵게 강조나 어떠한 마크다운 문법도 사용하지 마라. 모든 글자는 일반 텍스트로 작성해라.
3. 말투: 짧은 문장 위주, 빈번한 줄바꿈, 마침표 최소화, 자연스러운 실제 후기 느낌
4. 인사말: 블로거 닉네임이나 "안녕하세요" 같은 뻔한 첫인사 절대 금지
5. 사진 배치 (총 5장 고정): [사진1] ~ [사진5]를 흐름에 맞게 배치해라, 사진은 문단과 문단 사이에 넣을것
6. 흐름: '방문 계기', '위치' 같은 중간 소제목을 절대 쓰지 말고 자연스럽게 문단으로만 이어갈 것

■ 해시태그 규칙
- 해시태그는 #[태그] #[태그] 형식으로 각 태그 사이에 반드시 띄어쓰기를 넣어라.
- 맨 아래에 따로 모아서 작성해라.

■ 절대 금지 사항
- 효과, 개선, 치료, 변화, 추천, 강추, 갓성비, 할인, 이벤트, 가격, 혜택 표현 절대 금지
- 아래 명시된 '불가 키워드'는 제목, 본문, 해시태그 어디에도 등장해서는 안 됨
- 가이드라인 또는 키워드에 불가 키워드가 포함될 경우 불가키워드는 무조건 제거 후 글과 제목 작성
"""

BANNED_KEYWORDS = [
    "자연눈썹", "반영구", "문신", "SMP", "두피페인팅", "커버", "아이라인", "헤어라인", "입술", "미인점", "콤보", "헤어스트록", "헤어도트", "두피컬러링", "그라데이션", "잔흔", "수지", "엠보", "아치", "세미아치", "셰도우", "자연결", "타투샵",
    "플라즈마", "애교살", "MTS", "미세침", "시술", "콜드플라", "미용기기", "재생", "흉터", "색소", "색소침착", "외음부", "유륜",
    "울쎄라", "리프팅", "보톡스", "필러", "레이저", "성형", "치료", "흡입", "지방흡입", "약물", "물리치료", "피부과", "성형외과", "수술", "장애", "치매",
    "안마", "지압", "부종", "붓기", "감량", "아토피", "모낭", "소양증", "항염진통", "해독", "이뇨", "항암", "항진균", "항바이러스", "여드름",
    "경락", "개선", "윤곽", "축소", "교정", "모발이식", "탈모", "탈모관리", "증모", "생장", "두피보강", "두피디자인", "두피패턴", "모발시뮬레이션",
    "재활", "다이어트", "매입", "매매", "금은방", "금거래소", "금시세", "금값", "고물상", "전당포", "개통", "가입", "요금",
    "펍", "라운지", "라이브카페", "포차", "클럽", "바", "홀덤", "노래방", "운전연수", "주차대행", "리스", "보험", "대차", "대물", "렌탈", "렌트", "임대", "모텔",
    "분양", "입양", "임차", "원룸", "오피스텔", "부동산", "금액", "가격", "거래", "결제", "최저가", "최고가", "계약", "경매", "페이", "판매", "무료", "공짜", "특가", "세일", "전액", "전문1위", "압도적", "파격", "할인", "이벤트", "행사", "비용", "저렴", "강추", "강력추천", "추천"
]

# --- [2. 앱 로직 영역] ---
st.set_page_config(page_title="네이버 블로그 비서", layout="wide")

if 'history' not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.title("🛡️ 블로그 비서 v2.1")
    if st.button("+ 새 글 작성"):
        st.rerun()
    st.write("---")
    for h in st.session_state.history[-10:]:
        st.write(f"📌 {h['title']}")

st.title("네이버 블로그 자동 완성기")
user_guide = st.text_area("작성할 주제와 키워드를 입력하세요.", height=100)

if st.button("🚀 글 생성 및 검수"):
    if not user_guide:
        st.warning("내용을 입력해주세요.")
    else:
        try:
            with st.spinner("규칙을 검토하며 글을 생성 중입니다..."):
                full_prompt = f"{SYSTEM_PROMPT}\n\n[불가키워드]\n{', '.join(BANNED_KEYWORDS)}\n\n[주제]\n{user_guide}"
                response = model.generate_content(full_prompt)
                res_text = response.text

                # 제목, 본문, 해시태그 분리 로직
                title, content, hashtags = "추출 실패", "추출 실패", "추출 실패"
                
                try:
                    title = res_text.split("[TITLE]")[1].split("[CONTENT]")[0].strip()
                    content = res_text.split("[CONTENT]")[1].split("[HASHTAGS]")[0].strip()
                    hashtags = res_text.split("[HASHTAGS]")[1].strip()
                except:
                    content = res_text # 분리 실패 시 전체 출력

                # 검수
                char_count = len(re.sub(r'\s+', '', content))
                found_banned = [w for w in BANNED_KEYWORDS if w in res_text]

                st.divider()

                # 3단 구성 출력
                st.subheader("1️⃣ 블로그 제목")
                st.code(title, language=None)

                st.subheader("2️⃣ 블로그 본문")
                col1, col2 = st.columns(2)
                col1.metric("글자수 (공백제외)", f"{char_count}자")
                col2.metric("금칙어 발견", f"{len(found_banned)}개")
                
                if found_banned:
                    st.error(f"⚠️ 금칙어 주의: {', '.join(found_banned[:10])}...")
                
                st.text_area("본문 내용", content, height=400)

                st.subheader("3️⃣ 해시태그")
                st.code(hashtags, language=None)

                # 히스토리 저장
                st.session_state.history.append({"title": title[:20]})
                st.success("모든 생성이 완료되었습니다!")

        except Exception as e:
            st.error(f"에러 발생: {e}")