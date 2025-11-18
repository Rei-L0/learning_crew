// 1. 필요한 DOM 요소들을 선택합니다.
const uploadForm = document.getElementById("uploadForm");
// ✨ 2개의 파일 입력을 선택
const planFileInput = document.getElementById("planFile");
const reportFileInput = document.getElementById("reportFile");
const statusDiv = document.getElementById("status");
const resultContainer = document.getElementById("resultContainer"); // ✨ 결과 컨테이너 추가

const UPLOAD_URL = "http://127.0.0.1:8000/upload-and-analyze";

// ✨ 9-4 ~ 9-6 로직을 별도 함수로 분리 (재사용을 위해)
// (기존 9-4 ~ 9-6 코드를 이 함수 안으로 이동시킵니다)
function renderResultHTML(data, filename) {
  // 9-3. 항목별 한글 매핑
  const rationaleMap = {
    plan_specificity: "계획 구체성",
    plan_feasibility: "계획 실현성",
    plan_measurability: "계획 측정성",
    result_specificity_goal: "결과 구체성 (목표)",
    team_participation_diversity: "팀 참여도/다양성",
    evidence_strength: "증빙 강도",
  };

  // 9-4. '항목별 세부 평가' 목록 HTML 생성
  let rationaleHtml = "<ul>";
  for (const key in data.rationale) {
    const label = rationaleMap[key] || key;
    const score = data.scores_weighted[key];
    const rationaleText = data.rationale[key];

    rationaleHtml += `
        <li>
            <strong>${label} ( ${score}점 )</strong>
            <p>${rationaleText}</p>
        </li>`;
  }
  rationaleHtml += "</ul>";

  // 9-5. '참고 사항' 목록 HTML 생성 (기존과 동일)
  let uncertaintiesHtml = "<ul>";
  if (data.uncertainties && data.uncertainties.length > 0) {
    data.uncertainties.forEach((item) => {
      uncertaintiesHtml += `<li>${item}</li>`;
    });
  } else {
    uncertaintiesHtml += "<li>없음</li>";
  }
  uncertaintiesHtml += "</ul>";

  // 9-6. 최종 결과를 HTML 문자열로 반환
  return `
        <div class="result-item-container"> 
            <h3>📊 분석 결과 (${filename})</h3>
            
            <div class="result-box">
                <div class="result-item">
                    <strong>총점</strong>
                    <span>${data.total} 점</span>
                </div>
                <div class="result-item">
                    <strong>감지된 사진 수</strong>
                    <span>${data.photo_count_detected} 장</span>
                </div>
            </div>

            <h4>항목별 세부 평가</h4>
            ${rationaleHtml}

            <h4>참고 사항</h4>
            ${uncertaintiesHtml}

            <h4>최종 코멘트</h4>
            <p>${data.final_comment}</p>
        </div>
    `;
}

// 2. 폼 'submit' 이벤트 리스너
uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  // ✨ files (복수형) 컬렉션을 가져옴
  const planFiles = planFileInput.files;
  const reportFiles = reportFileInput.files;

  // ✨ 파일이 하나라도 선택되었는지 확인
  if (planFiles.length === 0 || reportFiles.length === 0) {
    statusDiv.textContent =
      "적어도 하나 이상의 계획서와 결과보고서 파일을 선택해주세요.";
    return;
  }

  const formData = new FormData();

  // ✨ FormData에 모든 파일을 'plan_files' 키로 추가 (복수형 주의)
  for (const file of planFiles) {
    formData.append("plan_files", file);
  }
  // ✨ FormData에 모든 파일을 'report_files' 키로 추가 (복수형 주의)
  for (const file of reportFiles) {
    formData.append("report_files", file);
  }

  // 8. 서버로 데이터 전송
  statusDiv.textContent = `업로드 중... (총 ${
    planFiles.length + reportFiles.length
  }개 파일)`;
  resultContainer.innerHTML = ""; // 이전 결과 초기화

  try {
    const response = await fetch(UPLOAD_URL, {
      method: "POST",
      body: formData,
    });

    // 9. 서버로부터 응답 받기 (✨ 수정)
    if (response.ok) {
      // 서버는 { summary: {...}, results: [...] } 구조를 반환
      const responseData = await response.json();
      console.log("서버 응답:", responseData);

      // 9-1. 요약 정보 표시
      const summary = responseData.summary;
      statusDiv.textContent = `✅ 분석 완료: ${summary.matched_count}건 매칭 성공, ${summary.unmatched_plans.length}건 계획서 매칭실패, ${summary.unmatched_reports.length}건 보고서 매칭실패`;

      // 9-2. 매칭 실패한 파일 목록 표시 (있을 경우)
      if (
        summary.unmatched_plans.length > 0 ||
        summary.unmatched_reports.length > 0
      ) {
        let unmatchedHtml = "<h4>--- 매칭 실패 ---</h4><ul>";
        summary.unmatched_plans.forEach((name) => {
          unmatchedHtml += `<li>[계획서] ${name} (짝을 찾지 못함)</li>`;
        });
        summary.unmatched_reports.forEach((name) => {
          unmatchedHtml += `<li>[보고서] ${name} (짝을 찾지 못함)</li>`;
        });
        unmatchedHtml += "</ul><hr>";
        resultContainer.innerHTML += unmatchedHtml;
      }

      // 9-3. 성공/실패한 모든 결과 항목을 순회하며 표시
      responseData.results.forEach((result) => {
        if (result.status === "success") {
          // 9-3-1. 성공한 경우 (기존 로직과 유사)
          try {
            // ========================================================
            // ✨ 여기가 핵심 수정 부분입니다. (JSON 파싱 강화)
            // ========================================================

            const rawString = result.analysis_result;

            // 1. 문자열에서 첫 번째 '{'의 위치를 찾습니다.
            const startIndex = rawString.indexOf("{");

            // 2. 문자열에서 마지막 '}'의 위치를 찾습니다.
            const endIndex = rawString.lastIndexOf("}");

            if (startIndex === -1 || endIndex === -1 || endIndex < startIndex) {
              // '{' 또는 '}'를 찾지 못했거나 순서가 잘못된 경우
              throw new Error("응답에서 유효한 JSON 객체를 찾을 수 없습니다.");
            }

            // 3. '{'부터 '}'까지의 문자열만 정확히 추출합니다.
            const cleanedString = rawString.substring(startIndex, endIndex + 1);

            // 4. 정리된 문자열을 JSON 객체로 변환합니다.
            const data = JSON.parse(cleanedString);

            // ========================================================
            // ✨ 수정 끝
            // ========================================================

            // 9-3-2. HTML 생성 함수 호출 및 삽입
            resultContainer.innerHTML += renderResultHTML(
              data,
              result.filename
            );
          } catch (parseError) {
            console.error(
              "JSON 파싱 오류:",
              parseError,
              result.analysis_result // 실패한 원본 문자열을 로그에 남깁니다.
            );
            resultContainer.innerHTML += `
              <div class="result-item-container error">
                <h3>❌ ${result.filename} 분석 실패 (JSON 파싱 오류)</h3>
                <p>${parseError.message}</p>
              </div>`;
          }
        } else {
          // 9-3-3. API 처리 실패한 경우
          resultContainer.innerHTML += `
            <div class="result-item-container error">
              <h3>❌ ${result.filename} 분석 실패</h3>
              <p>${result.error}</p>
            </div>`;
        }
      });
    } else {
      statusDiv.textContent = `❌ 업로드 실패: ${response.statusText}`;
    }
  } catch (error) {
    console.error("업로드 중 오류 발생:", error);
    statusDiv.textContent = `❌ 오류 발생: ${error.message}`;
  }
});
