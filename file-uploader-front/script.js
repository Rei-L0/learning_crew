// 1. 필요한 DOM 요소들을 선택합니다.
const uploadForm = document.getElementById("uploadForm");
const planFileInput = document.getElementById("planFile");
const reportFileInput = document.getElementById("reportFile");
const statusDiv = document.getElementById("status");
const resultContainer = document.getElementById("resultContainer");

const UPLOAD_URL = "http://127.0.0.1:8000/upload-and-analyze";

// ✨ (수정) 9-6 로직: renderResultHTML 함수 (HTML 구조 변경)
function renderResultHTML(data, filename) {
  // ... (rationaleMap, rationaleHtml, uncertaintiesHtml 생성 로직은 동일) ...
  const rationaleMap = {
    plan_specificity: "계획 구체성",
    plan_feasibility: "계획 실현성",
    plan_measurability: "계획 측정성",
    result_specificity_goal: "결과 구체성 (목표)",
    team_participation_diversity: "팀 참여도/다양성",
    evidence_strength: "증빙 강도",
  };
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
  let uncertaintiesHtml = "<ul>";
  if (data.uncertainties && data.uncertainties.length > 0) {
    data.uncertainties.forEach((item) => {
      uncertaintiesHtml += `<li>${item}</li>`;
    });
  } else {
    uncertaintiesHtml += "<li>없음</li>";
  }
  uncertaintiesHtml += "</ul>";

  // 9-6. (핵심 수정) 최종 결과를 '헤더'와 '콘텐츠'로 분리된 HTML로 반환
  return `
        <div class="result-item-container"> 
            
            <h3 class="result-header">📊 분석 결과 (${filename})</h3>
            
            <div class="result-content">
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
        </div>
    `;
}

// 2. 폼 'submit' 이벤트 리스너
uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  // ... (FormData 생성 및 파일 첨부 로직은 동일) ...
  const planFiles = planFileInput.files;
  const reportFiles = reportFileInput.files;
  if (planFiles.length === 0 || reportFiles.length === 0) {
    statusDiv.textContent =
      "적어도 하나 이상의 계획서와 결과보고서 파일을 선택해주세요.";
    return;
  }
  const formData = new FormData();
  for (const file of planFiles) {
    formData.append("plan_files", file);
  }
  for (const file of reportFiles) {
    formData.append("report_files", file);
  }

  statusDiv.textContent = `업로드 중... (총 ${
    planFiles.length + reportFiles.length
  }개 파일)`;
  resultContainer.innerHTML = "";

  try {
    const response = await fetch(UPLOAD_URL, {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      const responseData = await response.json();
      console.log("서버 응답:", responseData);

      // ... (9-1. 요약 정보 표시는 동일) ...
      const summary = responseData.summary;
      statusDiv.textContent = `✅ 분석 완료: ${summary.matched_count}건 매칭 성공, ${summary.unmatched_plans.length}건 계획서 매칭실패, ${summary.unmatched_reports.length}건 보고서 매칭실패`;

      // ... (9-2. 매칭 실패 파일 표시는 동일) ...
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

      // 9-3. 성공/실패 결과 순회
      responseData.results.forEach((result) => {
        if (result.status === "success") {
          try {
            // ... (JSON 파싱 로직은 동일) ...
            const rawString = result.analysis_result;
            const startIndex = rawString.indexOf("{");
            const endIndex = rawString.lastIndexOf("}");
            if (startIndex === -1 || endIndex === -1 || endIndex < startIndex) {
              throw new Error("응답에서 유효한 JSON 객체를 찾을 수 없습니다.");
            }
            const cleanedString = rawString.substring(startIndex, endIndex + 1);
            const data = JSON.parse(cleanedString);

            // (수정) renderResultHTML 함수가 새 구조를 반환
            resultContainer.innerHTML += renderResultHTML(
              data,
              result.filename
            );
          } catch (parseError) {
            console.error(
              "JSON 파싱 오류:",
              parseError,
              result.analysis_result
            );
            // ✨ (수정) 파싱 실패 시 HTML 구조도 헤더/콘텐츠로 분리
            resultContainer.innerHTML += `
              <div class="result-item-container error">
                <h3 class="result-header">❌ ${result.filename} 분석 실패 (JSON 파싱 오류)</h3>
                <div class="result-content">
                  <p>${parseError.message}</p>
                </div>
              </div>`;
          }
        } else {
          // ✨ (수정) API 처리 실패 시 HTML 구조도 헤더/콘텐츠로 분리
          resultContainer.innerHTML += `
            <div class="result-item-container error">
              <h3 class="result-header">❌ ${result.filename} 분석 실패</h3>
              <div class="result-content">
                <p>${result.error}</p>
              </div>
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

// --- ✨ (신규) 결과 항목 클릭(토글) 이벤트 리스너 ---
// 'resultContainer'에 이벤트 위임을 사용하여 동적으로 추가된 요소 처리
resultContainer.addEventListener("click", (event) => {
  // 1. 클릭된 요소가 'result-header'인지 확인
  const header = event.target.closest(".result-header");
  if (!header) {
    return; // 헤더가 아니면 무시
  }

  // 2. 헤더의 부모 컨테이너를 찾음
  const container = header.closest(".result-item-container");
  if (!container) {
    return;
  }

  // 3. (중요) 'error' 클래스가 없는 항목만 토글
  if (!container.classList.contains("error")) {
    container.classList.toggle("active");
  }
});
